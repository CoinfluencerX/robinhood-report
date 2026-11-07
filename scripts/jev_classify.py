"""Run the JEV classification step on Franklin's Mac through Operation Jarvis's approved adapter.

Run it the way Jarvis runs reviewed scripts, inside the installed Hermes runtime (installs nothing):

    cd ~/Developer/operation-jarvis
    python3 tools/runtime_entry.py ~/Developer/robinhood-report/scripts/jev_classify.py \
        --jarvis ~/Developer/operation-jarvis --build ~/Developer/robinhood-report/data/build.json \
        --out ~/Developer/robinhood-report/data/jev.json

Uses the same phoebe profile, credential pool (in memory only) and $1/day budget ledger as the Jev MCP.
5 tickers = 5 classify requests = 5 reservations ($0.05 reserved, actual cost a tiny fraction).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--jarvis", required=True, help="path to operation-jarvis")
    ap.add_argument("--build", required=True, help="data/build.json from `rhreport build`")
    ap.add_argument("--out", required=True)
    ap.add_argument("--proxy-credential", action="store_true",
                    help="cloud mode: the network proxy injects the OpenRouter key; use --ledger for the budget ledger")
    ap.add_argument("--ledger", help="budget ledger path for --proxy-credential mode (same $1/day, 200-attempt rules)")
    args = ap.parse_args(argv)
    if args.proxy_credential and not args.ledger:
        ap.error("--proxy-credential needs --ledger")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(args.jarvis).expanduser() / "tools"))
    import jev_decisions
    import jev_mcp
    from rhreport import jev

    if args.proxy_credential:
        # The key never enters this process: the proxy overwrites the Authorization header for openrouter.ai.
        ledger = jev_decisions.BudgetLedger(str(Path(args.ledger).expanduser()))
        supplier = lambda: "proxy-injected-placeholder"  # noqa: E731
    else:
        home = jev_mcp.APPROVED_HOME
        os.environ["HERMES_HOME"] = home
        ledger = jev_decisions.BudgetLedger(os.path.join(home, "state", "jev-budget.sqlite3"))
        supplier = jev_mcp.make_credential_supplier(jev_mcp._load_pool)
    client = jev_decisions.DecisionClient(transport=jev_decisions.UrllibTransport(), credential_supplier=supplier,
                                          ledger=ledger)
    build = json.loads(Path(args.build).read_text())
    decisions = jev.classify_all(client, build["snapshot"], build["derived"])
    out = {"schema": "robinhood-report/jev/v1", "model": jev_decisions.MODEL,
           "ran_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "snapshot_as_of": build["snapshot"]["as_of"], "decisions": decisions,
           "budget_after": ledger.status(datetime.now(timezone.utc))}
    Path(args.out).write_text(json.dumps(out, indent=2, default=str))
    for t in jev.sort_by_confidence(decisions):
        d = decisions[t]
        print(f"{t:5} {d['status']:8} {d.get('decision')!s:22} confidence={d.get('confidence')} reason={d.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
