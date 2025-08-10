# ProposalOS Error Testing Scenarios

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
