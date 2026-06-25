# Hermes Multi-Agent Orchestration: Setup Guide

This guide gets the Phase 1 CUA failure-analysis workflow running through
[Hermes Agent](https://hermes-agent.nousresearch.com/docs/) (Nous Research). Hermes
is the autonomous agent; this project gives it an operating contract
(`AGENTS.md` + `hermes/SOUL.md`), a runnable skill (`hermes/skills/`), and the
Babel scripts (`scripts/babel/`) it drives.

> Run Hermes from the `errorAnalysis/` directory. That is where `AGENTS.md`, the
> scripts, and `config/babel.env` live, and how Hermes auto-discovers the project
> context.

## 0. Mental model

```text
You ── chat (CLI / Telegram / ...) ──▶ Hermes Agent (local laptop or a small VPS)
                                          │  loads AGENTS.md + global SOUL.md
                                          │  loads skill: babel-osworld-analysis
                                          ▼
                                       terminal tool
                                          │  ssh / rsync / sbatch
                                          ▼
                                   CMU Babel (Slurm)  ──▶ /data/user_data outputs
                                          ▲
                          sync_outputs.sh │  pulls compact json/csv/md only
                                          ▼
                                 errorAnalysis/data/babel_outputs/<run_id>
```

Hermes itself does no GPU work. It runs locally and reaches Babel over SSH exactly
like you would by hand. For long Slurm waits, use `caffeinate -dims` on macOS so
background polls are not killed by sleep (see section 9).

## 1. Install Hermes

macOS / Linux / WSL2:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

(Or install the Hermes Desktop app from the website.) Then verify:

```bash
hermes --version
```

Docs: [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation).

## 2. Connect a model (fastest path)

```bash
hermes setup --portal
```

One OAuth via [Nous Portal](https://hermes-agent.nousresearch.com/docs/) provisions
a model plus the Tool Gateway (web search, image gen, TTS, browser). You can
instead point Hermes at OpenRouter / OpenAI / Anthropic / any OpenAI-compatible
endpoint — see
[Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
and [Configuring Models](https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models).

Sanity check:

```bash
cd ~/Documents/School/Research/pixelAgent/errorAnalysis
hermes chat -q "What project context did you load?"
```

Hermes should echo back facts from `AGENTS.md` (Phase 1, Babel, boundaries).

## 3. Context files: why `hermes/SOUL.md` is not enough

Hermes loads context in a specific way (see
[Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)):

| File | Loaded from | Role |
|---|---|---|
| `AGENTS.md` | working dir at startup + subdirs | **project instructions** (auto-loaded) |
| `.hermes.md` | walks to git root | project instructions (highest priority) |
| `SOUL.md` | **`~/.hermes/SOUL.md` only** | global personality/tone |

Key consequence: **Hermes never reads `SOUL.md` from the project directory.** So
`errorAnalysis/hermes/SOUL.md` is documentation for humans; it is the project
`AGENTS.md` (already created in this branch) that Hermes actually injects every
turn.

Optional personality: copy the tone/posture bits you like into the global file so
Hermes carries the right voice everywhere:

```bash
mkdir -p ~/.hermes
# edit ~/.hermes/SOUL.md — keep it about voice/identity, not project mechanics
```

Project mechanics belong in `AGENTS.md`; identity/voice belongs in `~/.hermes/SOUL.md`.
See [Use SOUL.md with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes).

## 4. Babel prerequisites (one-time)

1. SSH config so Hermes (and you) can reach login + compute nodes. Add to
   `~/.ssh/config` (from the Babel quickstart guide):

   ```ssh-config
   Host babel
     HostName login.babel.cs.cmu.edu
     User andiongu
     IdentityFile ~/.ssh/id_ed25519
     StrictHostKeyChecking no

   Host babel-*
     HostName %h
     User andiongu
     IdentityFile ~/.ssh/id_ed25519
     ProxyJump babel
     StrictHostKeyChecking no
   ```

   Confirm key-based, non-interactive login works: `ssh babel true && echo ok`.
   (Hermes runs commands non-interactively; a password prompt will hang it.)

2. Project Babel config (git-ignored):

   ```bash
   cd errorAnalysis
   cp config/babel.env.example config/babel.env   # edit only if account/paths change
   ```

3. Sync code, then create the remote Python env:

   ```bash
   # Syncs the repo; exits with setup instructions if .venv is not on Babel yet
   scripts/babel/submit_hf_analysis.sh || true

   ssh babel
   cd /home/andiongu/cua-failure-analysis && scripts/babel/setup_env.sh
   exit
   ```

   **Order matters:** sync first (any `submit_hf_analysis.sh` run does this), then
   `setup_env.sh` once. Later submits sync code but **preserve** `.venv` (rsync
   excludes it). `submit_hf_analysis.sh` refuses to queue Slurm if the venv is missing.

Full background: [docs/babel_hf_orchestration.md](babel_hf_orchestration.md).

## 5. Toolsets, security, and SSH passthrough

- Hermes needs the **terminal** (and file) toolset to run the scripts. The bundled
  `terminal`/`file` toolsets are on by default in `hermes chat`.
- `ssh`, `rsync`, and `sbatch` will trigger Hermes' dangerous-command approval the
  first time. Approve them (or pre-authorize) per
  [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security). On a
  VPS you may relax approvals; on your laptop keep them on at first.
- If you run Hermes in a Docker/Modal backend, make sure your SSH key and
  `config/babel.env` reach the sandbox. Locally this is automatic. See
  `terminal.env_passthrough` in
  [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration).

## 6. Install the Babel skill

The repo ships a skill at `hermes/skills/babel-osworld-analysis/SKILL.md` that
encodes the submit → poll → sync procedure. Hermes only discovers skills under
`~/.hermes/skills/<category>/<skill>/` (two levels deep), so you must place it
there — pointing config at the repo path is **not** enough.

1. Link (or copy) the skill into your Hermes skills directory. A symlink keeps it
   in sync with the repo as you edit it:

   ```bash
   ln -s ~/Documents/School/Research/pixelAgent/errorAnalysis/hermes/skills/babel-osworld-analysis \
     ~/.hermes/skills/research/babel-osworld-analysis
   ```

   (Use `cp -R` instead of `ln -s` if you prefer a snapshot over a live link.)

2. Confirm Hermes sees it:

   ```bash
   hermes skills list | grep babel
   # → babel-osworld-analysis  │ research │ local │ ... │ enabled
   ```

3. (Optional) set the project dir the skill reads — this is a *value the skill
   consumes after it loads*, not how it is discovered:

   ```bash
   hermes config set skills.config.babel.project_dir \
     ~/Documents/School/Research/pixelAgent/errorAnalysis
   ```

4. Test it loads (skills take effect in a *new* session, which `hermes chat -q`
   starts; inside an existing session use `/reset` or `--now`):

   ```bash
   hermes chat --toolsets skills,terminal,file \
     -q "Use the babel-osworld-analysis skill to list the priority packages."
   ```

   It should `skill_view` the skill, read `config/hf_osworld_packages.yaml`, and
   list the packages with `opencua_a3b_15` as the default smoke-test target.

> If Hermes replies "that skill doesn't exist," the skill is not in
> `~/.hermes/skills/`. Re-check step 1 — the most common mistake is only running
> the `hermes config set ...` from step 3.

Even without the skill, `AGENTS.md` already tells Hermes the workflow — the skill
just makes it crisper and reusable. See
[Work with Skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills).

## 7. Run it end to end (smoke test)

From `errorAnalysis/`, in a Hermes chat:

```text
Submit the OpenCUA A3B 15-step smoke-test package to Babel, then poll for
completion in the background and notify me. When it finishes, sync the outputs
and summarize summary.md and adapter_gaps.json.
```

Hermes should:

1. run `scripts/babel/submit_hf_analysis.sh opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step.zip` and capture the run id;
2. start a background poll with `scripts/babel/wait_for_run.sh <job_id> <run_id>`
   (NOT a bare `until summary.md` loop — failed jobs never create that file);
3. run `scripts/babel/sync_outputs.sh <run_id>`;
4. read `data/babel_outputs/<run_id>/summary.md` and report using the Output
   Standard in `AGENTS.md`.

## 8. Multi-agent orchestration patterns

- **Parallel packages** — analyze several models at once with `delegate_task`, one
  subagent per package, `toolsets=["terminal","file"]`. Each child only *submits*
  (fast) and returns its run id; the parent does the long wait + sync. Pass each
  child the absolute project path and exact command (subagents have no shared
  history). See
  [Delegation Patterns](https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns).
- **Durable waits** — Slurm jobs outlive a turn. `delegate_task` is synchronous and
  is discarded if the turn is interrupted, so use `cronjob` or
  `terminal(background=True, notify_on_complete=True)` for the wait. See
  [Cron Jobs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron).
- **Laptop polling** — background SSH polls die if the Mac sleeps. Before a long
  wait, run `caffeinate -dims` in a terminal (or `caffeinate -dims &` in the same
  shell) to prevent deep sleep while Hermes polls. If the laptop did sleep, Hermes
  should re-check `squeue` / remote logs on wake rather than assuming the poll is
  still alive.
- **Collapse mechanical steps** — use `execute_code` to chain submit → poll → sync
  in one inference call when no reasoning is needed between steps.
- **Concurrency** — bump `delegation.max_concurrent_children` in `config.yaml` if
  you want more than 3 packages in flight at once.

## 9. Keeping polls alive on a laptop

For long Slurm waits while Hermes runs locally, prevent macOS deep sleep so
background SSH polls stay connected:

```bash
caffeinate -dims
```

Leave that running in a terminal for the duration of the job (or start it in the
background before asking Hermes to poll). If the machine did sleep, ask Hermes to
check remote job state directly (`squeue`, Slurm logs) — the Babel job keeps running;
only the local poll died.

(Optional later: run Hermes on a small always-on VPS so polls survive without
`caffeinate` — see section 8 and
[Messaging](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/index).)

## Troubleshooting

| Symptom | Fix |
|---|---|
| Hermes ignores project rules | You launched outside `errorAnalysis/`; `cd` in, or add `.hermes.md` at the path. Confirm with "what context did you load?" |
| SSH command hangs | Non-interactive key auth not set up; test `ssh babel true`. |
| `/data/...` looks empty | AutoFS — paths mount when `stat`'d on a compute node; the scripts handle this. |
| `--gres` rejected | Must include a GPU type: `gpu:L40S:1`, set `BABEL_GPU_TYPE`. |
| `oom_kill` | CPU RAM, not HBM — raise `BABEL_MEM`. |
| `ModuleNotFoundError: huggingface_hub` (or similar) | Remote `.venv` missing. On Babel: `cd /home/andiongu/cua-failure-analysis && scripts/babel/setup_env.sh`. `submit_hf_analysis.sh` now refuses to submit without a venv. |
| Background poll died / no notification | Laptop slept — use `caffeinate -dims` during waits, or ask Hermes to re-check `squeue` and remote logs. |
| Poll runs for hours, job already gone | Job failed without writing `summary.md`. Use `wait_for_run.sh` (checks `sacct`); inspect `logs/cua-hf-analysis-<job_id>.err`. |
| `wait_for_run` errors but log says Analysis complete | False alarm — outputs are on compute storage. Run `sync_outputs.sh <run_id>`. |
| Subagent "lost" the Slurm job | It was a synchronous child; use cron/background terminal for the wait. |

## Next-steps checklist (to "fully working")

- [x] `AGENTS.md` project context (this branch).
- [x] `babel-osworld-analysis` skill (this branch).
- [x] Install Hermes + `hermes setup --portal`.
- [x] `~/.ssh/config` babel/ProxyJump block; verify `ssh babel true`.
- [x] `cp config/babel.env.example config/babel.env`.
- [x] Sync code to Babel, then one-time `scripts/babel/setup_env.sh` (creates `.venv`).
- [x] Install/tap the skill; `hermes config set skills.config.babel.project_dir ...`.
- [ ] Smoke test (section 7) on the OpenCUA A3B 15-step package.
- [ ] Use `caffeinate -dims` during long polls so the laptop does not sleep.
- [ ] (Optional) add a package-specific adapter once a zip layout is confirmed,
      then enable a calibrated judge (GPU run) — see
      [babel_hf_orchestration.md](babel_hf_orchestration.md).
