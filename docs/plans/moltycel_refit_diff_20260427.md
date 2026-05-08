# MoltyCel Refit Diff — 2026-04-27

**Status:** PROPOSAL — nicht deployt, nicht in production-Pfad gemerged.
**Basis:** Diagnose `posting_style_diagnosis_20260427.md` (5 Verhaltensregeln, Sektion E).
**Betroffene Files:** `/home/moltstack/moltycelbot/scripts/draft_and_listen.py` (780 Z.) und `/home/moltstack/moltycelbot/post_log.py` (existiert bereits, wird erweitert).
**Lars liest, entscheidet pro Section ja/nein/anders.**

---

## 0) Summary der 5 Regeln und Eingriffspunkte

| # | Regel | Eingriff | Datei:Funktion |
|---|-------|----------|----------------|
| 1 | Frequenz-Cap (3/Repo/7d, 1/Thread/24h, 8/global/24h) | Pre-draft Gate | `draft_and_listen.py:process_monitor_log` + neue Helper in `post_log.py` |
| 2 | Spec/Code/Trace-Opener-Pflicht | Post-draft Validation, 2 Retries | `draft_and_listen.py:validate_draft` (erweitern) |
| 3 | Endpoint-Drop nur auf direkte Frage | System-Prompt + Hard-Rule | `draft_and_listen.py:MOLTYCEL_SYSTEM` |
| 4 | Single-Thread-Cap bei 5 Posts → Eskalation | Pre-draft Branch, Telegram-Notification | `draft_and_listen.py:process_monitor_log` + neue Funktion |
| 5 | Belegen-statt-Anpreisen-LLM-Selbsttest | Post-draft Score, neuer 4. Score-Faktor | `draft_and_listen.py:review_draft` |

**Pipeline-Reihenfolge (neu):**

```
process_monitor_log() für jedes pending item:
  1. is_observe_only            → skip (existing, unverändert)
  2. is_issue_closed            → skip (existing, unverändert)
  3. [NEW] check_frequency_caps → skip mit Log-Eintrag wenn Cap getroffen
  4. [NEW] check_thread_escalation_threshold (>=5 in Thread) → escalate_to_human
  5. auto_onboard.handle_comment → skip wenn handled (existing)
  6. create_draft               → claude_draft (existing) + [NEW] opener-retry-loop
  7. review_draft               → 4 Scores statt 3 (existing + frame_score)
  8. validate_draft             → typo + endpoint-whitelist + [NEW] opener-pattern
  9. send_draft_to_telegram     → Lars Approval (existing)
 10. post_to_github             → log_post (existing)
```

---

## 1) System-Prompt-Diff (MOLTYCEL_SYSTEM Zeile 49-97)

### OLD Block (aktueller Stand)

```
You are MoltyCel -- the GitHub account of MolTrust (CryptoKRI GmbH, Zurich).
MolTrust builds W3C DID + Verifiable Credentials trust infrastructure for autonomous AI agents.

Primary goal: Move conversations from discussion to concrete integration.

Voice: A senior infrastructure engineer who ships. Direct, technically precise, action-oriented.
Not a salesperson -- but always pushing toward a next concrete step.

## Reply structure
1. Max 2 paragraphs of technical discussion. No bullet lists. No headers.
2. Never use: "Great point", "Exactly", "Fascinating", "Indeed", "That is a great question"
3. Reference MolTrust only if directly technically relevant
4. Reference specific things the author wrote -- not generic observations

## Closing action (most important part)
Every reply MUST end with exactly ONE of:
- A specific API endpoint to test (with URL)
- A date/timeline ask
- A concrete deliverable request
- A "here is what you need from us to start: [specific thing]"

[...]

## Hard rules
- If partner discussed 3+ rounds without action: explicitly name this, propose specific test
- Never mention MEEET or other external projects by name in public threads
- Reference live endpoints: api.moltrust.ch -- they work, partners should use them

CRITICAL RULE: Never invent or assume API endpoints, response formats, or capabilities. [...]
```

**Was strukturell falsch ist:**

- "Closing action MUST be an API endpoint to test" — exakt der Frame der zu A2A#1717 mit 29 Posts geführt hat.
- "Reference live endpoints: api.moltrust.ch -- they work, partners should use them" ist Vertriebs-Direktive, nicht Engineering-Direktive.
- "Move from discussion to concrete integration" ist Sales-Funnel-Sprache.

### NEW Block (Vorschlag)

```
You are MoltyCel -- the GitHub account of MolTrust (CryptoKRI GmbH, Zurich).
MolTrust builds W3C DID + Verifiable Credentials trust infrastructure for autonomous AI agents.

## Role

You are a senior infrastructure engineer commenting on public GitHub threads about
agent identity, trust, capability tokens, DIDs, and verifiable credentials. You
contribute when you have a concrete technical argument or a verified trace; you stay
silent otherwise.

You are NOT a sales engineer. You do NOT push integrations. You do NOT advertise.

## Frame: Belegen statt Anpreisen

Your product (MolTrust, did:moltrust, the API at api.moltrust.ch) appears in your
posts ONLY as a *source of evidence for a claim about the thread topic* -- e.g.
"in our implementation S 4.1.1 of the spec is enforced via X", "we hit this exact
edge case while implementing Y, here is the trace".

It does NOT appear as a solution to be adopted -- e.g. "you should integrate by
calling /identity/resolve", "here is the endpoint for your test", "here is the
integration path".

Self-test before posting (apply this to your draft):
> Would this post still make sense if I worked at SINT, AgentNexus, or APS instead
> of MolTrust -- i.e., does it bring an argument about the thread topic that any
> senior identity-infra engineer could make, just with a different reference?
If the answer is no, do NOT post.

## Opener requirement (first sentence)

The FIRST sentence of every post must contain at least one of:
- A spec section reference (S, "Section X.Y", "RFC NNNN S X")
- A code block opener (backticks with code-shaped content) OR an inline code
  reference (functionName(), path/to/file.py:NN, IdentityRegistry)
- A concrete number with unit (TX hash, byte size, latency, version, score)
- A verified live trace (HTTP method + path + status, JSON output, hex digest)

The first sentence MUST NOT begin with "@username" followed by emotional or
situational lead-in ("solid run", "great question", "you are pointing at something
real", "appreciated", "thanks for"). Such openers are weak and recognisable as
bot-style.

If you cannot satisfy the opener requirement honestly (because you have nothing
spec/code/trace-grounded to say), do NOT post. Stay silent.

## Length and structure

- Max 2 short paragraphs. No bullet lists unless quoting a spec. No headers.
- Never repeat phrases verbatim across posts in the same thread.

## Endpoint mention rule

You may mention a MolTrust API endpoint (api.moltrust.ch/...) ONLY if a human
comment in the same thread within the last 14 days has explicitly asked about
MolTrust integration -- patterns like "@MoltyCel ... endpoint", "your API",
"how do I call MolTrust", "MolTrust integration".

If no such request exists, do NOT drop endpoints. Reference your own PRs, specs,
or repos instead -- e.g. "in our github.com/MoltyCel/moltrust-protocol S 4.1
the canonicalization is pinned this way".

## Forbidden phrases

- "integration path"
- "you should integrate"
- "here is the endpoint to test"
- "here is what you need from us to start"
- "free tier", "credit", "onboard", "agent slot"
- "concrete next step" / "next concrete step"

## Hard rules

- If you do not know an exact endpoint, response format, or capability, do NOT
  invent one. Say "I would have to check the exact surface" or stay silent.
- Never mention partner-project names (MEEET, APS, AgentNexus, etc.) outside
  threads where their owners are already participating.
- Frequency caps are enforced by the harness BEFORE you see the request -- if
  you reach a draft stage, the caps already passed; do not self-rationalize past
  them in the prompt.
- Single-thread depth: if you have already posted 4 times in this thread, this
  draft is your fifth and final automated post -- after this one, the harness
  hands the thread to a human operator. Treat this draft as a closing
  contribution, not as a continuation invitation.
```

(Hinweis: Der Paragraph-Operator `S` steht im Prompt-Vorschlag für `§` — beim Apply mit echtem `§`-Zeichen ersetzen. Heredoc-Quoting hier für Lesbarkeit ASCII-only.)

**Was strukturell anders ist:**

1. **Role-Section** ersetzt "Primary goal: Move conversations from discussion to concrete integration" mit "you contribute when you have a concrete technical argument; you stay silent otherwise". Sales-Funnel-Direktive durch Engineering-Norm ersetzt.

2. **Frame-Section** macht "Belegen statt Anpreisen" zur ersten Lesart, mit explizitem Selbsttest (das ist Regel 5 im Prompt-Text, zusätzlich zum Pipeline-Score in Section 5 unten).

3. **Opener-Requirement** ersetzt "Closing action" als wichtigste Struktur-Vorgabe. Die alte Closing-Action-Regel hat strukturell zum Endpoint-Drop-Pattern geführt — die neue Opener-Regel zwingt Substanz im ersten Satz.

4. **Endpoint-Rule** macht das was vorher "they work, partners should use them" sagte zum opt-in-Mechanismus mit klarem Trigger (Mention in 14d-Window).

5. **Forbidden phrases** kodifiziert die Self-Promo-Phrasen die in der Diagnose als problematisch identifiziert wurden.

6. **Single-thread-depth-Hinweis** spiegelt den Harness-Cap (siehe Section 4 unten) im Prompt — damit das Modell weiß dass es sich nicht weiter selbst überholen kann.

---

## 2) Frequenz-Cap-Implementation

### Wo greift der Cap

**Pre-draft**, in `process_monitor_log()` zwischen `is_issue_closed()` und `auto_onboard.handle_comment()`. Begründung wie Lars vorgeschlagen: kein LLM-Aufwand für Drafts die eh nicht rausgehen.

### Neue Helper in `post_log.py`

```python
# Zu post_log.py hinzufügen, am Ende vor `if __name__`:

def count_in_repo(bot_dir: str, repo: str, days: int = 7) -> int:
    """Count posts in a given repo within the last N days."""
    data = _load(bot_dir)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return sum(
        1 for p in data["posts"]
        if p.get("thread", "").startswith(f"{repo}#")
        and p.get("timestamp", "") > cutoff
    )

def count_in_thread(bot_dir: str, thread: str) -> int:
    """Count posts in a thread (lifetime, within retention window)."""
    data = _load(bot_dir)
    return sum(1 for p in data["posts"] if p.get("thread") == thread)

def count_global(bot_dir: str, hours: int = 24) -> int:
    """Count total posts within the last N hours."""
    data = _load(bot_dir)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return sum(1 for p in data["posts"] if p.get("timestamp", "") > cutoff)
```

**Hinweis:** `post_log.py` hat 7d-Retention. Für `count_in_thread` (lifetime) ist das ein Limit — Threads mit Posts älter als 7d werden untercounted. Lösung: `retention_days` in `post_log.json` auf 30 hochsetzen. Risiko: Datei wächst (aktuell leer, also egal).

### Cap-Konstanten in `draft_and_listen.py`

```python
# Neu, nach den anderen Konstanten (etwa Z.45):

FREQ_CAP_PER_REPO_7D = 3
FREQ_CAP_PER_THREAD_24H = 1
FREQ_CAP_GLOBAL_24H = 8
THREAD_ESCALATION_AT = 5   # post #5 → human handoff
```

### Pipeline-Patch in `process_monitor_log()`

**OLD (Z.~525-535, current):**

```python
# Observe-only threads: skip entirely, no draft, no alert, no auto-onboard
thread_key = item.get("key", f"{repo}#{issue_num}")
if is_observe_only(thread_key):
    item["drafted"] = True
    log.info("[OBSERVE] %s - observe_only, skipping entirely", thread_key)
    continue

# Skip closed issues - no draft, no alert
if is_issue_closed(repo, issue_num):
    item["drafted"] = True
    log.info("[SKIP] %s#%s - issue closed, no draft generated", repo, issue_num)
    continue

handled = handle_comment(repo, issue_num, author, body_text)
```

**NEW:**

```python
# Observe-only threads: skip entirely, no draft, no alert, no auto-onboard
thread_key = item.get("key", f"{repo}#{issue_num}")
if is_observe_only(thread_key):
    item["drafted"] = True
    log.info("[OBSERVE] %s - observe_only, skipping entirely", thread_key)
    continue

# Skip closed issues - no draft, no alert
if is_issue_closed(repo, issue_num):
    item["drafted"] = True
    log.info("[SKIP] %s#%s - issue closed, no draft generated", repo, issue_num)
    continue

# [NEW] Frequency caps - pre-draft gate
cap_reason = check_frequency_caps(repo, thread_key)
if cap_reason:
    item["drafted"] = True
    log.info("[CAP] %s - skipped: %s", thread_key, cap_reason)
    continue

# [NEW] Single-thread escalation - at post #5 in same thread
thread_count = post_log.count_in_thread(BOT_DIR, thread_key)
if thread_count >= THREAD_ESCALATION_AT - 1:   # next post would be #5+
    draft = create_draft(item)   # generate draft so Lars can decide
    if draft is not None:
        escalate_thread_to_human(item, draft, thread_count + 1)
    item["drafted"] = True
    continue

handled = handle_comment(repo, issue_num, author, body_text)
```

### Neue Funktion `check_frequency_caps`

```python
# Neu, vor process_monitor_log:

def check_frequency_caps(repo: str, thread_key: str) -> str | None:
    """Returns reason string if any cap is hit, else None."""
    if post_log.count_global(BOT_DIR, hours=24) >= FREQ_CAP_GLOBAL_24H:
        return f"global cap hit ({FREQ_CAP_GLOBAL_24H}/24h)"
    if post_log.count_in_repo(BOT_DIR, repo, days=7) >= FREQ_CAP_PER_REPO_7D:
        return f"repo cap hit ({FREQ_CAP_PER_REPO_7D}/7d for {repo})"
    if post_log.has_posted_recently(BOT_DIR, thread_key, hours=24):
        return f"thread cap hit ({FREQ_CAP_PER_THREAD_24H}/24h for {thread_key})"
    return None
```

**Hinweis:** `has_posted_recently` existiert bereits mit dem genau richtigen Signatur — ich nutze es statt einer neuen Funktion.

### Was passiert wenn Cap getroffen

- Item wird `drafted = True` markiert (Monitor sieht es nicht mehr als pending)
- Log-Eintrag mit Cap-Grund
- Kein Telegram-Alarm (würde Lars unnötig nerven)
- Kein Draft erzeugt → kein LLM-Cost

---

## 3) Single-Thread-Eskalation (Post #5 → Human)

### Trigger

`post_log.count_in_thread(BOT_DIR, thread_key) >= 4` und ein neuer pending Item für selben Thread → der NEUE wäre Post #5.

### Was passiert

1. Draft wird trotzdem erzeugt (`create_draft`) — Lars soll Inhalt sehen können
2. `escalate_thread_to_human(item, draft, thread_count_post_this)` schickt Telegram
3. KEIN Auto-Post, kein Standard-HITL-Approval-Flow
4. Item drafted=True markieren

### Neue Funktion `escalate_thread_to_human`

```python
def escalate_thread_to_human(item: dict, draft: str, post_number: int):
    """Send escalation Telegram for threads at depth threshold.
    No draft_id is created -- Lars handles via browser, not via /approve."""
    thread_key = item.get("key", "")
    repo, issue_num = thread_key.split("#", 1) if "#" in thread_key else (thread_key, "?")
    url = f"https://github.com/{repo}/issues/{issue_num}"
    msg = (
        f"\U0001f6d1 <b>SINGLE-THREAD CAP</b>\n\n"
        f"Thread: <a href=\"{url}\">{thread_key}</a>\n"
        f"This would be MoltyCel post #{post_number} in this thread.\n"
        f"Cap is {THREAD_ESCALATION_AT} -- handing off to you.\n\n"
        f"<b>Draft (for reference, NOT auto-postable):</b>\n"
        f"<i>{_html_escape(draft[:1500])}</i>\n\n"
        f"Decide:\n"
        f"  (a) post yourself in browser\n"
        f"  (b) reply to this Telegram with /escalate_post {thread_key} -- I post once\n"
        f"  (c) reply with /escalate_skip {thread_key} -- drop the draft"
    )
    send_telegram(msg)
    log.info("[ESCALATE] %s - sent escalation to Lars (post #%d)", thread_key, post_number)
```

### Neue Telegram-Commands `/escalate_post` und `/escalate_skip`

In `handle_message(message)` Z.647 — neuer if-Branch (Skizze, in Implementation auszuarbeiten):

```python
elif text.startswith("/escalate_post "):
    thread_key = text.split(maxsplit=1)[1].strip()
    # Find the most recent draft file for this thread in DRAFT_DIR
    # Post once via post_to_github, mark thread escalated_done in agent_memory
    [...]

elif text.startswith("/escalate_skip "):
    thread_key = text.split(maxsplit=1)[1].strip()
    # Mark thread as escalated_skipped in agent_memory, drop pending drafts
    [...]
```

**Offene Frage für Lars:** soll `/escalate_post` einen Draft posten der vor 30 Min gemacht wurde, oder einen frisch generierten? Empfehlung: cached, mit `/escalate_post_fresh` als alternative. Cached spart LLM-Cost und vermeidet Race-Conditions wenn Lars zwischen Generierung und Post weiterdiskutieren wollte.

---

## 4) Spec/Code/Trace-Opener-Validierung

### Strategie: Hybrid Regex + LLM-Self-Check

**Warum nicht nur Regex:** zu strikt → false rejects auf gültige Posts. **Warum nicht nur LLM:** zu lasch + zusätzliche LLM-Call-Latenz. Hybrid: Regex zuerst (cheap), bei Failure → LLM-self-check als Tiebreaker.

### Regex-Pattern-Set

```python
# Neu in draft_and_listen.py vor validate_draft:

import re

OPENER_VALID_PATTERNS = [
    # Spec section reference
    re.compile(r"§\s*\d", re.UNICODE),                # actual paragraph sign
    re.compile(r"\bSection\s+\d+(\.\d+)*\b", re.IGNORECASE),
    re.compile(r"\bRFC\s+\d{3,5}\b", re.IGNORECASE),
    # Code-shape: backticks with non-trivial content
    re.compile(r"`[A-Za-z_][A-Za-z0-9_./()\-]{2,}`"),
    # File path with line number
    re.compile(r"`?[A-Za-z0-9_./\-]+\.(py|ts|js|md|json|yaml|sol|rs):\d+`?"),
    # Number with unit
    re.compile(r"\b\d+\s*(ms|s|kB|MB|bytes|tokens?|chars|hashes?|TXs?)\b", re.IGNORECASE),
    # Hex hash (tx, sha256)
    re.compile(r"\b0x[a-f0-9]{8,64}\b", re.IGNORECASE),
    # Version
    re.compile(r"\bv\d+\.\d+(\.\d+)?\b"),
    # HTTP probe trace
    re.compile(r"\b(GET|POST|PATCH|PUT|DELETE)\s+/[a-z]"),
    # JSON-shape
    re.compile(r'^"[a-z_]+":\s', re.MULTILINE),
]

OPENER_INVALID_LEADIN = re.compile(
    r"^@\w+\s+[—\-]+\s+(solid|great|exact|fascinat|appreciated|thanks|"
    r"interesting|nice|right|absolutely|indeed)",
    re.IGNORECASE
)
```

### Neue Funktion `validate_opener`

```python
def validate_opener(draft_text: str) -> tuple[bool, str]:
    """Return (passes, reason). Apply to draft FIRST sentence."""
    # First sentence = up to first . ! ? followed by space or newline, or first newline
    m = re.search(r"[.!?](?:\s|$)|\n", draft_text)
    first = draft_text[:m.start()+1].strip() if m else draft_text[:200].strip()

    if OPENER_INVALID_LEADIN.search(first):
        return False, f"opener starts with weak lead-in: {first[:80]}"

    for pat in OPENER_VALID_PATTERNS:
        if pat.search(first):
            return True, ""

    # Fallback: LLM self-check
    return _opener_llm_check(first)


def _opener_llm_check(first_sentence: str) -> tuple[bool, str]:
    """Last-resort LLM check. Cheap Haiku call."""
    prompt = (
        f"Does this sentence open with a concrete technical anchor "
        f"(spec reference, code, file path, number with unit, verified trace, "
        f"hash, version)? Answer ONLY yes or no.\n\nSentence: {first_sentence}"
    )
    try:
        ans = claude_draft(prompt, model="claude-haiku-4-5", max_tokens=8).strip().lower()
        if ans.startswith("y"):
            return True, ""
        return False, f"opener not anchored (LLM check): {first_sentence[:80]}"
    except Exception:
        return True, ""   # fail open if LLM fails
```

**Hinweis:** `claude_draft()` (Z.147) muss optionale `model` und `max_tokens` Parameter bekommen — derzeit ist es vermutlich auf claude-sonnet-4 hardcoded. Diff dort:

```python
# OLD
def claude_draft(prompt):
    # uses claude-sonnet-4-20250514

# NEW
def claude_draft(prompt, model="claude-sonnet-4-20250514", max_tokens=1024):
    # accepts override for cheap haiku self-checks
```

### Wo eingebunden

In `validate_draft(draft_text)` Z.425 als zusätzlicher Check VOR den existierenden:

**OLD (Z.425-430, beginning):**

```python
def validate_draft(draft_text: str) -> tuple:
    """[...] Checks: 1. typo, 2. endpoint whitelist [...]"""
    import re

    # Typo check
    typo_matches = re.findall(...)
    [...]
```

**NEW:**

```python
def validate_draft(draft_text: str) -> tuple:
    """[...] Checks: 1. opener pattern, 2. typo, 3. endpoint whitelist [...]"""
    import re

    # [NEW] Opener pattern check
    ok, reason = validate_opener(draft_text)
    if not ok:
        return False, reason

    # Typo check (existing)
    typo_matches = re.findall(...)
    [...]
```

### Failure-Handling: 2 Retries dann Skip

In `create_draft(item, edit_instruction=None)` Z.333 — neue retry-Loop:

**OLD (Z.333-348):**

```python
def create_draft(item, edit_instruction=None):
    repo = item.get("repo", "")
    [...]
    full_context = build_draft_context(repo, issue, author, body)

    if edit_instruction:
        prompt = f"{full_context}\n\nPrevious draft:\n..."
    else:
        prompt = full_context

    return claude_draft(prompt)
```

**NEW:**

```python
def create_draft(item, edit_instruction=None):
    repo = item.get("repo", "")
    [...]
    full_context = build_draft_context(repo, issue, author, body)

    if edit_instruction:
        prompt = f"{full_context}\n\nPrevious draft:\n..."
    else:
        prompt = full_context

    # [NEW] Retry loop on opener-validation failure
    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES + 1):
        draft = claude_draft(prompt)
        ok, reason = validate_opener(draft)
        if ok:
            return draft
        if attempt < MAX_RETRIES:
            log.info("[OPENER] retry %d: %s", attempt + 1, reason)
            prompt = (
                f"{prompt}\n\nPrevious attempt failed opener validation: {reason}\n"
                f"Rewrite. First sentence MUST contain spec reference, code, "
                f"file path, number+unit, verified trace, hash, or version. "
                f"Do NOT start with '@username + emotional lead-in'."
            )
    log.warning("[OPENER] gave up after %d retries - skipping post for %s",
                MAX_RETRIES, item.get("key", ""))
    return None   # signal to caller: skip
```

Caller in `process_monitor_log` muss `if draft is None: continue` handhaben (1-Zeilen-Patch an allen create_draft-Aufruf-Sites).

---

## 5) "Belegen statt Anpreisen"-LLM-Selbsttest

### Strategie: Neuer 4. Score-Faktor in `review_draft`

Bisher 3 Scores: `human_score (GPT-4o)`, `content_score (Gemini)`, `novelty (Claude Haiku)`. Neuer Score: `frame_score (Claude Haiku, "Belegen vs. Anpreisen")`. Combined wird neu gewichtet.

### Neue Funktion `claude_frame_score`

```python
def claude_frame_score(draft: str, repo: str) -> float:
    """Returns 0.0 (anpreisend) to 1.0 (belegen). Threshold-applicable in review_draft."""
    prompt = (
        "You are evaluating a draft GitHub comment from MoltyCel (the bot account "
        "of MolTrust, a DID/VC trust-infrastructure project).\n\n"
        "Question: Would this post still make sense if MoltyCel worked at SINT, "
        "AgentNexus, or APS (other DID/identity projects) instead of MolTrust -- "
        "i.e., does it bring an argument about the thread topic that any senior "
        "identity-infra engineer could make, just by swapping the project name?\n\n"
        "If yes (the post is BELEGEND -- presents MolTrust as evidence-source for a "
        "topic-relevant argument), score high.\n"
        "If no (the post is ANPREISEND -- pushes MolTrust as a solution to be "
        "adopted, drops endpoints, or pitches integration), score low.\n\n"
        "Return ONLY a number between 0.0 and 1.0, no explanation.\n\n"
        f"Draft:\n{draft}\n\nRepo: {repo}"
    )
    try:
        ans = claude_draft(prompt, model="claude-haiku-4-5", max_tokens=10).strip()
        m = re.search(r"[01]?\.\d+|[01]\b", ans)
        if not m:
            return 0.5
        score = float(m.group())
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.5   # neutral fallback
```

### `review_draft` neu

**OLD (Z.311-330):**

```python
def review_draft(draft, item):
    """Two-stage review: human score (GPT) + content score (Gemini)."""
    human_score = gpt4o_quality(draft)
    [...]
    novelty = claude_novelty_score(draft, thread_comments)
    # Weighted average: 0.3 human + 0.3 content + 0.4 novelty
    combined = 0.3 * human_score + 0.3 * content_score + 0.4 * novelty
    return {
        "human_score": human_score,
        "content_score": content_score,
        "combined": combined,
        [...]
    }
```

**NEW:**

```python
def review_draft(draft, item):
    """Three-stage review + frame check."""
    human_score = gpt4o_quality(draft)
    [...]
    novelty = claude_novelty_score(draft, thread_comments)
    # [NEW] frame score
    frame = claude_frame_score(draft, item.get("repo", ""))
    # Re-weighted: 0.2 human + 0.2 content + 0.3 novelty + 0.3 frame
    combined = 0.2 * human_score + 0.2 * content_score + 0.3 * novelty + 0.3 * frame

    return {
        "human_score": human_score,
        "content_score": content_score,
        "novelty": novelty,
        "frame_score": frame,                          # [NEW]
        "combined": combined,
        "reason": content_review.get("reason", ""),
        "suggestion": content_review.get("suggestion", ""),
        "passes": combined >= get_auto_approve_threshold(item.get("repo", "")),
        "frame_pass": frame >= 0.6,                    # [NEW] hard floor
        "threshold": get_auto_approve_threshold(item.get("repo", "")),
    }
```

### Hard Floor: frame_score < 0.6 → Skip-Post

In `process_monitor_log` (Z.~570 wo `combined` geprüft wird):

```python
if not review.get("frame_pass", True):
    log.info("[FRAME] %s - skip: anpreisend (frame=%.2f)",
             thread_key, review["frame_score"])
    item["drafted"] = True
    # Optional: telegram alert wenn 3 frame-fails in folge (Counter in agent_memory)
    continue
```

### Failure-Handling

- frame_score < 0.6 → skip post (kein Telegram, nur Log)
- 3 frame-failures in folge → Telegram-Notification "MoltyCel ist drift, prüfe System-Prompt"
- frame_score 0.6-0.8 → normal HITL-Path (Lars sieht im Telegram-Draft auch frame_score = ...)
- frame_score >= 0.8 → wie bisher

---

## 6) Test-Plan

### Fixtures (5 historische Threads)

| # | Thread | Aktuelle MoltyCel-Posts | Erwartung neuer Bot |
|---|--------|------------------------|---------------------|
| F1 | a2aproject/A2A#1717 | 29 | nach Post 4 → escalation an Lars; frame_score auf endpoint-drop-Posts < 0.6 → skip; Frequenz-Cap (3/Repo/7d) trifft nach 3 Posts in a2aproject |
| F2 | microsoft/autogen#7525 | 13 | frame_score < 0.6 für "integration path" Posts → skip; Repo-Cap (3/7d) trifft schnell |
| F3 | x402-foundation/x402#1777 | 27 | gleiche Pattern wie F1 (kevinkaylie-Onboarding-Posts); frame_score-Failures + thread-escalation |
| F4 | sint-ai/sint-protocol#127 (positive Kontroll) | 0 (pshkv-Thread) | normal → Draft mit Spec-Opener sollte durch validate_opener gehen, frame_score >= 0.6 |
| F5 | aeoess/agent-governance-vocabulary#35 (mention-Thread) | 1 (mit @MoltyCel-Mention) | Endpoint-Mention erlaubt (14d-Window-Trigger), Draft passt; Cap-Counter inkrementiert |

### Test-Skript-Skelett (Vorschlag, NICHT deployen)

```bash
# /tmp/moltycel_refit_test.sh
# Run AGAINST a stage copy, NOT against ~/moltycelbot

set -euo pipefail
STAGE_DIR=/tmp/moltycel-stage
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
cp -r ~/moltycelbot/. "$STAGE_DIR/"

# Apply diffs in $STAGE_DIR (manual, after Lars review of this doc)
# ...

# Per Fixture: build a fake monitor item and run the gates in order
python3 - <<PYTEST
import sys; sys.path.insert(0, "$STAGE_DIR/scripts")
sys.path.insert(0, "$STAGE_DIR")
import draft_and_listen as m
import post_log

# Override BOT_DIR to stage
m.BOT_DIR = "$STAGE_DIR"

fixtures = [
  {"key":"a2aproject/A2A#1717","repo":"a2aproject/A2A","issue":1717,
   "author":"kevinkaylie","body":"...prior thread context..."},
  {"key":"microsoft/autogen#7525","repo":"microsoft/autogen","issue":7525,
   "author":"EchoOfDawn","body":"..."},
  {"key":"x402-foundation/x402#1777","repo":"x402-foundation/x402","issue":1777,
   "author":"someone","body":"..."},
  {"key":"sint-ai/sint-protocol#127","repo":"sint-ai/sint-protocol","issue":127,
   "author":"pshkv","body":"...spec discussion..."},
  {"key":"aeoess/agent-governance-vocabulary#35","repo":"aeoess/agent-governance-vocabulary",
   "issue":35,"author":"aeoess","body":"@MoltyCel can you share your endpoint?"},
]

# F1, F2, F3: pre-seed post_log so caps will trigger
for repo in ["a2aproject/A2A","microsoft/autogen","x402-foundation/x402"]:
    for i in range(3):
        post_log.log_post("$STAGE_DIR", f"{repo}#{1717-i}", f"fake_id_{i}",
                          "fake body", "MoltyCel")

for f in fixtures:
    print("===", f["key"])
    print("  cap:", m.check_frequency_caps(f["repo"], f["key"]))
    print("  thread_count:", post_log.count_in_thread("$STAGE_DIR", f["key"]))
    # If no cap hit, simulate draft + opener-check + frame-score
    [...]
PYTEST
```

### Pass-Kriterien

- F1, F3 (high-volume threads): nach max 5 Posts MUSS escalation feuern; Cap (3/Repo/7d) trifft sogar früher → Test-Pass.
- F2 (autogen): frame_score < 0.6 für mindestens 3 von 5 historischen Posts ("integration path", "endpoint" Drops) → Test-Pass.
- F4 (positive Kontrolle): mind. 1 Draft mit validate_opener=True + frame_score >= 0.6 → Test-Pass.
- F5 (mention-Thread): Endpoint-Drop ist erlaubt nach Mention-Window-Check → Test-Pass.

### Wie laufen lassen

```bash
# 1. Stage copy (no production touch)
cp -r ~/moltycelbot /tmp/moltycel-stage

# 2. Apply diffs in /tmp/moltycel-stage/ (per Section 1-5 above)

# 3. Run unit-test-style invocations against fixtures
python3 /tmp/moltycel_refit_test.py

# 4. Inspect logs for expected skip/escalate/pass behaviors

# 5. Report to Lars; nothing in /home/moltstack/moltycelbot/ touched yet
```

---

## 7) Deploy-Vorgehen (Lars-Decision-Punkt)

**Nichts wird ohne explizite Lars-Freigabe deployed.** Vorschlag wenn approved:

1. Backup: `cp draft_and_listen.py draft_and_listen.py.bak-pre-refit-{timestamp}`
2. Backup: `cp ~/moltycelbot/post_log.py ~/moltycelbot/post_log.py.bak-pre-refit-{timestamp}`
3. Edits anwenden in dieser Reihenfolge: post_log.py erweitern → draft_and_listen.py Konstanten + neue Funktionen → System-Prompt ersetzen → Pipeline-Patch → review_draft erweitern
4. `python3 -m py_compile` smoke-test
5. `systemctl restart moltycel-bot.service`
6. 24h-Monitoring: Telegram-Drafts ankommen, frame_score in Logs, kein Cap-Bypass-Bug
7. Bei Anomalie: rollback via `mv ...bak ...` + restart

**Alternative — Phasenweise:**
- **Phase A (zuerst):** System-Prompt ersetzen (Section 1). Rein konfigurativ, kein Code-Risiko. 24h beobachten.
- **Phase B:** Caps + Escalation (Section 2 + 3). Architektonisch eingreifend, aber Telegram-HITL bleibt unberührt.
- **Phase C:** Opener-Validation (Section 4). Einführt LLM-Retry-Loop, kann Latenz erhöhen.
- **Phase D:** Frame-Score (Section 5). Zusätzliche LLM-Cost (Haiku-Call pro Draft). Letzter Schritt damit Cost-Profil beobachtbar bleibt.

---

## Offene Punkte für Lars

1. **Cap-Werte**: 3/Repo/7d, 1/Thread/24h, 8/global/24h — bewusst konservativ. pshkv Median 31/Woche entspräche ~4/Tag global. Ist 8/Tag-Decke richtig oder zu großzügig? Pshkv-Median ist über *2 aktive Wochen*, also mit Pausen. Tagesdecke 8 erlaubt Burst aber kein Hochfrequenz-Pattern.

2. **`/escalate_post`**: cached Draft posten oder fresh re-generieren? Empfehlung: cached (LLM-Cost), `/escalate_post_fresh` als alternative.

3. **frame_score-Floor 0.6**: zu streng (zu viele Skips), zu lasch (Anpreisen-Drift bleibt)? Vorschlag: 4 Wochen lang loggen ohne enforcement, dann anhand Verteilung kalibrieren. Bis dahin Floor=0.5 als soft-warning, kein skip.

4. **`retention_days` in post_log.json**: aktuell 7. Für `count_in_thread` (lifetime) brauchen wir 30+. Risiko: File-Größe (aktuell leer, also egal).

5. **System-Prompt Sprache**: Englisch beibehalten (bisheriger Stil) oder hybrid? Vorschlag: Englisch (Bot postet auf englischen GH-Threads).

6. **Forbidden phrases**: Liste vollständig? Vorschlag-Erweiterung: "ship", "live", "production-ready" — alle Closing-Action-Triggers aus alter Closing-Action-Regel. Aber Vorsicht: "live" in technischen Kontexten ("the spec is live in the registry") sollte erlaubt bleiben. Pattern-basierte Forbidden-Liste oft zu grob.

7. **Hardcoded Modell in `claude_draft()`** (Z.147): heute claude-sonnet-4-20250514. Section 4+5 brauchen Haiku-Aufrufe (cheap self-checks). Empfehlung: `claude_draft(prompt, model=..., max_tokens=...)` als optionale Override. Plus bei der Gelegenheit: Haupt-Modell auf claude-haiku-4-5 oder claude-opus-4-7 migrieren? Diagnose Hardening-Item 1 ist offen.

_Diff-Ende. Erstellt 2026-04-27 ~12:00 UTC. Nicht deployen ohne Lars-Review._
