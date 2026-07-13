# goldTrajectories

Generate **gold reference trajectories** for OSWorld tasks by having a
grounding-only agent replay the **OSWorld-Human** action sequences in a live
OSWorld VM, keeping the runs the OSWorld evaluator marks correct. These verified
trajectories are the reference rubric for judging unguided agents.

- **Guidance source:** [OSWorld-Human](https://github.com/WukLab/osworld-human) —
  each task's `human-ground-truth` is an ordered list of semantic steps
  (`` `CLICK` address bar ``, `` `TYPING` '…' ``, `` `PRESS` 'enter' ``). No
  coordinates → the model only does **grounding**.
- **Grounding model:** UGround-V1-7B (local vLLM, 48 GB GPU) — no API credits.
- **Environment:** live OSWorld VM on Babel via **Apptainer + QEMU/KVM** (no
  Docker), user-mode SLIRP networking. See [`docs/spike_plan.md`](docs/spike_plan.md).
- **Verification:** a run is gold only if the OSWorld task evaluator passes.

Operating contract and boundaries: [`AGENTS.md`](AGENTS.md).

## Layout

```
scripts/    launch_vm.sh (Apptainer+QEMU), spike drivers, sbatch
src/        manual OSWorld provider (attach DesktopEnv to a running VM)
config/     task lists, model/serve config
docs/       spike_plan.md, design notes
data/       compact run summaries (large traces live in external osworld_env/)
```

Large assets (SIF, `Ubuntu.qcow2`, venv, per-run scratch) live outside the repo
under `/data/group_data/mattlab/raghavg3/osworld_env/` and are git-ignored.
