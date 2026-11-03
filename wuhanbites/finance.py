from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from .common import ROOT

FIELDS = ["date", "kind", "amount", "platform", "note"]


def ledger_path() -> Path:
    p = ROOT / "data" / "ledger.csv"
    p.parent.mkdir(exist_ok=True)
    return p


def add_entry(kind: str, amount: float, note: str = "", platform: str = "",
              path: Path | None = None) -> None:
    if kind not in ("income", "cost"):
        raise ValueError("kind must be 'income' or 'cost'")
    path = path or ledger_path()
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date": date.today().isoformat(), "kind": kind,
                    "amount": f"{amount:.2f}", "platform": platform, "note": note})


def summarize(path: Path | None = None) -> dict:
    path = path or ledger_path()
    totals = {"income": 0.0, "cost": 0.0}
    if path.exists():
        with path.open() as f:
            for row in csv.DictReader(f):
                totals[row["kind"]] += float(row["amount"])
    return {**totals, "net": round(totals["income"] - totals["cost"], 2)}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="wuhanbites.finance")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--kind", required=True, choices=["income", "cost"])
    a.add_argument("--amount", required=True, type=float)
    a.add_argument("--note", default="")
    a.add_argument("--platform", default="")
    sub.add_parser("summary")
    args = ap.parse_args(argv)
    if args.cmd == "add":
        add_entry(args.kind, args.amount, args.note, args.platform)
        print("recorded")
    else:
        s = summarize()
        print(f"income {s['income']:.2f} | cost {s['cost']:.2f} | net {s['net']:.2f}")


if __name__ == "__main__":
    main()
