# CMU Babel account checklist (secondary cluster)

**Status:** Not yet provisioned — non-blocking for Bridges work.

## Steps

1. [ ] Open LTI intranet → **HPC Cluster User Account Request Form**
2. [ ] Cluster name: `babel`
3. [ ] Enter faculty sponsor / advisor
4. [ ] Complete safety quiz on [hpc.cs.cmu.edu](https://hpc.cs.cmu.edu/)
5. [ ] SSH test: `ssh <andrew_id>@babel.lti.cs.cmu.edu`
6. [ ] Ask advisor for lab partition (e.g. `swl_general`) and group quotas

## When to use Babel vs Bridges

| Workload | Primary |
|---|---|
| vLLM agent + judge | Bridges (`cis260099p`) |
| Overflow GPU jobs | Babel when account active |
| AgentNetBench offline | Either |

## Reuse

Same scripts as Bridges after setting `config/bridges.env` → copy to `config/babel.env` with Babel partition names. SLURM flags differ slightly (`srun` vs `interact`).
