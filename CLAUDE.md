# CLAUDE.md — moltrust-api

Repo-spezifische Instruktionen. Voller operativer Rahmen: `docs/WORKFLOW.md` (in **diesem** Repo). Backlog: `docs/BACKLOG.md`.

## Repo-as-Source-of-Truth (HART — WORKFLOW.md §11 V1.2)

- **11.1** Kein Server-Deploy ohne vorherigen gemergten Commit im zuständigen produktiven GitHub-Repo. `post-sha == repo-sha`.
- **11.2** Jede Arbeitsiteration sofort committen, sobald ein Artefakt-Kandidat existiert — Chat-Scratch zählt nicht.
- **11.3** Pro Console ein eigener `git worktree`. Server-schreibende Arbeit seriell — „Server frei" erst nach protokollierter Anfrage+Bestätigung.
- **11.4** Session-Start: `git fetch`, `git worktree list`, `git status`, `origin/main` — frischer Branch ab `origin/main` (0 behind), nie von stale local `main`.

**Geltungsbereich:** repo-verwaltete Dateien. Server-Infra (nginx/systemd/cron) ist **NICHT** repo-verwaltet → bis zur Backlog-Überführung manuelle Sorgfalt + Audit-Eintrag.

Volltext + Begriffsdefinitionen: `docs/WORKFLOW.md` §11.
