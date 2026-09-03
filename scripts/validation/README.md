# Before/after validation scripts

Deterministic replays used as the empirical gate for schema changes (see
AGE-687 "Competency-question validation"). They call the in-process gateway of
whichever checkout you run them from, so run each once on `main` and once on
the branch, then diff. Calls are spaced by `CQ_REPLAY_DELAY` seconds (default 3)
to respect upstream rate limits; run one checkout at a time.

```bash
# 1. dataset (once; needs the `datasets` package, not a project dependency)
uv run --with datasets python - <<'PY'
from datasets import load_dataset; import json
rows=[dict(r) for r in load_dataset("open-biosciences/biosciences-competency-questions-sample", split="train")]
json.dump(rows, open("/tmp/cq_dataset.json","w"))
PY

# 2. CQ workflow steps, per checkout
uv run python scripts/validation/cq_replay.py /tmp/cq_dataset.json /tmp/cq_main.json      # on main
uv run python scripts/validation/cq_replay.py /tmp/cq_dataset.json /tmp/cq_branch.json    # on the branch
python scripts/validation/cq_diff.py /tmp/cq_main.json /tmp/cq_branch.json

# 3. strict/list probes, per checkout (file names are <server>.<tool>.<arg>.json)
uv run python scripts/validation/wire_probe.py <snapshot_dir_from_main> /tmp/wire_branch
python scripts/validation/wire_diff.py <snapshot_dir_from_main> /tmp/wire_branch
```

Steps whose arguments depend on a prior result (no literal in the step text)
are skipped and reported as such. `add_memory` steps are never replayed.
