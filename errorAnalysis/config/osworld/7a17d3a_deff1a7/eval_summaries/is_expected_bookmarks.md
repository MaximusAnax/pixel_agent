# `is_expected_bookmarks`

## Purpose
Checks if the expected bookmarks are in Chrome.

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (2): 2ad9387a-65d8-4e33-ad5b-7580065a27ca, 7a5a7856-f1b6-42a4-ade9-1ca81ca0f263
- Metrics module: `chrome.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
bookmarks → get_bookmarks

## Source excerpt
```python
def is_expected_bookmarks(bookmarks: List[str], rule: Dict[str, Any]) -> float:
    """
    Checks if the expected bookmarks are in Chrome.
    """
    if not bookmarks:
        return 0.
    elif rule['type'] == "bookmark_bar_folders_names":
        bookmark_bar_folders_names = [bookmark['name'] for bookmark in bookmarks['bookmark_bar']['children'] if
                                      bookmark['type'] == 'folder']
        return 1. if set(bookmark_bar_folders_names) == set(rule['names']) else 0.
    elif rule['type'] == "bookmark_bar_websites_urls":
        bookmark_bar_websites_urls = [bookmark['url'] for bookmark in bookmarks['bookmark_bar']['children'] if
                                      bookmark['type'] == 'url']
        return 1. if set(bookmark_bar_websites_urls) == set(rule['urls']) else 0.
    elif rule['type'] == "liked_authors_websites_urls":
        # Check if "liked authors" folder exists
        liked_authors_folder = next((bookmark for bookmark in bookmarks['bookmark_bar']['children'] if
                                     bookmark['type'] == 'folder' and bookmark['name'] == 'Liked Authors'), None)
        if liked_authors_folder:
            # Check if it contains the specified URLs
            logger.info("'Liked Authors' folder exists")
            liked_authors_urls = [bookmark['url'] for bookmark in liked_authors_folder['children'] if
                                  bookmark['type'] == 'url']
            logger.info("Here is the 'Liked Authors' folder's urls: {}".format(liked_authors_urls))

            urls = rule['urls']

            for idx, url in enumerate(urls):
                if isinstance(url, str):
                    urls[idx] = [url]

            combinations = product(*urls)

            for combination in combinations:
                if set(combination) == set(liked_authors_urls):
                    return 1.
            return 0.
        else:
            return 0.
    else:
        raise TypeError(f"{rule['type']} not support yet!")
```
