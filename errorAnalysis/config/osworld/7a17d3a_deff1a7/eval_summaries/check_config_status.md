# `check_config_status`

## Purpose
Check if the GIMP status is as expected

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (3): 7b7617bd-57cc-468e-9c91-40c4ec2bcb3d, b148e375-fe0b-4bec-90e7-38632b0d73c2, d52d6308-ec58-42b7-a2c9-de80e4837b2b
- Metrics module: `gimp.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
gimp_config_file → get_gimp_config_file

## Source excerpt
```python
def check_config_status(actual_config_path, rule):
    """
    Check if the GIMP status is as expected
    """
    if actual_config_path is None:
        return 0.

    with open(actual_config_path, 'r') as f:
        content = f.readlines()

    for line in content:
        if line.startswith('#') or line == '\n':
            continue
        items = line.strip().lstrip('(').rstrip(')\n').split()
        if isinstance(rule["key"], str):
            if items[0] == rule["key"] and items[-1] == rule["value"]:
                return 1.
        elif isinstance(rule["key"], list) and len(rule["key"]) == 2:
            if items[0] == rule["key"][0] \
                    and items[1] == rule["key"][1] \
                    and items[-1] == rule["value"]:
                return 1.
    return 0.
```
