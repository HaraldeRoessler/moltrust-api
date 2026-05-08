#!/bin/bash
# Weekly Traffic Report — Montag 08:00 UTC
set -eo pipefail

source /home/moltstack/.moltrust_secrets

LOG="/var/log/nginx/access.log"
STATS_LOG="/home/moltstack/moltstack/logs/weekly_traffic.log"

# Top Endpoints (strip query params)
TOP_ENDPOINTS=$(awk '{print $7}' $LOG | cut -d'?' -f1 | sort | uniq -c | sort -rn | head -10)

# Unique IPs
UNIQUE_IPS=$(awk '{print $1}' $LOG | sort -u | wc -l)

# MCP stats
MCP_TOTAL=$(grep -c '/mcp' $LOG 2>/dev/null || echo 0)
MCP_AUTH=$(grep -c '/mcp.*api_key=mt_' $LOG 2>/dev/null || echo 0)
MCP_UNAUTH=$((MCP_TOTAL - MCP_AUTH))
MCP_429=$(awk '$7 ~ /\/mcp/ && $9 == 429' $LOG 2>/dev/null | wc -l)

# Active mt_ keys
ACTIVE_KEYS=$(grep '/mcp.*api_key=mt_' $LOG 2>/dev/null | grep -o 'api_key=mt_[^& ]*' | sort -u | wc -l)

# A2A discovery
A2A_CALLS=$(grep -c 'well-known/a2a\|well-known/agent' $LOG 2>/dev/null || echo 0)

# Top user agents
TOP_UA=$(awk -F'"' '{print $6}' $LOG | sort | uniq -c | sort -rn | head -5)

# Top profiles
TOP_PROFILES=$(grep '/mcp.*profile=' $LOG 2>/dev/null | grep -o 'profile=[^& ]*' | sort | uniq -c | sort -rn | head -5)

# Build message
MSG="📈 <b>Weekly Traffic Report</b>

<b>Overview:</b>
Unique IPs: ${UNIQUE_IPS}
Active API Keys (mt_): ${ACTIVE_KEYS}

<b>MCP:</b>
Total: ${MCP_TOTAL} (${MCP_AUTH} auth / ${MCP_UNAUTH} unauth)
Rate-limited (429): ${MCP_429}
A2A Discovery: ${A2A_CALLS}

<b>Top Endpoints:</b>
$(echo "$TOP_ENDPOINTS" | head -5 | awk '{printf "  %s %s\n", $1, $2}')

<b>Top Profiles:</b>
$(echo "$TOP_PROFILES" | head -3 | awk '{printf "  %s %s\n", $1, $2}')

$(date -u +'%Y-%m-%d %H:%M UTC')"

# Send Telegram
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d parse_mode="HTML" \
        --data-urlencode "text=$MSG" > /dev/null 2>&1
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] Weekly report sent" >> "$STATS_LOG"
fi

echo "Weekly traffic report complete."
