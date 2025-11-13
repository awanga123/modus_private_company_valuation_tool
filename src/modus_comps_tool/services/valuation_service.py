from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

import numpy as np
import structlog

from ..config.settings import settings
from ..models.audit import AuditCalculationStep, AuditTrail, ValuationMultipleAnalysis, ValuationResult
from ..models.company import PeerSelectionConfig, TargetCompany, ValuationConfig, ValuationRequest
from ..models.peer_group import PeerGroup
from ..models.valuation_multiple import ValuationMultiple
from .data_fetcher import CompanyDataFetcher
from .multiple_calculator import MultipleCalculator, MultipleResult
from .peer_selector import PeerSelector
from .stats_engine import StatsEngine

logger = structlog.get_logger(__name__)


@dataclass
class ValuationContext:
    request_id: str
    target_company: TargetCompany
    peer_group: PeerGroup
    valuation_config: ValuationConfig
    multiples: list[ValuationMultiple]
    audit_trail: AuditTrail


class ValuationService:
    """Coordinate peer selection, data fetching, multiple analysis, and audit logging."""

    # Initialize all the modules used in the valuation service 
    def __init__(
        self,
        peer_selector: PeerSelector | None = None,
        data_fetcher: CompanyDataFetcher | None = None,
        multiple_calculator: MultipleCalculator | None = None,
        stats_engine: StatsEngine | None = None,
    ) -> None:
        self.peer_selector = peer_selector or PeerSelector()
        self.data_fetcher = data_fetcher or CompanyDataFetcher()
        self.multiple_calculator = multiple_calculator or MultipleCalculator()
        self.stats_engine = stats_engine or StatsEngine()

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

        self._persist_audit_trail(result)
        return result

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
            except Exception as exc:  # capture all exceptions to keep audit trail
                logger.exception("peer_fetch.failure", ticker=peer.ticker, error=str(exc))
                ctx.peer_group.notes.append(f"Failed to fetch data for {peer.ticker}: {exc}")
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
        # group the multiple calculations by the type of multiple they are, ie either EV_REVENUE or EV_EBITDA
        # the output of grouped is a dictionary with the key being the type of multiple and the value being a list of MultipleResult objects
        grouped: dict[ValuationMultiple, list[MultipleResult]] = {}
        for result in multiple_results:
            grouped.setdefault(result.multiple, []).append(result)

        analyses: dict[str, ValuationMultipleAnalysis] = {}
        # iterate over the grouped multiple results and calculate the mean and median for each multiple type 
        for multiple, results in grouped.items():
            # get the numeric results for the multiple, ie either the revenue or ebitda values for the target company
            numeric_results = [(idx, res) for idx, res in enumerate(results) if res.value is not None]
            # get the values for the multiple, ie either the revenue or ebitda values for the target company
            raw_values = [res.value for _, res in numeric_results]

            # get the target company's metric value for the multiple, ie either it's revenue or ebitda
            metric_value = self._target_company_metric_value(multiple, ctx.target_company)

            logger.info(
                "valuation.multiple_values",
                multiple=multiple.value,
                values=raw_values,
                count=len(raw_values),
            )

            # if there are no raw values, then we know that peer comapnies did not have any data for this multiple type 
            if not raw_values:
                analyses[multiple.value] = ValuationMultipleAnalysis(
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
                continue

            # Use StatsEngine to detect outliers and calculate statistics
            summary_all = self.stats_engine.summarize(raw_values)
            outlier_indices = set(summary_all.outlier_indices)
            filtered_values = [
                value for idx, value in enumerate(raw_values) if idx not in outlier_indices
            ]
            summary_filtered = self.stats_engine.summarize(filtered_values) if filtered_values else summary_all

            outliers_excluded = []
            for idx in outlier_indices:
                result = numeric_results[idx][1]
                outliers_excluded.append(f"{result.ticker}: {result.value}")

            logger.info(
                "valuation.simple_average",
                multiple=multiple.value,
                average=summary_filtered.mean,
                median=summary_filtered.median,
                target_metric=metric_value,
            )

            implied_values: dict[str, float] = {}
            if metric_value is not None:
                # Calculate implied valuations for both mean and median
                if summary_filtered.mean is not None:
                    implied_values["mean"] = summary_filtered.mean * metric_value
                    logger.info(
                        "valuation.implied_value",
                        multiple=multiple.value,
                        stat="mean",
                        calculation=f"{summary_filtered.mean:.2f} × {metric_value:,.0f}",
                        result=implied_values["mean"],
                    )
                if summary_filtered.median is not None:
                    implied_values["median"] = summary_filtered.median * metric_value
                    logger.info(
                        "valuation.implied_value",
                        multiple=multiple.value,
                        stat="median",
                        calculation=f"{summary_filtered.median:.2f} × {metric_value:,.0f}",
                        result=implied_values["median"],
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

        # Collect all implied values for mean and median separately
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

        if not mean_values and not median_values:
            summary_base["enterprise_value"] = None
            summary_base["revenue_based_valuation_mean"] = None
            summary_base["revenue_based_valuation_median"] = None
            summary_base["ebitda_based_valuation_mean"] = None
            summary_base["ebitda_based_valuation_median"] = None
            return summary_base, {}

        # Extract specific valuations for both mean and median
        revenue_mean = multiple_analysis.get("EV_REVENUE", ValuationMultipleAnalysis(
            values=[], mean=None, median=None, min=None, max=None, std_dev=None,
            outliers_excluded=[], target_metric=None, implied_values={}
        )).implied_values.get("mean")
        revenue_median = multiple_analysis.get("EV_REVENUE", ValuationMultipleAnalysis(
            values=[], mean=None, median=None, min=None, max=None, std_dev=None,
            outliers_excluded=[], target_metric=None, implied_values={}
        )).implied_values.get("median")
        ebitda_mean = multiple_analysis.get("EV_EBITDA", ValuationMultipleAnalysis(
            values=[], mean=None, median=None, min=None, max=None, std_dev=None,
            outliers_excluded=[], target_metric=None, implied_values={}
        )).implied_values.get("mean")
        ebitda_median = multiple_analysis.get("EV_EBITDA", ValuationMultipleAnalysis(
            values=[], mean=None, median=None, min=None, max=None, std_dev=None,
            outliers_excluded=[], target_metric=None, implied_values={}
        )).implied_values.get("median")

        summary_base["revenue_based_valuation_mean"] = revenue_mean
        summary_base["revenue_based_valuation_median"] = revenue_median
        summary_base["ebitda_based_valuation_mean"] = ebitda_mean
        summary_base["ebitda_based_valuation_median"] = ebitda_median
        summary_base["mean_valuation"] = float(np.mean(mean_values)) if mean_values else None
        summary_base["median_valuation"] = float(np.mean(median_values)) if median_values else None

        logger.info(
            "valuation.final_summary",
            revenue_mean=revenue_mean,
            revenue_median=revenue_median,
            ebitda_mean=ebitda_mean,
            ebitda_median=ebitda_median,
            mean_valuation=summary_base["mean_valuation"],
            median_valuation=summary_base["median_valuation"],
        )

        adjustments: dict[str, object] = {
            "note": "Calculation using mean and median of peer multiples with outlier detection (z-score threshold = 2.0)",
        }

        return summary_base, adjustments

    def _persist_audit_trail(self, result: ValuationResult) -> None:
        settings.absolute_audit_trail_dir.mkdir(parents=True, exist_ok=True)
        path = settings.absolute_audit_trail_dir / f"{result.request_id}.json"
        payload = result.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        logger.info("audit.persisted", request_id=result.request_id, path=str(path))

    def load_result(self, request_id: str) -> ValuationResult | None:
        """Load a previously generated valuation result from disk."""
        path = settings.absolute_audit_trail_dir / f"{request_id}.json"
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        return ValuationResult.model_validate(data)

