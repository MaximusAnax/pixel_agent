# autoResearch loop run `det-grid-001`

- Completed: 2026-08-10T23:34:05Z
- Eval set hash: `20c83ed3cbce3d37` (12 calibration / 5 holdout cases)
- Experiments this session: 55 (kept 2, discarded 52)
- Best candidate: **grid-0008[far_threshold_px=40.0,long_horizon_threshold_ratio=0.85,min_repeat=2,near_margin_ratio=5.0]** (`308d125283a522f3`)
- Best calibration 0.8286 / holdout 0.6000 (macro-F1, multi-label)
- Cost: $0.00 (offline detector executor)

## Kept candidates

- `exp-0003` grid-0002[far_threshold_px=40.0,long_horizon_threshold_ratio=0.7,min_repeat=2,near_margin_ratio=5.0]: calib 0.7810 (Δ+0.0633), holdout 0.5000 [kept] — tier1.py defaults + judge protocol v1
- `exp-0009` grid-0008[far_threshold_px=40.0,long_horizon_threshold_ratio=0.85,min_repeat=2,near_margin_ratio=5.0]: calib 0.8286 (Δ+0.0476), holdout 0.6000 [kept] — tier1.py defaults + judge protocol v1

_Scores are harness-calibration numbers on the pinned eval set — not scientific results. See autoResearch/AGENTS.md boundaries._
