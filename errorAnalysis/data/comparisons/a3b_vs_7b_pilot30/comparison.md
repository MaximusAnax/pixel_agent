# Multi-Model Failure Prevalence Comparison

- Generated: 2026-06-26T17:32:59
- Models: opencua-a3b, opencua-7b
- Status: provisional (pre human-gold calibration)

## Failure rate (over analyzed pilot episodes)

| Model | Episodes | Failed | Failure rate |
|---|---:|---:|---:|
| opencua-a3b | 30 | 21 | 70% |
| opencua-7b | 30 | 17 | 57% |

## Perception vs Cognitive (share of failures at t*)

| Model | n failures | Perception | Cognitive | Other/Unresolved |
|---|---:|---:|---:|---:|
| opencua-a3b | 21 | 0% | 95% | 1 |
| opencua-7b | 17 | 6% | 82% | 2 |

## Per-leaf prevalence at t* (conditional on failure)

| Leaf | opencua-a3b (CI) | opencua-7b (CI) |
|---|---|---|
| Action Looping (Repetition) | 2/21 10% [3%, 29%] | 4/17 24% [10%, 47%] |
| Click Region Error | 0 | 1/17 6% [1%, 27%] |
| Goal Hallucination | 4/21 19% [8%, 40%] | 3/17 18% [6%, 41%] |
| Location Hallucination | 3/21 14% [5%, 35%] | 0 |
| Reasoning Drift | 11/21 52% [32%, 72%] | 7/17 41% [22%, 64%] |

## Propagation rate (consequence leaves)

| Model | Leaf | n | Propagated | Rate |
|---|---|---:|---:|---:|
| opencua-a3b | Action Looping (Repetition) | 2 | 0 | 0% |
| opencua-a3b | Long-Horizon Memory Failure | 0 | 0 | 0% |
| opencua-7b | Action Looping (Repetition) | 4 | 0 | 0% |
| opencua-7b | Long-Horizon Memory Failure | 0 | 0 | 0% |

## Pilot task overlap (failed task IDs)

- Intersection (failed by all models): 16
- Union (failed by any model): 22

> Denominators differ per model because each model fails on a different subset of tasks. Compare prevalence shares, not raw counts.

