"""rhreport: collect -> build -> (JEV on the Mac) -> story (Opus via claude -p) -> report."""
import argparse
import json
import sys
from pathlib import Path

from . import build as B
from . import collect, story
from .chain import LiveChain

ROOT = Path(__file__).resolve().parents[1]


def _load(p):
    return json.loads(Path(p).read_text()) if p else None


def cmd_collect(a):
    snap = collect.snapshot(LiveChain(), sample=a.sample)
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / (snap["as_of"].replace(":", "").replace("-", "") + ".json")
    path.write_text(json.dumps(snap, indent=2))
    print(path)
    return 0


def cmd_build(a):
    Path(a.out).write_text(json.dumps(B.build(_load(a.snapshot), _load(a.prev)), indent=2))
    print(a.out)
    return 0


def cmd_prompt(a):
    built, jev_out = _load(a.build), _load(a.jev)
    data = {"order": B.report(built, jev_out)["order"], "snapshot": built["snapshot"], "derived": built["derived"],
            "jev": (jev_out or {}).get("decisions")}
    sys.stdout.write((ROOT / "prompts" / "story.md").read_text() + json.dumps(data, indent=1) + "\n")
    return 0


def cmd_check_story(a):
    built, jev_out = _load(a.build), _load(a.jev)
    bad = story.check(Path(a.story).read_text(), {"snapshot": built["snapshot"], "derived": built["derived"],
                                                  "jev": (jev_out or {}).get("decisions")})
    if bad:
        print("unsupported numbers:", ", ".join(bad), file=sys.stderr)
        return 1
    print("story numbers: all found in the data")
    return 0


def cmd_verify_report(a):
    """Re-check a published report.json: its story may only use numbers from its own data."""
    rep = _load(a.report)
    if not rep.get("story"):
        print("no story in report")
        return 0
    jev_block = rep.get("jev") or {}
    bad = story.check(rep["story"]["markdown"], {"snapshot": {"tickers": rep["tickers"], "chain": rep["chain"]},
                                                 "derived": rep["derived"], "jev": jev_block.get("decisions")})
    if bad:
        print("unsupported numbers:", ", ".join(bad), file=sys.stderr)
        return 1
    print("published report: story numbers all found in its data")
    return 0


def cmd_report(a):
    built = _load(a.build)
    rep = B.report(built, _load(a.jev), Path(a.story).read_text() if a.story else None, _load(a.jev_status))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=2))
    if a.metrics_csv:
        Path(a.metrics_csv).write_text(B.metrics_long_csv(built["snapshot"]))
    print(a.out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rhreport")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("collect"); s.add_argument("--sample", type=int, default=200); s.add_argument("--dir", default="data/snapshots")
    s = sub.add_parser("build"); s.add_argument("--snapshot", required=True); s.add_argument("--prev"); s.add_argument("--out", default="data/build.json")
    s = sub.add_parser("prompt"); s.add_argument("--build", default="data/build.json"); s.add_argument("--jev")
    s = sub.add_parser("check-story"); s.add_argument("--story", required=True); s.add_argument("--build", default="data/build.json"); s.add_argument("--jev")
    s = sub.add_parser("verify-report"); s.add_argument("--report", default="data/report.json")
    s = sub.add_parser("report"); s.add_argument("--build", default="data/build.json"); s.add_argument("--jev"); s.add_argument("--story")
    s.add_argument("--jev-status", help="data/jev_status.json (paused/active)")
    s.add_argument("--out", default="data/report.json"); s.add_argument("--metrics-csv")
    a = ap.parse_args(argv)
    return {"collect": cmd_collect, "build": cmd_build, "prompt": cmd_prompt, "check-story": cmd_check_story,
            "report": cmd_report, "verify-report": cmd_verify_report}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
