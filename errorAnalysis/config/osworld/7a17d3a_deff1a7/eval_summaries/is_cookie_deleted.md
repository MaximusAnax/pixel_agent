# `is_cookie_deleted`

## Purpose
Check if the cookie is deleted.

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): 7b6c7e24-c58a-49fc-a5bb-d57b80e5b4c3
- Metrics module: `chrome.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
cookie_data → get_cookie_data

## Source excerpt
```python
def is_cookie_deleted(cookie_data, rule):
    """
    Check if the cookie is deleted.
    """

    if rule['type'] == 'domains':
        cookies_domains = [cookie[1] for cookie in cookie_data]
        for domain in rule['domains']:
            for cookies_domain in cookies_domains:
                if compare_urls(domain, cookies_domain):
                    return 0.
        return 1.
    else:
        raise TypeError(f"{rule['type']} not support yet!")
```
