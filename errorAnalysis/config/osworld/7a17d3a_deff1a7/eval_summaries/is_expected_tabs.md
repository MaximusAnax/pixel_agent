# `is_expected_tabs`

## Purpose
Check that Chrome open-tab URLs match the expected URL list (order-sensitive via are_lists_equal + compare_urls).

## Inputs
open_tabs (list of {url,...} from get_open_tabs_info); rule with type=url and urls=[...].

## Matching rules
Returns 1.0 iff expected and actual URL lists are equal under compare_urls; else 0.0.

## Common pitfalls
Trailing slashes / www / redirects can fail compare_urls; empty open_tabs → 0.0; order matters.

## Pilot usage
- Tasks (1): 06fe7178-4491-4589-810f-2e2bc9502122
- Metrics module: `chrome.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
open_tabs_info → get_open_tabs_info

## Source excerpt
```python
def is_expected_tabs(open_tabs: List[Dict[str, str]], rule: Dict[str, Any]) -> float:
    """
    Checks if the expected tabs are open in Chrome.
    """
    if not open_tabs:
        return 0.

    match_type = rule['type']

    if match_type == "url":
        expected_urls = rule['urls']
        actual_urls = [tab['url'] for tab in open_tabs]
        if not are_lists_equal(expected_urls, actual_urls, compare_urls):
            logger.error("list not match") 
            logger.error(expected_urls)
            logger.error(actual_urls)
            return 0
        return 1 if are_lists_equal(expected_urls, actual_urls, compare_urls) else 0
    else:
        logger.error(f"Unknown type: {match_type}")
        return 0
```
