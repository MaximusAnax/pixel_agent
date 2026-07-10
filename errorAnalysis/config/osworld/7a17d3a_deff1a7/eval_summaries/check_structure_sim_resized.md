# `check_structure_sim_resized`

## Purpose
Check if the structure of the two images are similar after resizing.
gimp:d16c99dc-2a1e-46f2-b350-d97c86c85c15

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
def check_structure_sim_resized(src_path, tgt_path):
    """
    Check if the structure of the two images are similar after resizing.
    gimp:d16c99dc-2a1e-46f2-b350-d97c86c85c15
    """
    if src_path is None or tgt_path is None:
        return 0.

    img_src = Image.open(src_path)
    img_tgt = Image.open(tgt_path)

    # Check if source image has transparency and extract content area
    if img_src.mode in ('RGBA', 'LA') or 'transparency' in img_src.info:
        if img_src.mode != 'RGBA':
            img_src = img_src.convert('RGBA')

        # Get alpha channel and find bounding box of non-transparent pixels
        alpha = img_src.split()[-1]
        bbox = alpha.getbbox()

        if bbox is None:
            # Image is completely transparent
            logging.debug("Source image is completely transparent")
            return 0.

        # Crop to content area only
        img_src_content = img_src.crop(bbox)
        logging.debug(f"Source image cropped from {img_src.size} to {img_src_content.size}")

        # Convert to RGB for comparison
        img_src_content = img_src_content.convert('RGB')
        img_src_resized = img_src_content.resize(img_tgt.size)
    else:
        # No transparency, resize normally
        img_src_resized = img_src.resize(img_tgt.size)

    # Ensure target image is RGB for comparison
    if img_tgt.mode != 'RGB':
        img_tgt = img_tgt.convert('RGB')

    # Check if the structure is similar
    structure_same = structure_check_by_ssim(img_src_resized, img_tgt)
    if structure_same:
        return 1.
    else:
        return 0.
```
