# Parser Parity Report

Date: 2026-04-21

Comparison of legacy (pre-WP1.1) parser against new parser with pre-clean stage.

## Summary

- **Regressions**: 0 (PASS)
- **Total improvements**: 0

## Per-Tag Statistics

### WINNER

| Metric | Legacy | New |
| --- | --- | --- |
| tag_match | 241 | 241 |
| open_tag_recovery | 0 | 0 |
| heuristic_recovery | 396 | 396 |
| missing | 804 | 804 |
| **Regressions** | - | **0** |
| **Improvements** | - | **0** |

### REASON

| Metric | Legacy | New |
| --- | --- | --- |
| tag_match | 637 | 637 |
| open_tag_recovery | 0 | 0 |
| heuristic_recovery | 0 | 0 |
| missing | 804 | 804 |
| **Regressions** | - | **0** |
| **Improvements** | - | **0** |

### CHOICE

| Metric | Legacy | New |
| --- | --- | --- |
| tag_match | 396 | 396 |
| open_tag_recovery | 0 | 0 |
| heuristic_recovery | 99 | 99 |
| missing | 946 | 946 |
| **Regressions** | - | **0** |
| **Improvements** | - | **0** |

### RESPONSE

| Metric | Legacy | New |
| --- | --- | --- |
| tag_match | 396 | 396 |
| open_tag_recovery | 296 | 296 |
| heuristic_recovery | 59 | 59 |
| missing | 690 | 690 |
| **Regressions** | - | **0** |
| **Improvements** | - | **0** |

### FACTS

| Metric | Legacy | New |
| --- | --- | --- |
| tag_match | 359 | 359 |
| open_tag_recovery | 14 | 14 |
| heuristic_recovery | 0 | 0 |
| missing | 1068 | 1068 |
| **Regressions** | - | **0** |
| **Improvements** | - | **0** |

## Improvements Detail

Cases where legacy parser failed but new parser recovered a value.
Showing first 20 improvements with before/after excerpts.
