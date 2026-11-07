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
JEV_ARGS=()
if python3 -c "import json,sys;sys.exit(0 if json.load(open('data/jev_status.json')).get('state')=='paused' else 1)" 2>/dev/null; then
  echo "JEV paused (data/jev_status.json): skipping labels"
else
  ( cd "$JARVIS" && python3 tools/runtime_entry.py "$REPO/scripts/jev_classify.py" \
      --jarvis "$JARVIS" --build "$REPO/data/build.json" --out "$REPO/data/jev.json" )   # 3. JEV labels
  JEV_ARGS=(--jev data/jev.json)
fi
python3 -m rhreport prompt ${JEV_ARGS[@]+"${JEV_ARGS[@]}"} \
  | claude -p --model claude-opus-5-5 --effort high --safe-mode --tools "" \
      --strict-mcp-config --mcp-config '{"mcpServers":{}}' --setting-sources '' > data/story.md   # 4. Opus story
python3 -m rhreport check-story --story data/story.md ${JEV_ARGS[@]+"${JEV_ARGS[@]}"}                      # 5. number check
python3 -m rhreport report ${JEV_ARGS[@]+"${JEV_ARGS[@]}"} --jev-status data/jev_status.json --story data/story.md \
  --out data/report.json --metrics-csv data/metrics_long.csv                                     # 6. export
mkdir -p "$PUBLISH_DIR" && cp data/report.json "$PUBLISH_DIR/report.json"                        # 7. site picks it up
echo "Published $PUBLISH_DIR/report.json (review it, then commit data/ when you're happy)"
