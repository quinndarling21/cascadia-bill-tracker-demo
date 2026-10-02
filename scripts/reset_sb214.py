#!/usr/bin/env python3
"""Set SB 214's status for a demo run, then rebuild the site.

  python3 scripts/reset_sb214.py                    # Signed by Governor today (Pacific time)
  python3 scripts/reset_sb214.py --date 2026-10-05  # Signed by Governor on a given date
  python3 scripts/reset_sb214.py --state committee  # back to the initial "In committee" state
  python3 scripts/reset_sb214.py --push             # ...then git add -A, commit, and push
"""

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "bills.json"
PACIFIC = ZoneInfo("America/Los_Angeles")

SLUG = "sb-214"
SIGNING_ACTIONS = ["Passed Senate", "Passed House", "Signed by Governor"]
# Restoring the original status-change time also restores the original feed guid,
# so going back to committee doesn't show up as a new item in feed readers.
COMMITTEE_STATE = {
    "status": "In committee",
    "status_date": "2026-01-22",
    "status_changed_at": "2026-01-22T10:15:00-08:00",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", choices=["signed", "committee"], default="signed")
    parser.add_argument(
        "--date", type=date.fromisoformat, metavar="YYYY-MM-DD",
        help="signing date for --state signed (default: today in America/Los_Angeles)",
    )
    parser.add_argument("--push", action="store_true", help="git add -A, commit, and push after rebuilding")
    args = parser.parse_args()

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    bill = next(b for b in data["bills"] if b["slug"] == SLUG)
    before = f"{bill['status']} ({bill['status_date']})"
    history = [entry for entry in bill["history"] if entry["action"] not in SIGNING_ACTIONS]

    if args.state == "signed":
        now = datetime.now(PACIFIC).replace(microsecond=0)
        day = args.date or now.date()
        bill.update(
            status="Signed by Governor",
            status_date=day.isoformat(),
            status_changed_at=datetime.combine(day, now.timetz()).isoformat(),
        )
        history += [{"date": day.isoformat(), "action": action} for action in SIGNING_ACTIONS]
    else:
        bill.update(COMMITTEE_STATE)
    bill["history"] = history

    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if subprocess.run([sys.executable, str(ROOT / "build.py")], stdout=subprocess.DEVNULL).returncode:
        sys.exit("build.py failed; data/bills.json was updated but the site was not rebuilt.")
    print(
        f"SB 214: {before} -> {bill['status']} ({bill['status_date']}), "
        f"status changed at {bill['status_changed_at']}; site rebuilt."
    )

    if args.push:
        for cmd in (["git", "add", "-A"], ["git", "commit", "-m", "Update SB 214 status"], ["git", "push"]):
            if subprocess.run(cmd, cwd=ROOT).returncode:
                sys.exit(f"Stopped: '{' '.join(cmd)}' failed.")


if __name__ == "__main__":
    main()
