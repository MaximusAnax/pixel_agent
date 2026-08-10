# `check_font_size`

## Purpose
Check if the font size is as expected.

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): af630914-714e-4a24-a7bb-f9af687d3b91
- Metrics module: `chrome.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
chrome_font_size → get_chrome_font_size

## Source excerpt
```python
def check_font_size(font_size, rule):
    """
    Check if the font size is as expected.
    """

    default_font_size = font_size['default_font_size']
    if rule['type'] == 'value':
        return 1. if default_font_size == rule['value'] else 0.
    elif rule['type'] == 'range':
        return 1. if rule['min'] < default_font_size < rule['max'] else 0.
    else:
        raise TypeError(f"{rule['type']} not support yet!")
```
