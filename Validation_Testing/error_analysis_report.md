# Detailed Validation Report

## ✅ Valid Facts (7)

- **Travel** (direct)
  - ID: `valid_001`
  - Source: 231.205-46
  - Confidence: 0.85

- **Direct Labor** (direct)
  - ID: `error_missing_url`
  - Source: 31.202
  - Confidence: 0.50

- **Overhead** (indirect)
  - ID: `error_low_confidence`
  - Source: 31.203
  - Confidence: 0.15

- **Fringe** (indirect)
  - ID: `error_missing_section`
  - Source: 
  - Confidence: 0.40

- **Travel** (direct)
  - ID: `duplicate_001`
  - Source: 231.205-46
  - Confidence: 0.85

- **G&A** (indirect)
  - ID: `valid_002`
  - Source: 410.50
  - Confidence: 0.92

- **Unknown Cost** (ambiguous)
  - ID: `error_ambiguous`
  - Source: 
  - Confidence: 0.00


## ❌ Invalid Facts (3)

- **G&A** (indirect)
  - ID: `error_quote_length`
  - Issues:
    - ⚠️ Quote exceeds 25 words (53 words)
  - Source: 410.50

- **Travel** (direct)
  - ID: `error_reg_mismatch`
  - Issues:
    - ⚠️ Regulatory mismatch: Travel cited from 31.201-2
    - ⚠️ Low confidence: 0.25
  - Source: 31.201-2

- **Fee** (fee)
  - ID: `error_no_support`
  - Issues:
    - ⚠️ No regulatory support provided
  - Source: 

