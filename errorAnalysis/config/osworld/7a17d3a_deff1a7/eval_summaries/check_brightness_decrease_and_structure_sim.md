# `check_brightness_decrease_and_structure_sim`

## Purpose
Check the brightness of src is lower than tgt and the structures are similar
gimp:7a4deb26-d57d-4ea9-9a73-630f66a7b568

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): 7a4deb26-d57d-4ea9-9a73-630f66a7b568
- Metrics module: `gimp.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
vm_file → get_vm_file

## Source excerpt
```python
def check_brightness_decrease_and_structure_sim(src_path, tgt_path, threshold=0.03):
    """
    Check the brightness of src is lower than tgt and the structures are similar
    gimp:7a4deb26-d57d-4ea9-9a73-630f66a7b568
    """
    if src_path is None or tgt_path is None:
        return 0.

    img_src = Image.open(src_path)
    img_tgt = Image.open(tgt_path)

    # Brightness comparison
    brightness_src = calculate_brightness(img_src)
    brightness_tgt = calculate_brightness(img_tgt)
    brightness_reduced = brightness_tgt > brightness_src

    # print(f"Brightness src: {brightness_src}, tgt: {brightness_tgt}, reduced: {brightness_reduced}")

    # Normalize and compare images
    target_brightness = 128
    img_src_normalized = normalize_brightness(img_src, target_brightness)
    img_tgt_normalized = normalize_brightness(img_tgt, target_brightness)

    structure_same = structure_check_by_mse(img_src_normalized, img_tgt_normalized, threshold=threshold)
    if brightness_reduced and structure_same:
        return 1.
    else:
        return 0.
```
