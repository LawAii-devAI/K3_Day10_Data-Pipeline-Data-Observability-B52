# Data Corruption & Repair Impact Report

## Baseline vs Corrupted vs Repaired Comparison

| Metric / Indicator | Baseline | Corrupted | Repaired |
|---|---|---|---|
| **Retrieval Hit Rate** | 1.0000 | 0.6250 | 1.0000 |
| **Mean Token F1** | 1.0000 | 0.5116 | 1.0000 |
| **Judge Accuracy** | 0.9583 | 0.4583 | 0.9583 |
| **Mean Judge Score** | 4.8333 | 3.0833 | 4.8333 |
| **Data Quality Status** | PASSED | FAILED | PASSED |
| **Freshness Status** | FRESH | STALE | FRESH |
| **Stale Rows** | 0 | 5 | 0 |

## Summary Findings
1. **Corruption Impact**: Data quality issues (blank summaries, truncated titles, stale dates) directly impair vector retrieval accuracy and LLM answer quality.
2. **Observability Detection**: Quality checks and freshness checks successfully catch data corruption issues before deployment.
3. **Repair Effectiveness**: Pipeline repair from raw artifacts restores quality checks and brings RAG metrics back to baseline performance.
