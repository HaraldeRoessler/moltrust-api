# Endpoint Probe

Monitors critical MolTrust API endpoints every 5 minutes via cron.
Alerts via Telegram on sustained failures, sends recovery notifications.

## Files

| Path | Purpose |
|------|---------|
| `~/moltstack/scripts/endpoint_probe.py` | Probe script |
| `~/moltstack/state/endpoint_probe.json` | State file (per-endpoint status) |
| `~/moltstack/logs/endpoint_probe.log` | Log file |

## Monitored Endpoints

| Path | Body Check |
|------|-----------|
| `/health` | HTTP 200 |
| `/.well-known/did.json` | HTTP 200 + contains `did:web:api.moltrust.ch` |
| `/.well-known/jwks.json` | HTTP 200 + JSON has `keys` array |
| `/.well-known/agent-card.json` | HTTP 200 |
| `/skill/trust-score/...d34ed796a4dc4698` | HTTP 200 + JSON has `trust_score` |

All responses are also checked for `"DNS cache overflow"` in the body (paranoid guard).

## Alert Policy

- **Down alert**: After 2 consecutive failures on the same endpoint.
  Only one alert per incident (deduped via state file).
- **Recovery alert**: When endpoint returns to 200 after being in down state.
  Includes downtime duration in minutes.

## Cron

```
*/5 * * * * /usr/bin/python3 /home/moltstack/moltstack/scripts/endpoint_probe.py >> /home/moltstack/moltstack/logs/endpoint_probe.log 2>&1
```

## Adding/Removing Endpoints

Edit the `ENDPOINTS` list in `endpoint_probe.py`. Each entry:

```python
{
    "path": "/your/path",              # Display name + state key
    "url": "https://api.moltrust.ch/your/path",
    "body_contains": "expected string", # or None
    "body_json_key": "expected_key",    # or None
}
```

After adding: delete the endpoint's entry from `state/endpoint_probe.json`
(or delete the whole file) to reset state.

## Silencing an Alert

Edit `~/moltstack/state/endpoint_probe.json`. Set `"alerted_down": true`
for the endpoint you want to silence. No further down alerts will fire
until the endpoint recovers and fails again.

## Dry Run

```bash
python3 ~/moltstack/scripts/endpoint_probe.py --dry-run
```

Runs all checks, logs results, but does not send Telegram messages.

## Log Retention

Logs are appended to `endpoint_probe.log`. Clean up entries older than
14 days manually or via logrotate.
