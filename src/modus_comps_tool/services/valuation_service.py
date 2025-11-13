from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

import numpy as np
import structlog

from ..models.audit import (
    AuditCalculationStep,
    AuditTrail,
    ValuationMultipleAnalysis,
    ValuationResult,
)
from ..models.company import (
    PeerSelectionConfig,
    TargetCompany,
    ValuationConfig,
    ValuationRequest,
)
from ..models.peer_group import PeerGroup
from ..models.valuation_multiple import ValuationMultiple
from .audit_persistence import AuditPersistence
from .data_fetcher import CompanyDataFetcher
from .multiple_calculator import MultipleCalculator, MultipleResult
from .peer_selector import PeerSelector
from .stats_engine import StatsEngine

logger = structlog.get_logger(__name__)


# Major context object to store the valuation context and data during the valuation process.
# Note that the audit trail is built up throughout the steps as to keep track of what is going on sequentially 
# which is why we include the audit trail in the context object.
@dataclass
class ValuationContext:
    request_id: str
    target_company: TargetCompany
    peer_group: PeerGroup
    valuation_config: ValuationConfig
    multiples: list[ValuationMultiple]
    audit_trail: AuditTrail


class ValuationService:
    """Orchestrate valuation workflow including peer selection, data fetching, and multiple analysis."""

    def __init__(
        self,
        peer_selector: PeerSelector | None = None,
        data_fetcher: CompanyDataFetcher | None = None,
        multiple_calculator: MultipleCalculator | None = None,
        stats_engine: StatsEngine | None = None,
        audit_persistence: AuditPersistence | None = None,
    ) -> None:
        self.peer_selector = peer_selector or PeerSelector()
        self.data_fetcher = data_fetcher or CompanyDataFetcher()
        self.multiple_calculator = multiple_calculator or MultipleCalculator()
        self.stats_engine = stats_engine or StatsEngine()
        self.audit_persistence = audit_persistence or AuditPersistence()

    def valuate(self, request: ValuationRequest) -> ValuationResult:
        """Execute the simplified valuation workflow for the supplied request."""
        request_id = str(uuid4())

        # Only use EV_REVENUE and EV_EBITDA multiples, in the future we can add more multiples if needed like P/E ratio etc
        multiples = [ValuationMultiple.EV_REVENUE, ValuationMultiple.EV_EBITDA]

        # Initialize audit trail at the start to track steps as they happen
        audit_trail = AuditTrail(
            request_id=request_id,
            valuation_date=datetime.now(timezone.utc),
            data_sources={
                "peer_financials_source": "yfinance",
            },
        )

        # Use default configs if not provided - simplifies API usage
        peer_selection = request.peer_selection or PeerSelectionConfig()
        valuation_config = request.valuation_config or ValuationConfig()

        # Step 1: Select peer companies using the peer selector module
        peer_group = self.peer_selector.select_peers(request.target_company, peer_selection)

        ctx = ValuationContext(
            request_id=request_id,
            target_company=request.target_company,
            peer_group=peer_group,
            valuation_config=valuation_config,
            multiples=multiples,
            audit_trail=audit_trail,
        )

        # Record peer selection step in audit trail
        ctx.audit_trail.calculation_steps.append(
            AuditCalculationStep(
                description="Peer selection completed",
                data=ctx.peer_group.model_dump(),
            )
        )

        logger.info("valuation.start", request_id=request_id, company=ctx.target_company.name)
        start_time = datetime.now(timezone.utc)
        # Step 2: Fetch financial data for each peer using the data fetcher module and calling the yfinance API
        peer_financials = self._populate_peers(ctx)

        # Record financial data fetching step in audit trail
        ctx.audit_trail.data_sources["peer_count"] = len(peer_financials)
        ctx.audit_trail.calculation_steps.append(
            AuditCalculationStep(
                description="Fetched peer financials",
                data={ticker: {"keys": list(data.keys())} for ticker, data in peer_financials.items()},
            )
        )

        # Step 3: Calculate the multiples for each peer using the multiple calculator module
        # Exmaple output from the multiple calculator module:
        #
        # [MultipleResult(ticker='COIN', multiple=<ValuationMultiple.EV_REVENUE: 'EV_REVENUE'>,
        #        value=12.18500263801434, numerator=79982698496, denominator=6564028000.0, rationale='enterprise_value / revenue'),
        #  MultipleResult(ticker='COIN', multiple=<ValuationMultiple.EV_EBITDA: 'EV_EBITDA'>,
        #       value=35.779478488974185, numerator=79982698496, denominator=2235435000.0, rationale='enterprise_value / ebitda'),
        #  etc]
        multiple_results = self._calculate_multiples(ctx.peer_group, ctx.multiples)
        logger.debug("calculated_multiples", results_count=len(multiple_results))

        # Record multiple calculation step in audit trail
        peer_multiple_details: dict[str, list[dict[str, object | None]]] = {}
        for result in multiple_results:
            peer_multiple_details.setdefault(result.ticker, []).append(
                {
                    "multiple": result.multiple.value,
                    "numerator": result.numerator,
                    "denominator": result.denominator,
                    "calculated_multiple": result.value,
                    "rationale": result.rationale,
                }
            )
        ctx.audit_trail.calculation_steps.append(
            AuditCalculationStep(
                description="Calculated valuation multiples per peer",
                data=peer_multiple_details,
            )
        )

        # Step 4: Calcualte the statistics for the multiples using the stats engine module to find the outliers
        # and calculate the mean and median multiples for the target company
        multiple_analysis = self._analyze_multiples_simple(multiple_results, ctx)

        # Record multiple analysis step in audit trail
        implied_values_detail: dict[str, dict[str, object]] = {}
        for multiple_key, analysis in multiple_analysis.items():
            implied_values_detail[multiple_key] = {
                "peer_multiples_used": analysis.values,
                "statistics_after_outlier_screening": {
                    "mean": analysis.mean,
                    "median": analysis.median,
                    "min": analysis.min,
                    "max": analysis.max,
                    "std_dev": analysis.std_dev,
                    "outliers_removed": analysis.outliers_excluded,
                },
                "target_metric_applied": analysis.target_metric,
                "implied_enterprise_values": analysis.implied_values,
            }
        ctx.audit_trail.calculation_steps.append(
            AuditCalculationStep(
                description="Multiple analysis summary",
                data=implied_values_detail,
            )
        )

        # Step 5: Summarize the results
        valuation_summary, adjustments = self._summarize_results_simple(ctx, multiple_analysis)

        # Record final valuation summary step in audit trail
        ctx.audit_trail.calculation_steps.append(
            AuditCalculationStep(
                description="Final valuation summary",
                data={
                    "valuation_summary": valuation_summary,
                    "adjustments": adjustments,
                },
            )
        )

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        # Add final metadata to audit trail
        ctx.audit_trail.metadata["calculation_time_ms"] = duration_ms
        ctx.audit_trail.metadata["applied_multiples"] = [multiple.value for multiple in ctx.multiples]

        result = ValuationResult(
            request_id=request_id,
            valuation_summary=valuation_summary,
            peer_analysis=ctx.peer_group.model_dump(),
            multiple_analysis=multiple_analysis,
            adjustments=adjustments,
            audit_trail=ctx.audit_trail,
            metadata={
                "calculation_time_ms": duration_ms,
                "multiples_used": [multiple.value for multiple in ctx.multiples],
            },
        )

        self.audit_persistence.persist(result)
        return result




### Helper methods for the valuation service ###


    def _populate_peers(self, ctx: ValuationContext) -> dict[str, dict]:
        """Fetch financial data for every peer and enrich the peer objects in-place."""
        financials = {}
        for peer in ctx.peer_group.peers:
            try:
                data = self.data_fetcher.fetch(peer.ticker)
                financials[peer.ticker] = data
                peer.enterprise_value = data.get("enterprise_value")
                peer.revenue = data.get("revenue")
                peer.ebitda = data.get("ebitda")
                peer.market_cap = data.get("market_cap")
                peer.net_income = data.get("net_income")
                timestamp = data.get("source_meta", {}).get("fetched_at")
                if timestamp:
                    try:
                        peer.data_timestamp = datetime.fromisoformat(timestamp)
                    except ValueError:
                        logger.warning("peer_fetch.timestamp_parse_failed", ticker=peer.ticker, value=timestamp)
                peer.raw_source = data
                if peer.enterprise_value is None or peer.revenue is None:
                    ctx.peer_group.notes.append(
                        f"Incomplete data for {peer.ticker}: enterprise_value={peer.enterprise_value}, revenue={peer.revenue}"
                    )
            except (ConnectionError, TimeoutError) as exc:
                logger.warning("peer_fetch.network_error", ticker=peer.ticker, error_type=type(exc).__name__)
                ctx.peer_group.notes.append(f"Network error fetching data for {peer.ticker}")
            except (KeyError, ValueError, TypeError) as exc:
                logger.error("peer_fetch.data_error", ticker=peer.ticker, error=str(exc))
                ctx.peer_group.notes.append(f"Data format error for {peer.ticker}")
            except Exception as exc:
                # Catch remaining exceptions but log them clearly
                logger.exception("peer_fetch.unexpected_error", ticker=peer.ticker, error_type=type(exc).__name__)
                ctx.peer_group.notes.append(f"Unable to retrieve financial data for {peer.ticker}")
        return financials

    def _calculate_multiples(
        self,
        peer_group: PeerGroup,
        multiples: Iterable[ValuationMultiple],
    ) -> list[MultipleResult]:
        """Evaluate all requested multiples for every peer in the group."""
        results: list[MultipleResult] = []
        for peer in peer_group.peers:
            peer_results = self.multiple_calculator.calculate(peer, multiples)
            for outcome in peer_results:
                if outcome.value is not None:
                    if outcome.multiple == ValuationMultiple.EV_REVENUE:
                        peer.ev_to_revenue = outcome.value
                    elif outcome.multiple == ValuationMultiple.EV_EBITDA:
                        peer.ev_to_ebitda = outcome.value
                results.append(outcome)
        return results

    def _target_company_metric_value(self, multiple: ValuationMultiple, target: TargetCompany) -> float | None:
        """Get the target company's metric value for the given multiple."""
        if multiple == ValuationMultiple.EV_REVENUE:
            return target.revenue
        if multiple == ValuationMultiple.EV_EBITDA:
            return target.ebitda
        return None

    def _analyze_multiples_simple(
        self,
        multiple_results: list[MultipleResult],
        ctx: ValuationContext,
    ) -> dict[str, ValuationMultipleAnalysis]:
        """Calculate mean and median with outlier detection using z-score threshold."""
        grouped = self._group_results_by_multiple(multiple_results)

        analyses: dict[str, ValuationMultipleAnalysis] = {}
        for multiple, results in grouped.items():
            # For every grouped multiple, we extract the numeric values and the raw values for the multiple in order to 
            # calculate the statistics and the implied values.
            numeric_results, raw_values = self._extract_numeric_values(results)
            metric_value = self._target_company_metric_value(multiple, ctx.target_company)

            logger.info(
                "valuation.multiple_values",
                multiple=multiple.value,
                values=raw_values,
                count=len(raw_values),
            )

            # If there are no raw values then there is no data to calculate the statistics and the implied values,
            # so we create an empty analysis for this multiple.
            if not raw_values:
                analyses[multiple.value] = self._create_empty_analysis(metric_value)
                continue

            # We detect and filter out the outliers using the z-score threshold of 2.0
            #  and return the filtered statistics and the outliers excluded.
            summary_filtered, outliers_excluded = self._detect_and_filter_outliers(
                raw_values, numeric_results
            )

            logger.info(
                "valuation.simple_average",
                multiple=multiple.value,
                average=summary_filtered.mean,
                median=summary_filtered.median,
                target_metric=metric_value,
            )

            implied_values = self._calculate_implied_values(
                summary_filtered, metric_value, multiple.value
            )

            analyses[multiple.value] = ValuationMultipleAnalysis(
                values=raw_values,
                mean=summary_filtered.mean,
                median=summary_filtered.median,
                min=summary_filtered.min,
                max=summary_filtered.max,
                std_dev=summary_filtered.std_dev,
                outliers_excluded=outliers_excluded,
                target_metric=metric_value,
                implied_values=implied_values,
            )

        return analyses

    def _group_results_by_multiple(
        self, multiple_results: list[MultipleResult]
    ) -> dict[ValuationMultiple, list[MultipleResult]]:
        """Group multiple results by their type (EV_REVENUE or EV_EBITDA)."""
        grouped: dict[ValuationMultiple, list[MultipleResult]] = {}
        for result in multiple_results:
            grouped.setdefault(result.multiple, []).append(result)
        return grouped

    def _extract_numeric_values(
        self, results: list[MultipleResult]
    ) -> tuple[list[tuple[int, MultipleResult]], list[float]]:
        """Extract numeric values from results, filtering out None values."""
        numeric_results = [(idx, res) for idx, res in enumerate(results) if res.value is not None]
        raw_values = [res.value for _, res in numeric_results]
        return numeric_results, raw_values

    def _detect_and_filter_outliers(
        self, raw_values: list[float], numeric_results: list[tuple[int, MultipleResult]]
    ) -> tuple[Any, list[str]]:
        """Detect outliers using z-score and return filtered statistics."""
        summary_all = self.stats_engine.summarize(raw_values)
        # We get the outlier indices from the summary so we can filter out the outliers from the raw values.
        outlier_indices = set(summary_all.outlier_indices)

        # We filter out the outliers from the raw values to get the filtered values.
        filtered_values = [
            value for idx, value in enumerate(raw_values) if idx not in outlier_indices
        ]
        # We calculate the statistics for the filtered values if there are any, otherwise we use the summary of all values.
        summary_filtered = self.stats_engine.summarize(filtered_values) if filtered_values else summary_all

        outliers_excluded = self._format_outliers(outlier_indices, numeric_results)

        return summary_filtered, outliers_excluded

    def _format_outliers(
        self, outlier_indices: set[int], numeric_results: list[tuple[int, MultipleResult]]
    ) -> list[str]:
        """Format outlier information as human-readable strings."""
        outliers_excluded = []
        for idx in outlier_indices:
            result = numeric_results[idx][1]
            outliers_excluded.append(f"{result.ticker}: {result.value}")
        return outliers_excluded

    def _calculate_implied_values(
        self, summary: Any, metric_value: float | None, multiple_name: str
    ) -> dict[str, float]:
        """Calculate implied enterprise values using mean and median multiples."""
        implied_values: dict[str, float] = {}
        # Actually calculate the implied values using the mean and median multiples and the target metric value.
        # This is the core of the valuation process, the implied values are the values that are implied by the multiples and the target metric value.

        if metric_value is None:
            return implied_values

        if summary.mean is not None:
            implied_values["mean"] = summary.mean * metric_value
            logger.info(
                "valuation.implied_value",
                multiple=multiple_name,
                stat="mean",
                calculation=f"{summary.mean:.2f} × {metric_value:,.0f}",
                result=implied_values["mean"],
            )

        if summary.median is not None:
            implied_values["median"] = summary.median * metric_value
            logger.info(
                "valuation.implied_value",
                multiple=multiple_name,
                stat="median",
                calculation=f"{summary.median:.2f} × {metric_value:,.0f}",
                result=implied_values["median"],
            )

        return implied_values

    def _create_empty_analysis(self, metric_value: float | None) -> ValuationMultipleAnalysis:
        """Create an empty analysis when no peer data is available."""
        return ValuationMultipleAnalysis(
            values=[],
            mean=None,
            median=None,
            min=None,
            max=None,
            std_dev=None,
            outliers_excluded=[],
            target_metric=metric_value,
            implied_values={},
        )

    def _get_implied_value(
        self, multiple_analysis: dict[str, ValuationMultipleAnalysis], multiple_key: str, stat_key: str
    ) -> float | None:
        """Extract implied value for a specific multiple and statistic (mean/median)."""
        default_analysis = ValuationMultipleAnalysis(
            values=[],
            mean=None,
            median=None,
            min=None,
            max=None,
            std_dev=None,
            outliers_excluded=[],
            target_metric=None,
            implied_values={},
        )
        return multiple_analysis.get(multiple_key, default_analysis).implied_values.get(stat_key)

    def _apply_dlom(self, valuation: float | None, dlom_percentage: float) -> float | None:
        """Apply Discount for Lack of Marketability (DLOM) to a valuation."""
        if valuation is None:
            return None
        return valuation * (1 - dlom_percentage)

    def _summarize_results_simple(
        self,
        ctx: ValuationContext,
        multiple_analysis: dict[str, ValuationMultipleAnalysis],
    ) -> tuple[dict[str, object], dict[str, object]]:
        """Simplified summary: show both mean and median based valuations separately."""
        summary_base = {
            "target_company": ctx.target_company.name,
            "valuation_date": datetime.now(timezone.utc).date().isoformat(),
        }

        # Collect all implied values for mean and median separately for each multiple type.
        mean_values: list[float] = []
        median_values: list[float] = []
        for multiple_key, analysis in multiple_analysis.items():
            for stat_name, value in analysis.implied_values.items():
                if stat_name == "mean":
                    mean_values.append(value)
                elif stat_name == "median":
                    median_values.append(value)
                logger.info(
                    "valuation.summary_value",
                    multiple=multiple_key,
                    stat=stat_name,
                    value=value,
                )

        # If there are no mean or median values then there is no data to calculate the enterprise value,
        # so we return the summary base with the enterprise value set to None.
        if not mean_values and not median_values:
            summary_base["enterprise_value"] = None
            summary_base["revenue_based_valuation_mean"] = None
            summary_base["revenue_based_valuation_median"] = None
            summary_base["ebitda_based_valuation_mean"] = None
            summary_base["ebitda_based_valuation_median"] = None
            return summary_base, {}

        # Extract specific valuations for both mean and median (pre-DLOM)
        revenue_mean = self._get_implied_value(multiple_analysis, "EV_REVENUE", "mean")
        revenue_median = self._get_implied_value(multiple_analysis, "EV_REVENUE", "median")
        ebitda_mean = self._get_implied_value(multiple_analysis, "EV_EBITDA", "mean")
        ebitda_median = self._get_implied_value(multiple_analysis, "EV_EBITDA", "median")

        # Store pre-DLOM valuations
        summary_base["revenue_based_valuation_mean"] = revenue_mean
        summary_base["revenue_based_valuation_median"] = revenue_median
        summary_base["ebitda_based_valuation_mean"] = ebitda_mean
        summary_base["ebitda_based_valuation_median"] = ebitda_median

        # Calculate overall mean and median valuations (pre-DLOM)
        mean_valuation_pre_dlom = float(np.mean(mean_values)) if mean_values else None
        median_valuation_pre_dlom = float(np.mean(median_values)) if median_values else None

        summary_base["mean_avereage_valuation"] = mean_valuation_pre_dlom
        summary_base["median_average_valuation"] = median_valuation_pre_dlom

        # Apply DLOM if configured
        dlom_applied = False
        if ctx.valuation_config.apply_dlom and ctx.valuation_config.dlom_percentage > 0:
            dlom_applied = True
            dlom_pct = ctx.valuation_config.dlom_percentage

            # Apply DLOM to all valuations
            revenue_mean_post_dlom = self._apply_dlom(revenue_mean, dlom_pct)
            revenue_median_post_dlom = self._apply_dlom(revenue_median, dlom_pct)
            ebitda_mean_post_dlom = self._apply_dlom(ebitda_mean, dlom_pct)
            ebitda_median_post_dlom = self._apply_dlom(ebitda_median, dlom_pct)
            mean_valuation_post_dlom = self._apply_dlom(mean_valuation_pre_dlom, dlom_pct)
            median_valuation_post_dlom = self._apply_dlom(median_valuation_pre_dlom, dlom_pct)

            # Add post-DLOM values to summary
            summary_base["dlom_applied"] = True
            summary_base["dlom_percentage"] = dlom_pct
            summary_base["revenue_based_valuation_mean_post_dlom"] = revenue_mean_post_dlom
            summary_base["revenue_based_valuation_median_post_dlom"] = revenue_median_post_dlom
            summary_base["ebitda_based_valuation_mean_post_dlom"] = ebitda_mean_post_dlom
            summary_base["ebitda_based_valuation_median_post_dlom"] = ebitda_median_post_dlom
            summary_base["mean_average_valuation_post_dlom"] = mean_valuation_post_dlom
            summary_base["median_average_valuation_post_dlom"] = median_valuation_post_dlom

            logger.info(
                "valuation.dlom_applied",
                dlom_percentage=dlom_pct,
                mean_pre_dlom=mean_valuation_pre_dlom,
                mean_post_dlom=mean_valuation_post_dlom,
                median_pre_dlom=median_valuation_pre_dlom,
                median_post_dlom=median_valuation_post_dlom,
            )
        else:
            summary_base["dlom_applied"] = False

        logger.info(
            "valuation.final_summary",
            revenue_mean=revenue_mean,
            revenue_median=revenue_median,
            ebitda_mean=ebitda_mean,
            ebitda_median=ebitda_median,
            mean_valuation=mean_valuation_pre_dlom,
            median_valuation=median_valuation_pre_dlom,
            dlom_applied=dlom_applied,
        )

        # Build adjustments dict with DLOM info
        adjustments: dict[str, object] = {
            "note": "Calculation using mean and median of peer multiples with outlier detection (z-score threshold = 2.0)",
        }

        if dlom_applied:
            adjustments["dlom"] = {
                "applied": True,
                "percentage": ctx.valuation_config.dlom_percentage,
                "description": f"Applied {ctx.valuation_config.dlom_percentage:.1%} discount for lack of marketability",
                "valuation_adjustments": {
                    "mean_valuation": {
                        "pre_dlom": mean_valuation_pre_dlom,
                        "post_dlom": summary_base.get("mean_average_valuation_post_dlom"),
                        "discount_amount": mean_valuation_pre_dlom - summary_base.get("mean_average_valuation_post_dlom")
                        if mean_valuation_pre_dlom and summary_base.get("mean_average_valuation_post_dlom")
                        else None,
                    },
                    "median_valuation": {
                        "pre_dlom": median_valuation_pre_dlom,
                        "post_dlom": summary_base.get("median_average_valuation_post_dlom"),
                        "discount_amount": median_valuation_pre_dlom - summary_base.get("median_average_valuation_post_dlom")
                        if median_valuation_pre_dlom and summary_base.get("median_average_valuation_post_dlom")
                        else None,
                    },
                },
            }
        else:
            adjustments["dlom"] = {
                "applied": False,
                "percentage": 0.0,
                "description": "No DLOM adjustment applied",
            }

        return summary_base, adjustments

    def load_result(self, request_id: str) -> ValuationResult | None:
        """Load a previously generated valuation result from disk."""
        return self.audit_persistence.load(request_id)

