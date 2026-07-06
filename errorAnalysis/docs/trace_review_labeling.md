# Trace Review Labeling (abdoul + raghav)

Multi-annotator workflow for taxonomy discovery on paired pilot traces. Judge labels are frozen in `packet_manifest.json`; human labels live in a shared `annotations.json` on Babel.

## Registered annotators

| ID | Who |
|---|---|
| `abdoul` | Abdoul |
| `raghav` | Raghav |

Always pass your ID to `--annotator`. Saves only touch your namespace in `annotations.json`.

## Where state lives

| Artifact | Source of truth | How to sync |
|---|---|---|
| Code, scripts, this doc | **GitHub** (laptops) + **Babel shared clone** | `git pull` locally; `scripts/babel/sync_shared_repo.sh pull` on Babel |
| `config/babel.env` | **Your laptop** (+ copy secrets to `~/.pixel_agent/babel.env` on Babel for API keys) | Never commit |
| Full repo on Babel | **`/data/group_data/mattlab/pixel_agent/pixelAgent/`** | `init_shared_project.sh` once; `sync_shared_repo.sh pull` daily |
| Analysis outputs | **`.../pixel_agent/outputs/<run_id>/`** | `scripts/babel/sync_outputs.sh` |
| HTML packet (~368MB) | **`.../pixel_agent/review_packets/`** | `scripts/babel/sync_review_packet.sh` |
| Human labels | **`.../pixel_agent/review_annotations/`** | `scripts/babel/sync_annotations.sh` |
| Active packet ID | **Babel** `REVIEW_STATE.md` | After packet build |
| Agreement reports | **Local** (optional git commit) | `report_discovery_agreement.py` |

Group data is on **compute nodes only**. Sync scripts mirror through home staging via `srun` so login-node rsync works.

### Babel paths (mattlab)

```
/data/group_data/mattlab/pixel_agent/
  pixelAgent/                         # full git clone (errorAnalysis/, ops/, AGENTS.md)
  outputs/<run_id>/                   # shared HF analysis runs
  review_packets/<packet_id>/
  review_annotations/<packet_id>/annotations.json
  labeling/                           # optional worksheet snapshots
  .venv/                              # shared Python env
  REVIEW_STATE.md
  BABEL_SETUP.md
```

Per-user HF cache (not shared): `/data/group_data/mattlab/$USER/`

## Two copies of the repo (don't mix them up)

| Copy | Location | Purpose |
|---|---|---|
| **Your laptop** | `~/.../pixelAgent/` | Scripts, local server, browser UI — you `git clone` here |
| **Babel shared** | `/data/group_data/mattlab/pixel_agent/pixelAgent/` | Cluster jobs, shared outputs — created by `init_shared_project.sh` |

You **do not** SSH into Babel and run `git clone` in the group directory yourself.  
`init_shared_project.sh` runs **from your laptop**; it SSHs to Babel and clones on a compute node.

Labeling happens on your **laptop** (`serve_review_packet.py` + browser). Only `annotations.json` syncs to Babel.

## Setup checklist

### A. Each person — on your laptop

Run these in `pixelAgent/errorAnalysis` on **your own machine** (abdoul and raghav both do this):

```bash
git clone git@github.com:MaximusAnax/pixel_agent.git
cd pixelAgent/errorAnalysis
git checkout feat/starting-failure-analysis && git pull

cp config/babel.env.example config/babel.env
# Set BABEL_USER to YOUR Babel username (andiongu vs raghav's account)
```

Verify SSH from your laptop:

```bash
source config/babel.env
ssh $BABEL_LOGIN
```

Pull the HTML review packet to your laptop once (~368MB, for the browser UI):

```bash
scripts/babel/sync_review_packet.sh pilot_taxonomy_paired_20260703
```

### B. Once for the lab — only one person runs this

**Either abdoul or raghav**, not both. Run from **your laptop** in `errorAnalysis/`:

```bash
source config/babel.env
scripts/babel/init_shared_project.sh
```

This creates the shared dirs, clones `pixelAgent` on Babel, and builds the shared `.venv`.

The other person skips this step. To confirm it worked:

```bash
scripts/babel/sync_shared_repo.sh status
```

#### If `init_shared_project.sh` fails with "Host key verification failed"

This is **not** your laptop GitHub token. The clone runs on a **Babel compute node** via SSH
(`git@github.com:...`). Laptop env vars are not used there.

**Option 1 — SSH on Babel (recommended):** on the login node once:

```bash
ssh $BABEL_LOGIN
mkdir -p ~/.ssh && chmod 700 ~/.ssh
ssh-keyscan -t ed25519,rsa github.com >> ~/.ssh/known_hosts
ssh -T git@github.com   # must succeed; add ~/.ssh/id_ed25519.pub to GitHub if needed
```

Then re-run `init_shared_project.sh` from your laptop. The updated script also runs
`ssh-keyscan` automatically; you still need a **Babel SSH key** registered on GitHub.

**Option 2 — HTTPS + token (private repo):** in local `config/babel.env` only:

```bash
export BABEL_SHARED_GIT_URL=https://github.com/MaximusAnax/pixel_agent.git
export BABEL_GIT_TOKEN=ghp_...   # fine-grained or classic PAT with repo read
```

**Option 3 — public repo:** use HTTPS without a token:

```bash
export BABEL_SHARED_GIT_URL=https://github.com/MaximusAnax/pixel_agent.git
```

If a partial clone was left behind, remove it on a compute node before retrying:

```bash
rm -rf /data/group_data/mattlab/pixel_agent/pixelAgent
```

### C. Abdoul only — if the packet is not on Babel yet

```bash
git push
scripts/babel/sync_shared_repo.sh pull
PACKET_ID=pilot_taxonomy_paired_20260703 scripts/babel/build_review_packet.sh
```

Then **each person** runs `sync_review_packet.sh` (step A) to pull the packet locally.

## Before Babel analysis jobs or packet rebuilds

From your laptop (whoever is submitting):

```bash
git push
scripts/babel/sync_shared_repo.sh pull
```

Not required for everyday labeling if you only `git pull` on your laptop.

## Every labeling session — Abdoul

All commands run on **your laptop** in `pixelAgent/errorAnalysis`:

```bash
source config/babel.env
git pull

scripts/babel/sync_annotations.sh pull pilot_taxonomy_paired_20260703

python scripts/serve_review_packet.py pilot_taxonomy_paired_20260703 \
  --annotator abdoul --babel-sync

# Open http://127.0.0.1:8765/index.html
```

**Rules:** always `--annotator abdoul`; pull annotations before each session; do not edit `packet_manifest.json`.

## Every labeling session — Raghav

Same as above, replacing `--annotator raghav`.

## After both label a batch

```bash
source config/babel.env
scripts/babel/sync_annotations.sh pull pilot_taxonomy_paired_20260703

python scripts/report_discovery_agreement.py \
  --manifest data/review_packets/pilot_taxonomy_paired_20260703/packet_manifest.json \
  --annotations data/review_packets/pilot_taxonomy_paired_20260703/annotations.json

python scripts/export_discovery_comparison.py \
  --manifest data/review_packets/pilot_taxonomy_paired_20260703/packet_manifest.json \
  --annotations data/review_packets/pilot_taxonomy_paired_20260703/annotations.json \
  --output data/labeling/discovery_comparison_abdoul_raghav.csv
```

## Conflict avoidance

- **Pull before session** so you see your partner's latest labels (read-only on index).
- Saves merge by annotator key — abdoul and raghav never overwrite each other.
- Push creates timestamped `.bak` on Babel.

## Schema (annotations.json v2)

```json
{
  "schema_version": 2,
  "packet_id": "pilot_taxonomy_paired_20260703",
  "annotators": {
    "abdoul": { "labels": { "a3b/chrome__uuid": { "modes_ordered": ["..."], ... } } },
    "raghav": { "labels": {} }
  }
}
```

Primary mode for agreement = first entry in `modes_ordered`.

## Related docs

- [babel_hf_orchestration.md](babel_hf_orchestration.md) — Babel storage and Slurm
- [AGENTS.md](../../AGENTS.md) — project boundaries
