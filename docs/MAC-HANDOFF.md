# Mac Mini handoff: put the Robinhood Report on franklineth.ai

**For:** the local Claude Code session on Franklin's Mac Mini (production).
**Approved by Franklin on 2026-11-07:** add the `/robinhood-report` page, add a green card for it to the homepage "Tools & Research" grid, and install a weekly data-sync job. Nothing else: no other homepage edits, no credential changes.

## Why this has to run on the Mac
The homepage's "Tools & Research" section (Poker Math Lab, Hyperliquid Carry, AI Knowledge Hub, Research & modeling desk) exists **only on the Mac**. It isn't on any branch of `CoinfluencerX/franklineth-blog-work` on GitHub (checked 2026-11-07, all 16 branches). So production must be backed up to GitHub first, then the report page merged in. Never overwrite production with GitHub's `main`.

## Steps (stop and report if any step fails)

1. **Back up production.** In `~/franklineth-blog-work`:
   ```bash
   git status --short && git log --oneline -3
   git switch -c prod/snapshot-2026-11-07
   git add -A && git commit -m "Snapshot of Mac Mini production (homepage Tools & Research, new design)"
   git push -u origin prod/snapshot-2026-11-07
   ```
   Before committing, confirm that `.env`, keys, `node_modules` and anything else `.gitignore` excludes stay out of the commit. If `git status` shows a secret-looking file, stop and ask Franklin.

2. **Merge the report page.** Still on `prod/snapshot-2026-11-07`:
   ```bash
   git fetch origin feat/robinhood-report
   git merge --no-ff origin/feat/robinhood-report
   ```
   It adds `lib/robinhood-report-page.js`, the `/robinhood-report` route in `server.js`, a portfolio entry, a command-palette route, `scripts/verify-robinhood-report.js` and its fixture. In any conflict, **keep production's version** and add only the report pieces.

3. **Add the homepage card.** Find the "Tools & Research / Practice and research tools." grid (search for `Hyperliquid Carry`). Copy the **Hyperliquid Carry** card's markup and classes exactly (dark green card) and add a new card with:
   - eyebrow: `ON-CHAIN RESEARCH · ROBINHOOD CHAIN`
   - title: `franklineth's Robinhood Report`
   - text: `What the blockchain shows about tokenized stocks: who's borrowing them on-chain, who's moving them, and testable ideas for alpha. Read straight from Robinhood Chain, labeled by a decision model, every number machine-checked.`
   - link: `Read the report →` → `/robinhood-report`

   If the grid is 2-wide, put it right after Hyperliquid Carry and let the grid reflow. Don't restyle the other cards.

4. **Get the data.**
   ```bash
   mkdir -p ~/Developer && cd ~/Developer
   [ -d robinhood-report ] || git clone https://github.com/CoinfluencerX/robinhood-report.git
   cd robinhood-report && git pull --ff-only && /usr/bin/python3 -m rhreport verify-report
   mkdir -p ~/data/robinhood-report && cp data/report.json ~/data/robinhood-report/report.json
   ```
   (The site reads `$DATA_DIR/robinhood-report/report.json`; `DATA_DIR` defaults to `~/data` next to the repo.)

5. **Verify, then restart.** In `~/franklineth-blog-work`:
   ```bash
   npm run verify:robinhood-report
   npm test
   launchctl kickstart -k gui/$(id -u)/ai.franklineth.site
   sleep 3
   curl -s http://127.0.0.1:3001/robinhood-report | grep -c "Robinhood Report"
   curl -s http://127.0.0.1:3001/ | grep -c "robinhood-report"
   ```
   Both counts must be ≥ 1. Then open https://franklineth.ai/ and https://franklineth.ai/robinhood-report to confirm.

6. **Install the weekly sync.** Create `~/Library/LaunchAgents/ai.franklineth.robinhood-report-sync.plist`:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0"><dict>
     <key>Label</key><string>ai.franklineth.robinhood-report-sync</string>
     <key>ProgramArguments</key><array><string>/bin/bash</string><string>-lc</string>
       <string>cd "$HOME/Developer/robinhood-report" &amp;&amp; git pull --ff-only -q &amp;&amp; /usr/bin/python3 -m rhreport verify-report &amp;&amp; mkdir -p "$HOME/data/robinhood-report" &amp;&amp; cp data/report.json "$HOME/data/robinhood-report/report.json"</string></array>
     <key>StartCalendarInterval</key><dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>23</integer></dict>
     <key>StandardOutPath</key><string>/tmp/robinhood-report-sync.log</string>
     <key>StandardErrorPath</key><string>/tmp/robinhood-report-sync.log</string>
   </dict></plist>
   ```
   ```bash
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.franklineth.robinhood-report-sync.plist
   launchctl kickstart gui/$(id -u)/ai.franklineth.robinhood-report-sync && sleep 5 && cat /tmp/robinhood-report-sync.log
   ```
   This only pulls public data and copies one file: no keys, no model calls, no cost. The weekly report itself is produced in the cloud every Sunday evening (US time) and committed to this repo, so the Monday 06:23 sync picks it up.

7. **Make GitHub match production.** Push the merged branch and open a PR into `main` titled "Production snapshot + Robinhood Report" for Franklin to merge:
   ```bash
   git push origin prod/snapshot-2026-11-07
   gh pr create --base main --head prod/snapshot-2026-11-07 --title "Production snapshot + Robinhood Report" --body "Mac Mini production state plus /robinhood-report and its homepage card."
   ```

8. **Report back** with the commands you ran, their exit codes, the two `curl` counts, the sync log, and the PR link.
