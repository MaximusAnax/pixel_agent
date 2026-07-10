# `match_in_list`

## Purpose
(no docstring; see source excerpt)

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): bb5e4c0d-f964-439c-97b6-bdb9747de3f4
- Metrics module: `general.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
default_search_engine → get_default_search_engine

## Source excerpt
```python
def match_in_list(result, rules) -> float:
    expect = rules["expected"]
    print(result, expect)

    if result in expect:
        return 1.
    else:
        return 0.
```
