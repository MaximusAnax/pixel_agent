# `check_include_exclude`

## Purpose
(no docstring; see source excerpt)

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): a746add2-cab0-4740-ac36-c3769d9bfb46
- Metrics module: `general.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
vm_command_line → get_vm_command_line

## Source excerpt
```python
def check_include_exclude(result: str, rules: Dict[str, List[str]]) -> float:
    if result is None:
        return 0.

    print(result, rules)
    include = rules.get("include", [])
    exclude = rules.get("exclude", [])
    if all(r in result for r in include) and all(r not in result for r in exclude):
        return 1.
    else:
        return 0.
```
