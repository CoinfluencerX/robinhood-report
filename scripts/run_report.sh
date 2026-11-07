#!/usr/bin/env bash
# One full report run on Franklin's Mac. Costs: JEV (5 classify calls, inside the $1/day Jarvis ledger)
# and the Claude subscription (one `claude -p` call). Everything else is free public chain data.
# Not scheduled: adding a launchd/Hermes job needs Franklin's explicit approval.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
JARVIS="${JARVIS:-$HOME/Developer/operation-jarvis}"
PUBLISH_DIR="${PUBLISH_DIR:-$HOME/data/robinhood-report}"
cd "$REPO"

PREV="$(ls -1 data/snapshots/*.json 2>/dev/null | tail -1 || true)"
SNAP="$(python3 -m rhreport collect)"                                  # 1. read the chain
python3 -m rhreport build --snapshot "$SNAP" ${PREV:+--prev "$PREV"}   # 2. deterministic signals
( cd "$JARVIS" && python3 tools/runtime_entry.py "$REPO/scripts/jev_classify.py" \
    --jarvis "$JARVIS" --build "$REPO/data/build.json" --out "$REPO/data/jev.json" )   # 3. JEV labels
python3 -m rhreport prompt --jev data/jev.json \
  | claude -p --model claude-opus-5-5 --effort high --safe-mode --tools "" \
      --strict-mcp-config --mcp-config '{"mcpServers":{}}' --setting-sources '' > data/story.md   # 4. Opus story
python3 -m rhreport check-story --story data/story.md --jev data/jev.json                       # 5. number check
python3 -m rhreport report --jev data/jev.json --story data/story.md \
  --out data/report.json --metrics-csv data/metrics_long.csv                                     # 6. export
mkdir -p "$PUBLISH_DIR" && cp data/report.json "$PUBLISH_DIR/report.json"                        # 7. site picks it up
echo "Published $PUBLISH_DIR/report.json (review it, then commit data/ when you're happy)"
