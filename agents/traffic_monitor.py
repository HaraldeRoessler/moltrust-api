#!/usr/bin/env python3
"""
Traffic Monitor v2 — Persistent IP Tracking
Solves the "25-30 New External Callers" noise by tracking truly new IPs
across runs via a state file.
"""

import psycopg2
import requests
import json
from datetime import datetime
import os

# Configuration
KNOWN_IPS_FILE = "/home/moltstack/known_ips.txt"
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DB_PASSWORD = os.getenv('MOLTSTACK_DB_PW', '')
TRUSTED_PREFIXES = ['127.', '::1', '10.', '172.16.', '192.168.', '88.99.', '116.202.', '46.225.175.']


def load_known_ips():
    """Load previously seen IPs from persistent state file"""
    try:
        with open(KNOWN_IPS_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()


def save_known_ips(ips):
    """Save all known IPs to persistent state file"""
    with open(KNOWN_IPS_FILE, 'w') as f:
        for ip in sorted(ips):
            f.write(f"{ip}\n")


def is_trusted_ip(ip):
    """Check if IP is from trusted sources (localhost, private ranges, Hetzner)"""
    return any(ip.startswith(prefix) for prefix in TRUSTED_PREFIXES)


def get_external_callers():
    """Get external callers with >10 requests in last 25 hours"""
    conn = psycopg2.connect(
        host="localhost",
        database="moltstack",
        user="moltstack",
        password=DB_PASSWORD,
    )

    query = """
    SELECT
        ip,
        COUNT(*) as request_count,
        MAX(ts) as last_seen,
        MIN(ts) as first_seen,
        (array_agg(DISTINCT user_agent))[1] as user_agent,
        (array_agg(DISTINCT ip_org) FILTER (WHERE ip_org IS NOT NULL))[1] as ip_org
    FROM request_log
    WHERE ts > NOW() - INTERVAL '25 hours'
        AND ip IS NOT NULL
    GROUP BY ip
    HAVING COUNT(*) > 10
    ORDER BY COUNT(*) DESC
    """

    with conn.cursor() as cur:
        cur.execute(query)
        results = cur.fetchall()

    conn.close()

    external_callers = []
    for row in results:
        ip, count, last_seen, first_seen, user_agent, ip_org = row
        if not is_trusted_ip(ip):
            external_callers.append({
                'ip': ip,
                'count': count,
                'last_seen': last_seen,
                'first_seen': first_seen,
                'user_agent': user_agent or 'Unknown',
                'ip_org': ip_org or '',
            })

    return external_callers


def categorize_callers(current_callers, known_ips):
    """Categorize callers into truly new vs recurring"""
    current_ips = {caller['ip'] for caller in current_callers}
    truly_new_ips = current_ips - known_ips
    recurring_ips = current_ips & known_ips

    new_callers = [c for c in current_callers if c['ip'] in truly_new_ips]
    recurring_callers = [c for c in current_callers if c['ip'] in recurring_ips]

    return new_callers, recurring_callers


def format_telegram_message(new_callers, recurring_callers):
    """Format Telegram message (Markdown v1: *bold*, no **)"""
    total = len(new_callers) + len(recurring_callers)
    new_count = len(new_callers)

    if new_count == 0 and len(recurring_callers) <= 5:
        return None

    lines = [
        "🔍 *External Traffic Report*",
        "",
        f"*Total Active:* {total} callers",
        f"*Truly New:* {new_count}",
        f"*Recurring:* {len(recurring_callers)}",
        "",
    ]

    if new_callers:
        lines.append(f"🚨 *NEW External Callers ({new_count})*")
        lines.append("")
        for caller in new_callers:
            org = f" ({caller['ip_org']})" if caller['ip_org'] else ""
            ua_short = caller['user_agent'][:50]
            if len(caller['user_agent']) > 50:
                ua_short += "..."
            lines.append(f"`{caller['ip']}`{org}")
            lines.append(f"{caller['count']} reqs | UA: {ua_short}")
            lines.append("")

    if recurring_callers and new_count > 0:
        lines.append("🔄 *Top Recurring Callers*")
        lines.append("")
        top_recurring = sorted(recurring_callers, key=lambda x: x['count'], reverse=True)[:5]
        for caller in top_recurring:
            org = f" ({caller['ip_org']})" if caller['ip_org'] else ""
            lines.append(f"`{caller['ip']}`{org} — {caller['count']} reqs")

    return "\n".join(lines)


def send_telegram_alert(message):
    """Send alert to Telegram"""
    if not message or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown',
            },
            timeout=10,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


def main():
    """Main traffic monitor with persistent tracking"""
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Traffic Monitor v2 starting")

    known_ips = load_known_ips()
    print(f"  Known IPs from state file: {len(known_ips)}")

    current_callers = get_external_callers()
    print(f"  Active external callers (>10 reqs/25h): {len(current_callers)}")

    new_callers, recurring_callers = categorize_callers(current_callers, known_ips)
    print(f"  Truly new: {len(new_callers)}, Recurring: {len(recurring_callers)}")

    # Update known IPs
    all_current_ips = {caller['ip'] for caller in current_callers}
    updated_known_ips = known_ips | all_current_ips
    save_known_ips(updated_known_ips)
    print(f"  State file updated: {len(updated_known_ips)} total known IPs")

    message = format_telegram_message(new_callers, recurring_callers)
    if message:
        success = send_telegram_alert(message)
        print(f"  Telegram alert sent: {success}")
    else:
        print(f"  No alert — quiet period")


if __name__ == "__main__":
    main()
