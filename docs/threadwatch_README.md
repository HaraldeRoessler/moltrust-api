# ThreadWatch

Stop-gap inbound monitor for MolTrust. Runs 2x/day via cron, generates a Telegram report on:

1. External GitHub threads waiting for MolTrust response
2. MolTrust-owned agent health flags (suspensions, stuck queues, stale posts)

Built 2026-04-24 after VCOne suspension (15 days unnoticed), aeoess trust_verification slot lost (20h after tag), Kevin's #1717 reply hung 19h. Diagnostic-only — never auto-replies, never auto-posts.

## Files

| Path | Purpose |
|---|---|
| `~/moltstack/scripts/threadwatch.py` | main script |
| `~/moltstack/scripts/threadwatch_config.yaml` | watchlist + thresholds (edit here, no code change) |
| `~/moltstack/state/threadwatch.json` | acknowledgments + telegram offset |
| `~/moltstack/logs/threadwatch.log` | rotating, 14 days retention |

## Cron schedule

```
0 8,18 * * * /home/moltstack/moltstack/venv/bin/python3 /home/moltstack/moltstack/scripts/threadwatch.py >> /home/moltstack/moltstack/logs/threadwatch.log 2>&1
```

08:00 and 18:00 UTC. Lars-DACH-local: morning planning + end-of-day check.

## What it does

**Per run:**

1. Pulls fresh Telegram messages, applies `/ack` / `/ack_list` / `/ack_remove` commands.
2. Checks GitHub rate-limit remaining; aborts run silently if below threshold (default 500).
3. Crawls every repo in `watchlist` for issues+comments updated in the last 7 days.
4. Scans bodies for MolTrust mentions (configurable keywords + identity @-mentions).
5. Classifies each thread:
   - **🔴 urgent** — direct @-mention, no MolTrust reply since, < 48h
   - **🟡 active** — we historically commented, external follow-up, no reply, < 7d
   - **🟢 stale** — MolTrust mentioned, no reply, < 30d
6. Probes agent health:
   - VCOne-AI public profile (404 = suspended) + last event age
   - MoltyCel pending-drafts queue size + oldest draft age
   - Moltbook agents' last successful POST timestamps from logs
   - Endpoint-probe state file
7. Suppresses any thread with active `/ack`.
8. Sends consolidated Telegram report. Logs full unfiltered list to `threadwatch.log`.

## Telegram commands

Run any time, applied at next ThreadWatch run:

| Command | Effect |
|---|---|
| `/ack <repo>#<num>` | suppress thread for 7 days |
| `/ack <repo>#<num> <days>` | custom suppression length |
| `/ack <repo>#<num> <days> <note>` | with annotation in state.json |
| `/ack_list` | list active acks |
| `/ack_remove <repo>#<num>` | un-ack |

Examples:
```
/ack a2aproject/A2A#1717
/ack aeoess/agent-governance-vocabulary#36 14 slot taken by AgentID
/ack_list
/ack_remove a2aproject/A2A#1717
```

Acknowledgments expire automatically — no cleanup needed.

## CLI flags

| Flag | Purpose |
|---|---|
| `--dry-run` | full run, but write report to stdout/log instead of Telegram |
| `--with-test-fixture` | inject a synthetic urgent thread (for ack-flow tests) |
| `--process-acks-only` | only fetch + apply Telegram commands, no report |

## Editing the watchlist

```bash
$EDITOR ~/moltstack/scripts/threadwatch_config.yaml
# add to `watchlist:` list, save, no restart needed — read fresh each run
```

The `moltrust_identities` and `mention_keywords` lists also live there. Keep them in sync with active GitHub accounts.

## Manual ack via state.json

If Telegram is unavailable:

```bash
$EDITOR ~/moltstack/state/threadwatch.json
# under "acknowledged": add  "<repo>#<num>": {"until": "<ISO>", "acked_at": "...", "note": "..."}
```

## Known limitations

- **Notifications API not yet used as primary trigger** — current implementation fully relies on active-crawl. Notifications hint still useful for cross-checking but redundant given crawl coverage.
- **No Slack/Email/LinkedIn channels** — GitHub-only by design.
- **No content suggestion** — flags threads, doesn't draft replies.
- **No multi-Lars HITL** — single Telegram chat_id only.
- **Issue body changes (silent edits, label changes) trigger notifications but aren't surfaced** — only comment/issue-body content is scanned.
- **Rate limit only checked on `core` resource** — search API has separate budget; not currently used.

This is a **stop-gap**. The structural replacement (notification-event-driven, multi-channel, persistent state across acknowledgments) lands separately.
