# `exact_match`

## Purpose
(no docstring; see source excerpt)

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): 2ae9ba84-3a0d-4d4c-8338-3a1478dc5fe3
- Metrics module: `general.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
profile_name → get_profile_name

## Source excerpt
```python
def exact_match(result, rules) -> float:
    expect = rules["expected"]
    print(result, expect)

    if result == expect:
        return 1.
    else:
        return 0.
```
