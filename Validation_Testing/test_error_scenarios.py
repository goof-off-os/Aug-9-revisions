#!/usr/bin/env python3
"""
Test Error Scenarios for ProposalOS
====================================
Creates test cases with deliberate errors to validate error tracking
"""

import json
from pathlib import Path
from datetime import datetime

def create_test_kb_with_errors():
    """Generate a KB with various error conditions for testing"""
    
    test_facts = [
        # VALID FACT 1: Properly formatted Travel fact
        {
            "fact_id": "valid_001",
            "element": "Travel",
            "classification": "direct",
            "rfp_relevance": "Travel costs are direct charges to contracts",
            "regulatory_support": [{
                "reg_title": "DFARS - Travel Costs",
                "reg_section": "231.205-46",
                "quote": "Travel costs are the expenses for transportation lodging subsistence",  # 10 words - valid
                "url": "https://www.acquisition.gov/dfars/231.205-46",
                "confidence": 0.85,
                "validated": True
            }],
            "source": {
                "doc_id": "dfars_231_205_46",
                "title": "DFARS - Travel Costs",
                "section": "231.205-46",
                "url": "https://www.acquisition.gov/dfars/231.205-46"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # ERROR 1: Quote exceeds 25 words
        {
            "fact_id": "error_quote_length",
            "element": "G&A",
            "classification": "indirect",
            "rfp_relevance": "G&A allocated per CAS 410",
            "regulatory_support": [{
                "reg_title": "CAS 410",
                "reg_section": "410.50",
                "quote": "G&A expense shall be allocated to final cost objectives by means of a cost input base which represents the total activity of the business unit during a cost accounting period and which has a causal or beneficial relationship between such base and various cost objectives which is way too long for the limit",  # 53 words - TOO LONG
                "url": "https://www.acquisition.gov/cas/410",
                "confidence": 0.7,
                "validated": False
            }],
            "source": {
                "doc_id": "cas_410",
                "title": "CAS 410",
                "section": "410.50",
                "url": "https://www.acquisition.gov/cas/410"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # ERROR 2: Regulatory mismatch (Travel cited from wrong regulation)
        {
            "fact_id": "error_reg_mismatch",
            "element": "Travel",
            "classification": "direct", 
            "rfp_relevance": "Travel is a direct cost",
            "regulatory_support": [{
                "reg_title": "FAR Part 31 - Contract Cost Principles",
                "reg_section": "31.201-2",  # WRONG - should be 31.205-46
                "quote": "A cost is allowable only when it complies with requirements",
                "url": "https://www.acquisition.gov/far/31.201-2",
                "confidence": 0.25,  # Low confidence due to mismatch
                "validated": False
            }],
            "source": {
                "doc_id": "far_31_201_2",
                "title": "FAR Part 31",
                "section": "31.201-2",
                "url": "https://www.acquisition.gov/far/31.201-2"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # ERROR 3: Missing URL attribution
        {
            "fact_id": "error_missing_url",
            "element": "Direct Labor",
            "classification": "direct",
            "rfp_relevance": "Direct labor charged to contracts",
            "regulatory_support": [{
                "reg_title": "FAR Direct Costs",
                "reg_section": "31.202",
                "quote": "Direct costs identified specifically with a contract",
                "url": "",  # MISSING URL
                "confidence": 0.5,
                "validated": False
            }],
            "source": {
                "doc_id": "far_31_202",
                "title": "FAR Direct Costs",
                "section": "31.202",
                "url": ""  # MISSING URL
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # ERROR 4: Low confidence score
        {
            "fact_id": "error_low_confidence",
            "element": "Overhead",
            "classification": "indirect",
            "rfp_relevance": "Overhead is an indirect cost",
            "regulatory_support": [{
                "reg_title": "FAR Indirect Costs",
                "reg_section": "31.203",
                "quote": "Indirect costs incurred for common objectives",
                "url": "https://www.acquisition.gov/far/31.203",
                "confidence": 0.15,  # VERY LOW CONFIDENCE
                "validated": False
            }],
            "source": {
                "doc_id": "far_31_203",
                "title": "FAR Indirect Costs",
                "section": "31.203",
                "url": "https://www.acquisition.gov/far/31.203"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # ERROR 5: Missing regulatory section
        {
            "fact_id": "error_missing_section",
            "element": "Fringe",
            "classification": "indirect",
            "rfp_relevance": "Fringe benefits are indirect costs",
            "regulatory_support": [{
                "reg_title": "FAR Compensation",
                "reg_section": "",  # MISSING SECTION
                "quote": "Compensation for personal services includes fringe benefits",
                "url": "https://www.acquisition.gov/far/31.205-6",
                "confidence": 0.4,
                "validated": False
            }],
            "source": {
                "doc_id": "far_31_205_6",
                "title": "FAR Compensation",
                "section": "",  # MISSING SECTION
                "url": "https://www.acquisition.gov/far/31.205-6"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # ERROR 6: No regulatory support at all
        {
            "fact_id": "error_no_support",
            "element": "Fee",
            "classification": "fee",
            "rfp_relevance": "Fee is profit above costs",
            "regulatory_support": [],  # NO SUPPORT PROVIDED
            "source": {
                "doc_id": "unknown",
                "title": "Unknown Source",
                "section": "",
                "url": ""
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # DUPLICATE 1: Same as valid_001 (for dedup testing)
        {
            "fact_id": "duplicate_001",
            "element": "Travel",
            "classification": "direct",
            "rfp_relevance": "Travel costs are direct charges to contracts",
            "regulatory_support": [{
                "reg_title": "DFARS - Travel Costs",
                "reg_section": "231.205-46",
                "quote": "Travel costs are the expenses for transportation lodging subsistence",
                "url": "https://www.acquisition.gov/dfars/231.205-46",
                "confidence": 0.85,
                "validated": True
            }],
            "source": {
                "doc_id": "dfars_231_205_46",  # SAME source as valid_001
                "title": "DFARS - Travel Costs",
                "section": "231.205-46",  # SAME section
                "url": "https://www.acquisition.gov/dfars/231.205-46"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # VALID FACT 2: Properly formatted G&A fact
        {
            "fact_id": "valid_002",
            "element": "G&A",
            "classification": "indirect",
            "rfp_relevance": "G&A expenses allocated to all contracts",
            "regulatory_support": [{
                "reg_title": "CAS 410 - G&A Allocation",
                "reg_section": "CAS 410.50",
                "quote": "G&A allocated by means of cost input base",  # 9 words - valid
                "url": "https://www.acquisition.gov/cas/410.50",
                "confidence": 0.92,
                "validated": True
            }],
            "source": {
                "doc_id": "cas_410_50",
                "title": "CAS 410",
                "section": "410.50",
                "url": "https://www.acquisition.gov/cas/410.50"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        
        # ERROR 7: Ambiguous classification with multiple issues
        {
            "fact_id": "error_ambiguous",
            "element": "Unknown Cost",
            "classification": "ambiguous",
            "rfp_relevance": "Cannot determine proper treatment",
            "regulatory_support": [{
                "reg_title": "",  # Missing title
                "reg_section": "",  # Missing section
                "quote": "",  # Missing quote
                "url": "",  # Missing URL
                "confidence": 0.0,  # Zero confidence
                "validated": False
            }],
            "source": {
                "doc_id": "unknown",
                "title": "",
                "section": "",
                "url": ""
            },
            "timestamp": ""  # Missing timestamp
        }
    ]
    
    return {
        "schema_version": "1.1.0",
        "extraction_mode": "test_errors",
        "model": "test_harness",
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "facts": test_facts
    }

def create_test_report_markdown():
    """Create a markdown report showing error scenarios"""
    
    return """# ProposalOS Error Testing Scenarios

## Test Cases Overview

This test KB contains **10 facts** with various error conditions:

### ✅ Valid Facts (2)
1. **valid_001**: Properly formatted Travel fact with correct DFARS citation
2. **valid_002**: Properly formatted G&A fact with correct CAS citation

### ❌ Error Scenarios (7)
1. **error_quote_length**: Quote exceeds 25-word limit (53 words)
2. **error_reg_mismatch**: Travel cited from FAR 31.201-2 instead of 31.205-46
3. **error_missing_url**: Missing URL in regulatory support
4. **error_low_confidence**: Confidence score below 0.3 threshold
5. **error_missing_section**: Missing regulation section number
6. **error_no_support**: No regulatory support provided at all
7. **error_ambiguous**: Multiple missing fields and zero confidence

### 🔄 Duplicate Testing (1)
1. **duplicate_001**: Exact duplicate of valid_001 for deduplication testing

## Expected Validation Results

| Check | Expected Failures |
|-------|------------------|
| Quote Length | 1 (error_quote_length) |
| Regulatory Match | 1 (error_reg_mismatch) |
| Missing URL | 2 (error_missing_url, error_ambiguous) |
| Low Confidence | 3 (error_low_confidence, error_ambiguous, error_reg_mismatch) |
| Missing Section | 2 (error_missing_section, error_ambiguous) |
| No Support | 1 (error_no_support) |
| Duplicates | 1 (duplicate_001) |

## Validation Rules Being Tested

1. **Quote Length**: Must be ≤ 25 words
2. **Regulatory Match**: Citations must align with element type
3. **Attribution**: Must have URL, section, and timestamp
4. **Confidence**: Should be ≥ 0.3 for valid facts
5. **Deduplication**: Same (element, class, doc_id, section) = duplicate

## Running the Test

```bash
# Generate test KB
python3 test_error_scenarios.py --output test_kb_with_errors.json

# Analyze with error tracker
python3 error_tracking_dashboard.py --kb test_kb_with_errors.json

# Run through refactored pipeline with strict mode
python3 compile_reports_refactor.py --dry-run --strict
```
"""

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test KB with errors")
    parser.add_argument("--output", default="test_kb_with_errors.json", 
                       help="Output path for test KB")
    parser.add_argument("--report", action="store_true",
                       help="Also generate markdown report")
    args = parser.parse_args()
    
    # Generate test KB
    test_kb = create_test_kb_with_errors()
    output_path = Path(args.output)
    
    with open(output_path, 'w') as f:
        json.dump(test_kb, f, indent=2)
    
    print(f"✅ Test KB with errors saved to: {output_path}")
    print(f"   Contains {len(test_kb['facts'])} test facts with various error conditions")
    
    # Generate report if requested
    if args.report:
        report_path = output_path.with_suffix('.md')
        report_path.write_text(create_test_report_markdown())
        print(f"📄 Test report saved to: {report_path}")
    
    print("\n🔍 To analyze errors, run:")
    print(f"   python3 error_tracking_dashboard.py --kb {output_path}")

if __name__ == "__main__":
    main()