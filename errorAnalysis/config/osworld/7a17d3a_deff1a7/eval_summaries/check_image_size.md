# `check_image_size`

## Purpose
Check if the size of the src image is correct
multi-apps:42f4d1c7-4521-4161-b646-0a8934e36081

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): d16c99dc-2a1e-46f2-b350-d97c86c85c15
- Metrics module: `gimp.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
vm_file → get_vm_file

## Source excerpt
```python
def check_image_size(src_path, rule):
    """
    Check if the size of the src image is correct
    multi-apps:42f4d1c7-4521-4161-b646-0a8934e36081
    """
    if src_path is None:
        return 0.

    # Load the image
    img = Image.open(src_path)

    # Check if we should ignore transparent parts
    ignore_transparent = rule.get("ignore_transparent", False)

    if ignore_transparent and img.mode in ('RGBA', 'LA') or 'transparency' in img.info:
        # Calculate bounding box of non-transparent pixels
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Get alpha channel
        alpha = img.split()[-1]

        # Find bounding box of non-transparent pixels
        bbox = alpha.getbbox()

        if bbox is None:
            # Image is completely transparent
            actual_width = 0
            actual_height = 0
        else:
            # Calculate actual content size
            actual_width = bbox[2] - bbox[0]
            actual_height = bbox[3] - bbox[1]

        logging.debug(f"Original size: {img.size}, Content size: {actual_width}x{actual_height}")
    else:
        # Use original image size
        actual_width = img.size[0]
        actual_height = img.size[1]
        logging.debug(f"Image size: {img.size}")

    # Check the size
    if rule.get("height", None) is not None:
        height_same = actual_height == rule["height"]
    else:
        height_same = True
    if rule.get("width", None) is not None:
        width_same = actual_width == rule["width"]
    else:
        width_same = True

    if height_same and width_same:
        logging.debug(f"height_same: {height_same}, width_same: {width_same}")
        return 1.
    else:
        logging.debug(f"height_same: {height_same}, width_same: {width_same}")
        return 0.
```
