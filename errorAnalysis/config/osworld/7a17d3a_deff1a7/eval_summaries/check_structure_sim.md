# `check_structure_sim`

## Purpose
Check if the structure of the two images are similar
gimp:2a729ded-3296-423d-aec4-7dd55ed5fbb3

## Inputs
See function signature and task evaluator.result / expected.

## Matching rules
See return value in source (typically 0.0 / 1.0 or [0,1] score).

## Common pitfalls
Confirm expected rules in the task JSON; empty getter results often score 0.

## Pilot usage
- Tasks (1): 2a729ded-3296-423d-aec4-7dd55ed5fbb3
- Metrics module: `gimp.py`
- OSWorld commit: `7a17d3abc86d524420ea4ec96752f84d245fea74`

## Getter mapping
vm_file → get_vm_file

## Source excerpt
```python
def check_structure_sim(src_path, tgt_path):
    """
    Check if the structure of the two images are similar
    gimp:2a729ded-3296-423d-aec4-7dd55ed5fbb3
    """
    if src_path is None or tgt_path is None:
        return 0.

    try:
        img_src = Image.open(src_path)
        img_tgt = Image.open(tgt_path)

        if img_src.size != img_tgt.size:
            logging.debug(f"size different: src_path: {src_path}, tgt_path: {tgt_path}")
            return 0.0

        structure_same = structure_check_by_ssim(img_src, img_tgt)
        return 1.0 if structure_same else 0.0

    except Exception as e:
        logging.error(f"check_structure_sim error: {str(e)}")
        return 0.0
```
