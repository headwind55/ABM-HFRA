"""Run adaptation policy 1 (insurance only) for MED seeds 1-10 and four SSPs.

At most five simulations run concurrently across the complete scenario/seed
grid. Policy 1 enables insurance take-up and disables disaster relocation
while retaining flood exposure and loss calculation. Seed 1 uses
Task_ID_MED_POLICY1_<SCENARIO>; seeds 2-10 use unique task directories.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runtime" / "output"
LOGS = ROOT / "runtime" / "logs" / "policy_1_seed_ensemble"
MANIFEST = ROOT / "runtime" / "analysis" / "MED_policy_1_seed_ensemble_manifest.csv"
SCENARIOS = ("SSP126", "SSP245", "SSP370", "SSP585")
SEEDS = tuple(range(1, 11))
POLICY_SCENARIO = "1"


def task_id(seed: int, scenario: str) -> str:
    return f"MED_POLICY1_{scenario}" if seed == 1 else f"MED_POLICY1_S{seed:02d}_{scenario}"


def output_dir(seed: int, scenario: str) -> Path:
    return OUTPUT / f"Task_ID_{task_id(seed, scenario)}"


def completed(seed: int, scenario: str) -> bool:
    return (output_dir(seed, scenario) / "Pop_household_2100_seed.txt").exists()


def run_one(seed: int, scenario: str) -> dict[str, object]:
    destination = output_dir(seed, scenario)
    if completed(seed, scenario):
        return {"seed": seed, "scenario": scenario, "task_id": task_id(seed, scenario),
                "status": "reused_existing", "returncode": 0, "output_dir": str(destination)}

    command = [sys.executable, "Abm_Main_apply.py", "--seed", str(seed),
               "--task-id", task_id(seed, scenario), "--demographic-case", "Medium_case",
               "--no-log", "--policy-scenario", POLICY_SCENARIO,
               "--disaster-year", "2020", "--disaster-scenario", scenario]

    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"seed{seed:02d}_{scenario}.log"
    err_path = LOGS / f"seed{seed:02d}_{scenario}.err.log"
    with log_path.open("w", encoding="utf-8") as stdout, err_path.open("w", encoding="utf-8") as stderr:
        result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    status = "completed" if result.returncode == 0 and completed(seed, scenario) else "failed"
    return {"seed": seed, "scenario": scenario, "task_id": task_id(seed, scenario),
            "status": status, "returncode": result.returncode, "output_dir": str(destination)}


def write_manifest(rows: list[dict[str, object]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    order = {scenario: i for i, scenario in enumerate(SCENARIOS)}
    rows = sorted(rows, key=lambda row: (order[str(row["scenario"])], int(row["seed"])))
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["seed", "scenario", "task_id", "status", "returncode", "output_dir"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    all_rows = []
    # Limit total concurrency to five to avoid CPU and disk oversubscription.
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(run_one, seed, scenario): (seed, scenario)
            for seed in SEEDS
            for scenario in SCENARIOS
        }
        for future in as_completed(futures):
            row = future.result()
            all_rows.append(row)
            write_manifest(all_rows)
            print(f"[{row['scenario']}] seed {row['seed']:02d}: {row['status']}", flush=True)

    write_manifest(all_rows)
    failures = [row for row in all_rows if row["status"] == "failed"]
    if failures:
        raise SystemExit(f"{len(failures)} run(s) failed; see {MANIFEST}")
    print(f"All {len(SEEDS) * len(SCENARIOS)} policy-1 runs available. Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
