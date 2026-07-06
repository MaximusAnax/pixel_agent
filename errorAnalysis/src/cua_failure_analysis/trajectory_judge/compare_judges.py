"""Compare the 7B judge vs the 32B judge on the overlap of trajectories they both
classified, to estimate how much to trust the 7B labels.

    python compare_judges.py --a ../outputs/classifications.jsonl \
        --b ../outputs/classifications_32b.jsonl --outdir ../outputs

Reports exact primary-mode agreement, category agreement, Cohen's kappa, per-model
agreement, the category confusion matrix (rows=7B, cols=32B), and example
disagreements. Writes outputs/judge_agreement.md.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load(path: Path) -> dict[str, dict]:
    out = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("parse_ok"):
            out[r["uid"]] = r
    return out


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa for two raters over categorical labels."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    labels = sorted({x for p in pairs for x in p})
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    return (po - pe) / (1 - pe) if pe != 1 else 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="../outputs/classifications.jsonl", help="7B judge")
    ap.add_argument("--b", default="../outputs/classifications_32b.jsonl", help="32B judge")
    ap.add_argument("--outdir", default="../outputs")
    args = ap.parse_args()

    A, B = load(Path(args.a)), load(Path(args.b))
    uids = sorted(set(A) & set(B))
    L = ["# Judge agreement: 7B vs 32B", ""]
    L.append(f"- 7B classifications: {len(A)} | 32B: {len(B)} | **overlap compared: {len(uids)}**")
    if not uids:
        L.append("\n_No overlap yet._")
        (Path(args.outdir) / "judge_agreement.md").write_text("\n".join(L))
        print("\n".join(L)); return

    prim = [(A[u]["classification"]["primary_failure_mode"],
             B[u]["classification"]["primary_failure_mode"]) for u in uids]
    cat = [(A[u]["classification"]["category"],
            B[u]["classification"]["category"]) for u in uids]

    agree_prim = sum(1 for a, b in prim if a == b) / len(prim)
    agree_cat = sum(1 for a, b in cat if a == b) / len(cat)
    L += [
        "",
        f"- **Primary-mode exact agreement: {agree_prim:.0%}**  (kappa {cohen_kappa(prim):.2f})",
        f"- **Category agreement (perception/cognitive/other): {agree_cat:.0%}**  (kappa {cohen_kappa(cat):.2f})",
    ]

    # per-model agreement
    L += ["", "## Agreement by agent model", ""]
    by_model = defaultdict(list)
    for u in uids:
        by_model[A[u]["model"]].append(u)
    L.append("| agent model | n | primary agree | category agree |")
    L.append("|---|--:|--:|--:|")
    for m, us in sorted(by_model.items()):
        pa = sum(1 for u in us if A[u]["classification"]["primary_failure_mode"]
                 == B[u]["classification"]["primary_failure_mode"]) / len(us)
        cua = sum(1 for u in us if A[u]["classification"]["category"]
                  == B[u]["classification"]["category"]) / len(us)
        L.append(f"| {m} | {len(us)} | {pa:.0%} | {cua:.0%} |")

    # category confusion (rows = 7B, cols = 32B)
    cats = ["perception_grounding", "cognitive_planning", "other"]
    conf = Counter(cat)
    L += ["", "## Category confusion (rows = 7B, cols = 32B)", "",
          "| 7B \\ 32B | " + " | ".join(cats) + " |", "|---|" + "---|" * len(cats)]
    for r in cats:
        row = " | ".join(str(conf[(r, c)]) for c in cats)
        L.append(f"| {r} | {row} |")

    # where 7B and 32B disagree on category, what did each say
    L += ["", "## Most common category disagreements", ""]
    dis = Counter((a, b) for a, b in cat if a != b)
    for (a, b), n in dis.most_common(8):
        L.append(f"- 7B=`{a}` vs 32B=`{b}`: {n}")

    # example disagreement uids (a few)
    L += ["", "## Example disagreements (uid: 7B → 32B)", ""]
    shown = 0
    for u in uids:
        pa, pb = A[u]["classification"]["primary_failure_mode"], B[u]["classification"]["primary_failure_mode"]
        if pa != pb and shown < 12:
            L.append(f"- `{u}`: {pa} → {pb}")
            shown += 1

    out = Path(args.outdir) / "judge_agreement.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nWrote -> {out}")


if __name__ == "__main__":
    main()
