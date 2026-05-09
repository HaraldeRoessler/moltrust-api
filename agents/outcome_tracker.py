#!/usr/bin/env python3
"""
MoltGuard Outcome Tracker
Trackt Flag-Outcomes nach Polymarket Settlement.
Review: APPROVED 2026-04-02
Changes: marktabhaengige Schwellwerte, INCONCLUSIVE 0.25, "anomaly" statt "manipulation"
"""
import os, json, requests, psycopg2, datetime
from pathlib import Path

DB_URL = os.environ.get("DATABASE_URL", "dbname=moltstack user=moltstack")
POLYMARKET_API = "https://gamma-api.polymarket.com"


# Marktabhaengige Schwellwerte (Review-Aenderung #1)
def get_movement_threshold(price_at_flag: float) -> float:
    """Schwellwert fuer 'signifikante Preisbewegung' je nach Marktpreis"""
    if price_at_flag < 0.10:
        return 0.30  # Illiquide: 30%
    if price_at_flag < 0.30:
        return 0.20  # Niedrig: 20%
    if price_at_flag < 0.70:
        return 0.15  # Mittel: 15%
    return 0.10       # Hoch: 10%


def calculate_verdict(price_movement_pct: float, price_at_flag: float) -> tuple:
    """Berechnet Verdikt und FlagScore-Beitrag"""
    threshold = get_movement_threshold(price_at_flag)
    abs_movement = abs(price_movement_pct)

    if abs_movement >= threshold:
        return "CONFIRMED", 1.0
    elif abs_movement >= threshold * 0.5:
        return "PARTIAL", 0.5
    elif abs_movement < threshold * 0.1:
        return "INCORRECT", 0.0
    else:
        return "INCONCLUSIVE", 0.25  # Review-Aenderung #2


def get_polymarket_settlement(market_id: str) -> dict | None:
    """Prueft ob ein Polymarket Markt settled ist"""
    try:
        r = requests.get(f"{POLYMARKET_API}/markets/{market_id}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("closed") and data.get("resolutionTime"):
                return {
                    "settled": True,
                    "outcome": data.get("question", ""),
                    "resolved_at": data.get("resolutionTime"),
                    "last_price": data.get("lastTradePrice", 0)
                }
    except Exception as e:
        print(f"Polymarket API error: {e}")
    return None


def check_pending_flags():
    """Prueft alle pending Flags auf Settlement"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT flag_id, market_id, polymarket_slug, price_at_flag,
               settlement_expected_at, created_at
        FROM flag_records
        WHERE status IN ('pending', 'monitoring')
        AND (settlement_expected_at IS NULL OR settlement_expected_at < NOW() + INTERVAL '7 days')
    """)
    flags = cur.fetchall()
    print(f"Checking {len(flags)} pending flags...")

    for flag_id, market_id, slug, price_at_flag, expected_at, created_at in flags:
        settlement = get_polymarket_settlement(slug or market_id)

        if settlement and settlement["settled"]:
            price_now = float(settlement["last_price"])
            price_then = float(price_at_flag or 0.5)
            movement_pct = (price_now - price_then) / price_then if price_then > 0 else 0

            verdict, score = calculate_verdict(movement_pct, price_then)

            cur.execute("""
                INSERT INTO outcome_records
                (flag_id, settled_at, settlement_outcome, price_at_settlement,
                 price_movement_pct, verdict, flag_score_contribution)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s)
                ON CONFLICT (flag_id) DO NOTHING
            """, (flag_id, settlement["outcome"], price_now,
                  round(movement_pct * 100, 2), verdict, score))

            cur.execute("UPDATE flag_records SET status='settled' WHERE flag_id=%s", (flag_id,))
            conn.commit()

            print(f"Settled: {flag_id} -> {verdict} (movement: {movement_pct*100:.1f}%)")
            trigger_herald_outcome(flag_id, verdict, movement_pct, settlement)

    cur.close()
    conn.close()


def get_track_record() -> dict:
    """Berechnet oeffentlichen FlagScore"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT verdict, COUNT(*), AVG(flag_score_contribution)
        FROM outcome_records
        GROUP BY verdict
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    counts = {r[0]: r[1] for r in rows}
    total = sum(counts.values())
    if total == 0:
        return {"flag_score": None, "total_flags": 0}

    # Review-Aenderung #2: INCONCLUSIVE mit 0.25 im Nenner
    confirmed = counts.get("CONFIRMED", 0)
    partial = counts.get("PARTIAL", 0)
    inconclusive = counts.get("INCONCLUSIVE", 0)
    incorrect = counts.get("INCORRECT", 0)

    numerator = confirmed * 1.0 + partial * 0.5 + inconclusive * 0.25
    denominator = total
    flag_score = round(numerator / denominator, 3) if denominator > 0 else None

    return {
        "flag_score": flag_score,
        "total_flags": total,
        "confirmed": confirmed,
        "partial": partial,
        "inconclusive": inconclusive,
        "incorrect": incorrect
    }


def trigger_herald_outcome(flag_id: str, verdict: str, movement_pct: float, settlement: dict):
    """Triggert Herald Follow-up Tweet nach Settlement"""
    # Review-Aenderung #3: "anomaly" statt "manipulation"
    track = get_track_record()
    herald_prompt = (
        "Write a follow-up tweet about an anomaly flag that has now settled.\n\n"
        f"Flag ID: {flag_id}\n"
        f"Verdict: {verdict}\n"
        f"Price movement after flag: {movement_pct*100:.1f}%\n"
        f"Settlement: {settlement.get('outcome', 'resolved')}\n"
        f"Our track record: {track['flag_score']} FlagScore "
        f"({track['confirmed']} confirmed / {track['total_flags']} total)\n\n"
        "Rules:\n"
        '- Use "anomaly" never "manipulation" or "suspicious"\n'
        "- Never claim we predicted the outcome direction\n"
        "- State only: we flagged unusual activity, here is what happened\n"
        "- Include: flag URL, track record stat\n"
        "- Max 280 chars\n"
        "- Dry, factual tone"
    )

    queue_file = Path.home() / "moltstack/data/herald_outcome_queue.json"
    with open(queue_file, "a") as f:
        json.dump({
            "flag_id": flag_id,
            "prompt": herald_prompt,
            "created_at": datetime.datetime.utcnow().isoformat()
        }, f)
        f.write("\n")


if __name__ == "__main__":
    check_pending_flags()
    print("Track record:", get_track_record())
