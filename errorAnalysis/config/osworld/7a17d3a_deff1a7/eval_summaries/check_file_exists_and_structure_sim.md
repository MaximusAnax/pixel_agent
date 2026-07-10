# `check_file_exists_and_structure_sim`

## Purpose
Check if the image has been exported to the desktop
gimp:77b8ab4d-994f-43ac-8930-8ca087d7c4b4

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): 77b8ab4d-994f-43ac-8930-8ca087d7c4b4
- Metrics module: `gimp.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
vm_file → get_vm_file

## Source excerpt
```python
def check_file_exists_and_structure_sim(src_path, tgt_path):
    """
    Check if the image has been exported to the desktop
    gimp:77b8ab4d-994f-43ac-8930-8ca087d7c4b4
    """
    if src_path is None or tgt_path is None:
        return 0.

    # Check if the file exists
    export_file_exists = os.path.isfile(src_path)
    if not export_file_exists:
        return 0.

    # Check whether the target image is the same as the source image
    img_src = Image.open(src_path)
    img_tgt = Image.open(tgt_path)
    structure_same = structure_check_by_ssim(img_src, img_tgt)

    if structure_same:
        return 1.
    else:
        return 0.
```
