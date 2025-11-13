#!/usr/bin/env python3
"""
Simple test script to demonstrate the simplified valuation implementation.

This script:
1. Selects peers based on sector from peer_universe
2. Fills up to 10 peers (manual + from universe)
3. Logs yfinance output
4. Performs basic revenue and EBITDA calculations
"""

from src.modus_comps_tool.models.company import PeerSelectionConfig, TargetCompany, ValuationConfig, ValuationRequest
from src.modus_comps_tool.services.valuation_service import ValuationService


def main():
    # Create a simplified test case for Stripe
    target = TargetCompany(
        name="Stripe",
        ticker=None,
        industry="Financial Technology",
        sector="Financial Technology",  # Using sector that exists in peer_universe
        revenue=5_100_000_000,  # $5.1B
        ebitda=None,  # Not provided
    )

    # Specify only 2 manual peers, rest will be filled from peer_universe
    peer_selection = PeerSelectionConfig(
        method="sector_based",
        custom_tickers=["SQ", "PYPL"],  # Only 2 manual peers
        filters={},
    )

    valuation_config = ValuationConfig(
        multiples=["EV_REVENUE", "EV_EBITDA"],
        statistics=[],  # Not using statistics anymore
        apply_dlom=False,
    )

    request = ValuationRequest(
        target_company=target,
        peer_selection=peer_selection,
        valuation_config=valuation_config,
    )

    # Run the simplified valuation
    service = ValuationService()
    print("\n" + "=" * 80)
    print("SIMPLIFIED VALUATION FOR STRIPE")
    print("=" * 80)
    print(f"\nTarget Company: {target.name}")
    print(f"Revenue: ${target.revenue:,.0f}")
    print(f"Sector: {target.sector}")
    print(f"Manual Peers Specified: {len(peer_selection.custom_tickers)}")
    print("\nRunning valuation...\n")

    result = service.valuate(request)

    print("\n" + "=" * 80)
    print("VALUATION RESULTS")
    print("=" * 80)

    # Display peer information
    print(f"\nTotal Peers Selected: {len(result.peer_analysis['peers'])}")
    print("\nPeers:")
    for peer in result.peer_analysis["peers"]:
        print(f"  - {peer['ticker']}: {peer.get('name', 'N/A')}")

    # Display valuation summary
    print("\nValuation Summary:")
    summary = result.valuation_summary
    print(f"  Target Company: {summary['target_company']}")
    print(f"  Valuation Date: {summary['valuation_date']}")

    if summary.get("revenue_based_valuation"):
        print(f"  Revenue-Based Valuation: ${summary['revenue_based_valuation']:,.0f}")
    if summary.get("ebitda_based_valuation"):
        print(f"  EBITDA-Based Valuation: ${summary['ebitda_based_valuation']:,.0f}")
    if summary.get("simple_average_valuation"):
        print(f"  Simple Average Valuation: ${summary['simple_average_valuation']:,.0f}")

    # Display multiple analysis
    print("\nMultiple Analysis:")
    for multiple_key, analysis in result.multiple_analysis.items():
        print(f"\n  {multiple_key}:")
        if analysis.values:
            print(f"    Peer Multiples: {[f'{v:.2f}x' for v in analysis.values]}")
            if analysis.mean:
                print(f"    Average Multiple: {analysis.mean:.2f}x")
            if analysis.implied_values:
                for stat, value in analysis.implied_values.items():
                    print(f"    Implied Valuation ({stat}): ${value:,.0f}")

    print("\n" + "=" * 80)
    print("Audit trail saved to:", result.audit_trail.metadata.get("path", "N/A"))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
