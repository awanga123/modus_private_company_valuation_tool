#!/usr/bin/env python3
"""
Sample script demonstrating how to use the private company test data JSON files.
This can be adapted for your specific VC audit tool implementation.
"""

import json
from pathlib import Path
from typing import Dict, List


def load_company_data(filename: str) -> Dict:
    """Load a single company JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)


def load_all_companies() -> List[Dict]:
    """Load all companies from the batch file."""
    with open('all_companies_batch.json', 'r') as f:
        data = json.load(f)
        return data['companies']


def validate_company_data(company_data: Dict) -> bool:
    """Validate that required fields are present."""
    required_fields = [
        'target_company',
        'financials',
        'known_valuation',
        'peer_selection'
    ]
    
    for field in required_fields:
        if field not in company_data:
            print(f"Missing required field: {field}")
            return False
    
    return True


def extract_valuation_inputs(company_data: Dict) -> Dict:
    """Extract the key inputs needed for valuation."""
    return {
        'name': company_data['target_company']['name'],
        'revenue': company_data['financials'].get('revenue') or company_data['financials'].get('arr'),
        'ebitda': company_data['financials'].get('ebitda'),
        'industry': company_data['target_company']['industry'],
        'peer_tickers': company_data['peer_selection']['custom_tickers'],
        'known_valuation': company_data['known_valuation']['amount']
    }


def compare_to_known_valuation(estimated: float, known: float) -> Dict:
    """Compare estimated valuation to known valuation."""
    variance = (estimated - known) / known
    variance_pct = variance * 100
    
    within_range = -40 <= variance_pct <= 40
    
    return {
        'estimated_valuation': estimated,
        'known_valuation': known,
        'variance_dollars': estimated - known,
        'variance_percentage': variance_pct,
        'within_acceptable_range': within_range,
        'assessment': 'PASS' if within_range else 'FAIL'
    }


def print_test_results(company_name: str, results: Dict):
    """Pretty print test results."""
    print(f"\n{'='*60}")
    print(f"Test Results: {company_name}")
    print(f"{'='*60}")
    print(f"Known Valuation:     ${results['known_valuation']:,.0f}")
    print(f"Estimated Valuation: ${results['estimated_valuation']:,.0f}")
    print(f"Variance:            ${results['variance_dollars']:,.0f} ({results['variance_percentage']:.1f}%)")
    print(f"Status:              {results['assessment']}")
    print(f"{'='*60}\n")


def example_test_single_company():
    """Example: Test a single company."""
    print("Example 1: Testing Stripe")
    print("-" * 60)
    
    # Load Stripe data
    stripe_data = load_company_data('stripe_input.json')
    
    # Validate data
    if not validate_company_data(stripe_data):
        print("ERROR: Invalid data structure")
        return
    
    # Extract key inputs
    inputs = extract_valuation_inputs(stripe_data)
    
    print(f"Company: {inputs['name']}")
    print(f"Revenue: ${inputs['revenue']:,.0f}")
    print(f"Industry: {inputs['industry']}")
    print(f"Peer Tickers: {inputs['peer_tickers']}")
    
    # In a real implementation, you would:
    # 1. Fetch comparable company data using inputs['peer_tickers']
    # 2. Calculate valuation multiples
    # 3. Apply multiples to inputs['revenue']
    
    # For demonstration, let's assume your model estimated $85B
    estimated_valuation = 85_000_000_000
    
    # Compare to known valuation
    results = compare_to_known_valuation(
        estimated=estimated_valuation,
        known=inputs['known_valuation']
    )
    
    print_test_results(inputs['name'], results)


def example_test_all_companies():
    """Example: Test all companies in batch."""
    print("\nExample 2: Batch Testing All Companies")
    print("=" * 60)
    
    # Load all companies
    companies = load_all_companies()
    
    # Simulated valuations (replace with your actual valuation logic)
    simulated_valuations = {
        'stripe': 85_000_000_000,
        'spacex': 320_000_000_000,
        'databricks': 95_000_000_000,
        'canva': 38_000_000_000,
        'shein': 42_000_000_000
    }
    
    test_results = []
    
    for company in companies:
        company_id = company['id']
        name = company['target_company']['name']
        known_val = company['known_valuation']['amount']
        estimated_val = simulated_valuations[company_id]
        
        results = compare_to_known_valuation(estimated_val, known_val)
        test_results.append({
            'name': name,
            'results': results
        })
    
    # Print summary
    print("\nTest Summary:")
    print("-" * 60)
    passed = sum(1 for t in test_results if t['results']['assessment'] == 'PASS')
    total = len(test_results)
    
    for test in test_results:
        print(f"{test['name']:20s} {test['results']['assessment']:6s} "
              f"({test['results']['variance_percentage']:+6.1f}%)")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")


def example_integration_test():
    """Example: How to integrate with your valuation API."""
    print("\nExample 3: API Integration Pattern")
    print("-" * 60)
    
    # Load test data
    test_data = load_company_data('databricks_input.json')
    
    # Example API request structure
    api_request = {
        'target_company': test_data['target_company'],
        'financials': {
            'revenue': test_data['financials']['revenue'],
            'ebitda': test_data['financials'].get('ebitda')
        },
        'peer_selection': test_data['peer_selection'],
        'valuation_config': test_data['valuation_request']
    }
    
    print("API Request Payload:")
    print(json.dumps(api_request, indent=2))
    
    # In real implementation:
    # response = requests.post('http://localhost:8000/api/valuate', json=api_request)
    # valuation_result = response.json()
    
    print("\nExpected API Response Structure:")
    expected_response = {
        "valuation_summary": {
            "target_company": "Databricks",
            "enterprise_value_range": {
                "low": 85000000000,
                "mid": 95000000000,
                "high": 105000000000
            },
            "primary_valuation": 95000000000
        },
        "peer_analysis": {
            "peers_analyzed": ["SNOW", "MDB", "PLTR"],
            "methodology": "EV/Revenue multiple"
        },
        "audit_trail": {
            "calculation_steps": ["..."],
            "data_sources": {"...": "..."}
        }
    }
    print(json.dumps(expected_response, indent=2))


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Private Company Valuation Test Data - Usage Examples")
    print("="*60)
    
    # Check if files exist
    required_files = [
        'stripe_input.json',
        'all_companies_batch.json'
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"\nERROR: Missing required files: {missing_files}")
        print("Please ensure all JSON files are in the current directory.")
        return
    
    # Run examples
    try:
        example_test_single_company()
        example_test_all_companies()
        example_integration_test()
        
        print("\n" + "="*60)
        print("Examples completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
