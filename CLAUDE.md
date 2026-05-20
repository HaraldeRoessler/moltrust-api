# CLAUDE.md — moltrust-api

Repo-spezifische Instruktionen. Voller operativer Rahmen: `docs/WORKFLOW.md` (in **diesem** Repo). Backlog: `docs/BACKLOG.md`.

## Repo-as-Source-of-Truth (HART — WORKFLOW.md §11 V1.2)

- **11.1** Kein Server-Deploy ohne vorherigen gemergten Commit im zuständigen produktiven GitHub-Repo. `post-sha == repo-sha`.
- **11.2** Jede Arbeitsiteration sofort committen, sobald ein Artefakt-Kandidat existiert — Chat-Scratch zählt nicht.
- **11.3** Pro Console ein eigener `git worktree`. Server-schreibende Arbeit seriell — „Server frei" erst nach protokollierter Anfrage+Bestätigung.
- **11.4** Session-Start: `git fetch`, `git worktree list`, `git status`, `origin/main` — frischer Branch ab `origin/main` (0 behind), nie von stale local `main`.

**Geltungsbereich:** repo-verwaltete Dateien. Server-Infra (nginx/systemd/cron) ist **NICHT** repo-verwaltet → bis zur Backlog-Überführung manuelle Sorgfalt + Audit-Eintrag.

## Discovery-Checklist (HART — nichts gilt als "fertig" bevor entdeckbar)

Nach jeder neuen Seite, jedem neuen Endpoint, jedem neuen Publikations-Artefakt:

- [ ] `sitemap.xml` aktualisiert (URL + realistisches `lastmod` aus git-Commit-Stand der Datei, nicht heutiges Datum)
- [ ] `llms.txt` aktualisiert (Eintrag in passendem Block)
- [ ] Bei neuen Endpoints: Agent-Card / `.well-known/` und OpenAPI-Contract aktualisiert
- [ ] Sitemap deployt (Phase-A/B, `post-sha == repo-sha`, Live-curl-Probe)
- [ ] GSC-Sitemap-Re-Submit angestoßen: <https://search.google.com/search-console/sitemaps?resource_id=https%3A%2F%2Fmoltrust.ch%2F> (eingeloggt als `clipperati2015@gmail.com`)
- [ ] `noindex,nofollow` respektieren — Seiten mit diesem Meta **nicht** in Sitemap aufnehmen

**Begründung:** „Entdeckbarkeit = Definition of Done" — Lesson aus GROUP-5-Nachzug Mai 2026: 5 Seiten waren live, aber wochenlang nicht in Sitemap → für Crawler unsichtbar trotz vorhandenem Inhalt.

Volltext + Begriffsdefinitionen: `docs/WORKFLOW.md` §11.
