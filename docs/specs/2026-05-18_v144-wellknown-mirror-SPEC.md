# Spec — V1.4-4: .well-known-Mirror + Versionierung + RFC-8594-Deprecation (9 Sektionen)

**Status:** ENTWURF — Lars-Freigabe vor Code.
**§2.3-Cross-Review:** bewusster, begründeter **Skip** — Infrastruktur/Build-Pipeline + statische Auslieferung, kein Auth-/Credential-/Token-Pfad. State-Check ergab nichts Security-Relevantes.
**Datum:** 2026-05-18 · **Repo:** moltrust-api · **Branch:** docs/v144-wellknown-mirror-spec
**BACKLOG-Mapping (verifiziert):** `### .well-known-Mirror-Generierung + Deprecation-Header (Phase-1-Analyse §8 Punkt 4)` (## Medium). „V1.4-4" ist Sprechweise, nicht BACKLOG-Nummer.

## 1. Goal
`moltrust.ch/.well-known/agent-card.json` als **generierter Mirror** der **kanonischen** `api.moltrust.ch`-Quelle aufsetzen (statt zweier hand-gepflegter Kopien, Drift-Risiko, INC-08). Zusätzlich: Versionierungs-Schema der Auslieferung + RFC-8594-`Deprecation`/`Sunset`-Header.

## 2. Non-Goals
- Keine inhaltliche Änderung der agent-card-Daten (CAEP-Extension = V1.4-3).
- Keine API-Contract-Versionsentscheidung (das ist V1.4-5b/5c/5d).
- Kein Breaking-Change-Pfad-Design (5c, Produktentscheidung).

## 3. Architecture-Layer-Scope *(Pflichtfeld)*
- **Build/Deploy:** Generator, der den Mirror aus der kanonischen Quelle ableitet (Pull/Build-Step), + Auslieferung statisch unter moltrust.ch.
- **Edge/HTTP:** `Deprecation`/`Sunset`-Header (RFC 8594) für versionierte/abgelöste Ressourcen.
- **NICHT betroffen:** API-Handler-Logik, DB, Auth.

## 4. Data-Model-Changes
Keine DB-Änderung. Artefakt-Fluss kanonisch→Mirror; ggf. Build-Manifest/Versions-Metadatei (Form offen, §9).

## 5. API-Contract-Changes
- Verifizierter Ist-Zustand: beide URLs liefern 200, identische 7926 B; **kein** `Deprecation`/`Sunset`-Header. (Ob die moltrust.ch-Kopie heute hand-gepflegt oder bereits generiert ist, ist extern nicht beweisbar — Phase-1 INC-08 sagt hand-gepflegt/Drift-Risiko; **Verifikationspunkt bei Implementierung, nicht raten**.)
- Ziel: Mirror byte-deterministisch aus kanonischer Quelle; `Deprecation`/`Sunset` (RFC 8594) wo eine Ressource abgelöst wird; Versionierungs-Schema der ausgelieferten well-known-Artefakte.

## 6. Migration-Path
1. Generator etablieren; Mirror einmal aus kanonischer Quelle erzeugen; Byte-Diff gegen heutige moltrust.ch-Kopie (Drift sichtbar machen, dokumentieren).
2. Cut-over moltrust.ch auf generierten Mirror; Cron/Build-Hook für Re-Generierung bei Quelländerung.
3. RFC-8594-Header schrittweise einführen.
4. Abhängigkeit: V1.4-3 (CAEP-Extension) sollte vor dem Mirror-Cutover in der Quelle sein, sonst Mirror ohne CAEP — Sequenz-Hinweis, kein Hard-Block.

## 7. Rollback-Plan
moltrust.ch zurück auf statische Kopie (heutiger Zustand); Generator/Hook deaktivieren; Header entfernen. Folgenlos (Auslieferungsebene, keine Daten/State).

## 8. Success-Criteria
1. moltrust.ch/.well-known/* byte-identisch aus kanonischer api.moltrust.ch-Quelle generiert; kein manueller Pflege-Pfad mehr.
2. Quelländerung → Mirror zieht automatisch nach (kein Drift mehr).
3. RFC-8594 `Deprecation`/`Sunset` für abgelöste Ressourcen vorhanden + korrekt.
4. Regressions-frei: aktuelle Konsumenten beider URLs unverändert bedient.

## 9. Open Decisions
- **9.1** Generierungs-Mechanik: Build-Time-Pull vs. Cron-Sync vs. Edge-Proxy/Rewrite — Trade-offs bei Implementierung ausarbeiten (Infra-Entscheidung, kein Raten).
- **9.2** Versionierungs-Schema der well-known-Artefakte ist gekoppelt an V1.4-5b (öffentliche v1-Deklaration) und 5c (Breaking-Change-Pfad, Produktentscheidung) — **nicht hier allein entscheiden**; Querverweis.
- **9.3** Verifikationspunkt: heutige moltrust.ch-Kopie hand-gepflegt vs. generiert (INC-08-Annahme) — bei Implementierung bestätigen.
