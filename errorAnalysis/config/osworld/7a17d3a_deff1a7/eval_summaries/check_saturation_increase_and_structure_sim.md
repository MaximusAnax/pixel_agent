# `check_saturation_increase_and_structure_sim`

## Purpose
Check the saturation of src is higher than tgt and the structures are similar
gimp:554785e9-4523-4e7a-b8e1-8016f565f56a

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): 554785e9-4523-4e7a-b8e1-8016f565f56a
- Metrics module: `gimp.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
vm_file → get_vm_file

## Source excerpt
```python
def check_saturation_increase_and_structure_sim(src_path, tgt_path):
    """
    Check the saturation of src is higher than tgt and the structures are similar
    gimp:554785e9-4523-4e7a-b8e1-8016f565f56a
    """
    if src_path is None or tgt_path is None:
        return 0.

    img_src = Image.open(src_path)
    hsv_img_src = img_src.convert('HSV')
    img_tgt = Image.open(tgt_path)
    hsv_img_tgt = img_tgt.convert('HSV')

    # Saturation comparison
    src_saturation = measure_saturation(hsv_img_src)
    tgt_saturation = measure_saturation(hsv_img_tgt)

    saturation_increased = tgt_saturation < src_saturation

    # Structure comparison
    h1, s1, v1 = hsv_img_src.split()
    h2, s2, v2 = hsv_img_tgt.split()
    h_same = structure_check_by_ssim(h1, h2)
    v_same = structure_check_by_ssim(v1, v2)
    if h_same and v_same:
        structure_same = True
    else:
        structure_same = False

    if saturation_increased and structure_same:
        return 1.
    else:
        return 0.
```
