# Private Company Test Dataset for VC Audit Tool

This dataset contains real financial data and valuations for 5 major private companies, compiled from public sources (news articles, financial reports, and market research) as of November 2025. Use this data to test your Comparable Company Analysis (Comps) valuation methodology.

---

## Company 1: Stripe

### Industry Classification
- **Industry**: Financial Technology (FinTech)
- **Sector**: Payments Processing / Payment Infrastructure
- **SIC Code**: 6099 (Functions Related to Depository Banking)
- **Sub-sector**: Digital Payments, Payment Gateway, Financial Services Software

### Financial Data (2024-2025)
- **Revenue (2024)**: $5.1 billion (net revenue)
- **Gross Revenue (2024)**: ~$18 billion (before transaction processing costs)
- **EBITDA (2024)**: Not publicly disclosed, but company achieved profitability in 2024
- **Free Cash Flow (2024)**: $2.2 billion (doubled from 2023)
- **Revenue Growth (YoY)**: 28% (2023 to 2024)
- **Payment Volume (2024)**: $1.4 trillion processed
- **Gross Margin**: >80% for subscription products

### Valuation Information
- **Last Funding Round**: February 2025 (Series I-IV)
- **Current Valuation**: $91.5 billion (February 2025 tender offer)
- **Previous Valuations**:
  - November 2024: $70 billion
  - 2021 Peak: $95 billion
  - 2023: $50 billion (down round)
- **Valuation Multiple**: ~16.3x revenue (based on $91.5B valuation / $5.6B 2024 revenue)

### Key Metrics
- **Customers**: 100+ companies processing $1B+ annually
- **Websites Using Stripe**: 1.31 million active globally
- **Employees**: ~8,500
- **Founded**: 2010
- **Headquarters**: San Francisco, CA

### Comparable Public Companies (Suggested)
- Square/Block (SQ)
- PayPal (PYPL)
- Adyen (ADYE)
- Fiserv (FISV)
- Fidelity National Information Services (FIS)

### Example Input for Comps Model
```json
{
  "target_company": {
    "name": "Stripe",
    "ticker": null,
    "revenue": 5100000000,
    "ebitda": null,
    "industry": "Financial Technology",
    "sector": "Payment Processing",
    "sic_code": "6099",
    "founded_year": 2010
  },
  "known_valuation": {
    "amount": 91500000000,
    "date": "2025-02-27",
    "round": "Series I-IV",
    "source": "Secondary tender offer"
  },
  "peer_selection": {
    "method": "industry_based",
    "custom_tickers": ["SQ", "PYPL", "ADYE", "FIS", "FISV"],
    "filters": {
      "revenue_range": [1000000000, 50000000000],
      "exclude_negative_ebitda": true
    }
  }
}
```

### Data Sources
- Sacra.com, TechCrunch, Bloomberg, CNBC, The Information, Chargeflow.io
- Company announcements and secondary market reports

---

## Company 2: SpaceX

### Industry Classification
- **Industry**: Aerospace & Defense
- **Sector**: Space Transportation & Satellite Communications
- **SIC Code**: 3761 (Guided Missiles and Space Vehicles)
- **Sub-sector**: Launch Services, Satellite Internet (Starlink)

### Financial Data (2024-2025)
- **Revenue (2024)**: $14.2 billion
- **Revenue Breakdown**:
  - Starlink: $7.7 billion (54% of revenue)
  - Launch Services: $5.5 billion (39% of revenue)
  - Other: ~$1 billion (7% of revenue)
- **Revenue Growth (YoY)**: 63% (2023 to 2024)
- **Net Income**: Not publicly disclosed
- **EBITDA**: Estimated positive, company profitable
- **Starlink Subscribers**: 4.6 million (2024)

### Valuation Information
- **Last Funding Round**: December 2024
- **Current Valuation**: $350 billion (December 2024 tender offer)
- **Previous Valuations**:
  - June 2024: $210 billion
  - August 2024: $208 billion
  - 2021: $100 billion
  - 2015: $12 billion
- **Valuation Multiple**: ~24.6x revenue (based on $350B valuation / $14.2B revenue)

### Key Metrics
- **Launches (2024)**: 134 successful Falcon launches
- **Market Share**: >85% of orbital payloads (early 2024)
- **Starlink Market Position**: Leading LEO satellite internet provider
- **Employees**: Not publicly disclosed (estimated 10,000+)
- **Founded**: 2002
- **Headquarters**: Hawthorne, CA (relocating to Brownsville, TX)

### Comparable Public Companies (Suggested)
- Boeing (BA)
- Lockheed Martin (LMT)
- Northrop Grumman (NOC)
- L3Harris Technologies (LHX)
- Viasat (VSAT) - for Starlink comparison

### Example Input for Comps Model
```json
{
  "target_company": {
    "name": "SpaceX",
    "ticker": null,
    "revenue": 14200000000,
    "ebitda": null,
    "industry": "Aerospace & Defense",
    "sector": "Space Transportation",
    "sic_code": "3761",
    "founded_year": 2002
  },
  "known_valuation": {
    "amount": 350000000000,
    "date": "2024-12-15",
    "round": "Secondary tender",
    "source": "Employee and investor secondary sale"
  },
  "peer_selection": {
    "method": "industry_based",
    "custom_tickers": ["BA", "LMT", "NOC", "LHX"],
    "filters": {
      "revenue_range": [5000000000, 100000000000],
      "exclude_negative_ebitda": false
    }
  }
}
```

### Data Sources
- Sacra.com, SpaceXStock.com, Forge Global, Bloomberg, ARK Invest, Morgan Stanley
- Company announcements and tender offer reports

---

## Company 3: Databricks

### Industry Classification
- **Industry**: Business/Productivity Software
- **Sector**: Data Analytics & AI Platform
- **SIC Code**: 7372 (Prepackaged Software)
- **Sub-sector**: Data Lakehouse, Machine Learning Platform, Business Intelligence

### Financial Data (2024-2025)
- **ARR (Annual Recurring Revenue) Q2 2025**: $4 billion
- **ARR (2024 end)**: $3 billion
- **Revenue (2024)**: $3.7 billion
- **Revenue (2023)**: $2.4 billion
- **Revenue Growth (YoY)**: >50% (Q2 2025)
- **AI Products ARR**: $1 billion+ (2025)
- **Gross Margin**: 70-80% (typical for cloud software)
- **Free Cash Flow**: Positive (last 12 months as of Sept 2025)
- **Net Expansion Rate**: 140% (2024)

### Valuation Information
- **Last Funding Round**: September 2025 (Series K)
- **Current Valuation**: $100+ billion (September 2025)
- **Previous Valuations**:
  - December 2024: $62 billion (Series J)
  - September 2023: $43 billion
  - 2021: $38 billion
- **Valuation Multiple**: ~25x ARR (based on $100B valuation / $4B ARR)
- **Total Funding Raised**: ~$14 billion

### Key Metrics
- **Customers**: 10,000+ organizations (including 60% of Fortune 500)
- **Average Contract Value (ACV)**: $208,696 (June 2024)
- **Employees**: 12,312 total (683 engineers, 501 sales reps)
- **Founded**: 2013
- **Headquarters**: San Francisco, CA

### Comparable Public Companies (Suggested)
- Snowflake (SNOW)
- MongoDB (MDB)
- Palantir Technologies (PLTR)
- Confluent (CFLT)
- Elastic (ESTC)

### Example Input for Comps Model
```json
{
  "target_company": {
    "name": "Databricks",
    "ticker": null,
    "revenue": 4000000000,
    "ebitda": null,
    "industry": "Enterprise Software",
    "sector": "Data Analytics & AI",
    "sic_code": "7372",
    "founded_year": 2013,
    "business_model": "SaaS"
  },
  "known_valuation": {
    "amount": 100000000000,
    "date": "2025-09-08",
    "round": "Series K",
    "source": "Primary funding round"
  },
  "peer_selection": {
    "method": "industry_based",
    "custom_tickers": ["SNOW", "MDB", "PLTR", "CFLT", "ESTC"],
    "filters": {
      "revenue_range": [500000000, 10000000000],
      "exclude_negative_ebitda": false,
      "saas_only": true
    }
  }
}
```

### Data Sources
- Databricks.com, GetLatka, TechCrunch, Technology Magazine, The Motley Fool, Sacra.com
- Company press releases and investor presentations

---

## Company 4: Canva

### Industry Classification
- **Industry**: Multimedia and Design Software
- **Sector**: Creative Software / Graphic Design Tools
- **SIC Code**: 7372 (Prepackaged Software)
- **Sub-sector**: Design Platform, Collaboration Software, Visual Communication

### Financial Data (2024-2025)
- **ARR (August 2025)**: $3.3 billion
- **ARR (End of 2024)**: $2.8 billion
- **Revenue (2024)**: $2.7 billion (up 35% from 2023)
- **Revenue (2023)**: $2.0 billion
- **Revenue Growth (YoY)**: ~18% (2024 to 2025)
- **Net Profit Margin**: 10.6% (2025)
- **Gross Margin**: High (typical for SaaS, 70-80%+)
- **Profitability**: 7+ years of profitability

### Valuation Information
- **Latest Secondary Sale**: August 2025
- **Current Valuation**: $42 billion (August 2025 employee share sale)
- **Previous Valuations**:
  - July 2025: $37 billion
  - October 2024: $32 billion
  - April 2024: $26 billion (secondary sale)
  - 2021 Peak: $40 billion
- **Valuation Multiple**: ~12.7x ARR (based on $42B valuation / $3.3B ARR)
- **Total Funding Raised**: $612 million

### Key Metrics
- **Monthly Active Users**: 240 million (August 2025), up from 220M in Sept 2024
- **Paying Users/Teams**: 130,000+ teams with 1,000+ employees using Canva Teams
- **AI Usage**: 800M AI tool uses per month (700% YoY growth)
- **Employees**: 5,500-7,600
- **Founded**: 2012
- **Headquarters**: Sydney, Australia

### Comparable Public Companies (Suggested)
- Adobe (ADBE) - for design software comparison
- Figma (private, but can use ADBE as proxy)
- Autodesk (ADSK)
- Monday.com (MNDY) - for collaboration platform comparison
- Wix.com (WIX)

### Example Input for Comps Model
```json
{
  "target_company": {
    "name": "Canva",
    "ticker": null,
    "revenue": 3300000000,
    "ebitda": 349800000,
    "industry": "Creative Software",
    "sector": "Design & Collaboration Tools",
    "sic_code": "7372",
    "founded_year": 2012,
    "business_model": "Freemium SaaS"
  },
  "known_valuation": {
    "amount": 42000000000,
    "date": "2025-08-20",
    "round": "Secondary Market",
    "source": "Employee share sale"
  },
  "peer_selection": {
    "method": "industry_based",
    "custom_tickers": ["ADBE", "ADSK", "MNDY", "WIX"],
    "filters": {
      "revenue_range": [1000000000, 30000000000],
      "exclude_negative_ebitda": true,
      "saas_only": true
    }
  }
}
```

### Data Sources
- Sacra.com, CNBC, GetLatka, Whop.com, CBInsights, StartMotionMedia
- Company announcements and secondary market reports

---

## Company 5: Shein

### Industry Classification
- **Industry**: E-commerce / Fashion Retail
- **Sector**: Fast Fashion / Online Apparel
- **SIC Code**: 5961 (Catalog and Mail-Order Houses) or 5699 (Miscellaneous Apparel Stores)
- **Sub-sector**: Direct-to-Consumer Fashion, Mobile Commerce

### Financial Data (2024-2025)
- **Revenue (2024)**: $38 billion (some sources report $50B including GMV)
- **Revenue (Q1 2025)**: ~$10 billion
- **Revenue (2023)**: $32.5 billion
- **Revenue Growth (YoY)**: 23% (2023 to 2024)
- **Projected Revenue (2025)**: $56-58.5 billion
- **Net Income (2024)**: $1 billion (down 40% from 2023)
- **Net Income (Q1 2025)**: $400 million+
- **Net Profit Margin (Q1 2025)**: ~5%
- **GMV (2024)**: ~$50 billion

### Valuation Information
- **Current Valuation**: $30-45 billion (varies by source and timing)
  - January 2024: $45 billion (secondary market)
  - Mid-2024: $30 billion (seeking London IPO listing)
  - May 2023: $66 billion
- **Previous Valuations**:
  - 2023: $66 billion
  - 2022: $100 billion (peak)
  - 2019: $5 billion
- **Valuation Multiple**: ~0.8-1.2x revenue (at $30-45B range)
- **Total Funding Raised**: $4+ billion

### Key Metrics
- **Active Users**: 88.8 million globally (17.3M in US)
- **Daily Orders**: ~880,000-1,000,000
- **New SKUs Added Daily**: ~2,000
- **Market Share**: 18% of global fast fashion market
- **Employees**: 16,000+
- **Founded**: 2012 (rebranded from SheInside in 2015)
- **Headquarters**: Singapore

### Comparable Public Companies (Suggested)
- Inditex (ITX) - parent of Zara
- H&M (HM-B)
- Fast Retailing (9983.T) - parent of Uniqlo
- Lululemon (LULU)
- Gap (GPS)
- TJX Companies (TJX)

### Example Input for Comps Model
```json
{
  "target_company": {
    "name": "Shein",
    "ticker": null,
    "revenue": 38000000000,
    "ebitda": 1900000000,
    "industry": "Fashion Retail",
    "sector": "E-commerce / Fast Fashion",
    "sic_code": "5961",
    "founded_year": 2012,
    "business_model": "Direct-to-Consumer E-commerce"
  },
  "known_valuation": {
    "amount": 45000000000,
    "date": "2024-01-15",
    "round": "Secondary Market",
    "source": "Secondary market transactions"
  },
  "peer_selection": {
    "method": "industry_based",
    "custom_tickers": ["ITX", "HM-B", "9983.T", "LULU", "GPS", "TJX"],
    "filters": {
      "revenue_range": [10000000000, 100000000000],
      "exclude_negative_ebitda": false,
      "focus_fashion_only": true
    }
  }
}
```

### Data Sources
- Sacra.com, Business of Apps, Priori Data, Financial Times, Bloomberg, Mobiloud
- ECDB, The Motley Fool, SimiCart

---

## Summary Comparison Table

| Company | Industry | 2024 Revenue | Valuation | Val/Rev Multiple | Year Founded |
|---------|----------|--------------|-----------|------------------|--------------|
| Stripe | FinTech | $5.1B | $91.5B | 17.9x | 2010 |
| SpaceX | Aerospace | $14.2B | $350B | 24.6x | 2002 |
| Databricks | Software | $4.0B ARR | $100B | 25.0x | 2013 |
| Canva | Design Software | $3.3B ARR | $42B | 12.7x | 2012 |
| Shein | E-commerce | $38B | $30-45B | 0.8-1.2x | 2012 |

## Notes on Using This Data

### For Testing Your Comps Model:

1. **Expected Valuation Range**: Each company has a known valuation that your model should approximate using comparable public companies

2. **Valuation Multiples Vary by Industry**:
   - High-growth SaaS (Databricks, Stripe): 15-25x revenue
   - Deep tech/Aerospace (SpaceX): 20-25x revenue (premium for market dominance)
   - Consumer software (Canva): 10-15x revenue
   - E-commerce/Retail (Shein): 0.5-2x revenue (lower margins)

3. **Testing Methodology**:
   - Use yfinance to fetch comparable company data
   - Calculate EV/Revenue, EV/EBITDA multiples for peers
   - Apply median multiple to target company's revenue
   - Compare your model's output to the known valuation
   - Document the variance and assumptions

4. **Data Freshness**: This data is current as of November 2025. Market conditions and company financials change rapidly.

5. **DLOM Considerations**: Private company discounts (DLOM - Discount for Lack of Marketability) typically range 20-30%. However, these unicorn valuations are from actual market transactions (secondary sales, tender offers) that already reflect illiquidity discounts.

## Validation Approach

For each company, your audit tool should:

1. **Fetch Comparable Data**: Retrieve financial data for suggested public comparables
2. **Calculate Multiples**: Determine EV/Revenue, EV/EBITDA multiples
3. **Apply to Target**: Use median or mean multiple × target company revenue
4. **Generate Range**: Provide low/mid/high estimates based on different multiples
5. **Compare to Known**: Calculate variance from known valuation
6. **Document Assumptions**: Clearly state peer selection criteria, multiple choice, and adjustments

### Expected Model Performance

Your model should produce estimates within 20-40% of the known valuations, demonstrating:
- Sound methodology
- Appropriate peer selection
- Reasonable multiple calculation
- Clear audit trail

The goal is not perfect accuracy but a consistent, well-documented process that auditors can verify and validate.
