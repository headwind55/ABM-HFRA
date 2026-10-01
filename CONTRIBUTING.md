# Contributing

## Development setup

Create a virtual environment and install both runtime and development
dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Before submitting a change

1. Keep generated outputs, logs, caches, and local environments out of Git.
2. Add or update tests for behavioral changes.
3. Run `python -m pytest -q` from the repository root.
4. Update user documentation when command options, inputs, or outputs change.

Please keep model assumptions explicit, especially units, timing, stochastic
seeds, flood scenarios, and adaptation-policy switches.
