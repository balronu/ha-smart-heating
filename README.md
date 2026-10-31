# Smart Heating (Beta 2)

**Smart Heating** ist eine HACS-kompatible Home-Assistant-Integration für
Wochenzeitpläne, Status, Simulation und eine kompakte Lovelace-Karte.

> **Beta-2-Sicherheitsgrenze:** Die Integration arbeitet passiv. Sie schaltet
> keine Climate-Entity, keinen bestehenden Helper, keinen Scheduler und keinen
> Sondermodus. Eine Migration in eine produktive Heizungssteuerung ist nicht
> enthalten.

## Funktionen

- UI-basierter Config Flow und Options Flow
- persistenter Wochenplan in der Config Entry
- mehrere nicht überlappende Fenster pro Wochentag
- serverseitige Zeitberechnung und `next_switch`
- Simulation der dokumentierten Prioritätsreihenfolge
- read-only Diagnose und Migration-Preview
- kompakte responsive Lovelace-Karte mit eigener, validierter Planverwaltung
- deutsche und englische Übersetzungen
- vorsichtige automatische Entity-Erkennung mit sichtbaren Mehrdeutigkeiten
- read-only Migrationsassistent mit Fixture, Konflikten und manuellem Vorschlag
- isolierter Home-Assistant-Lifecycle-Test für Flow, Entities und Neustart

## Installation

Beta 2 ist ein Entwicklungsrelease und wird erst nach erfolgreichem CI-Gate
als GitHub-Prerelease veröffentlicht. In HACS muss die Vorabversion explizit
aktiviert werden. Danach über **HACS → Integrationen → Smart Heating**
installieren und Home Assistant neu starten.

Alternativ kann das Repository als benutzerdefiniertes HACS-Repository
(`Integration`) hinzugefügt werden. Die Integration darf zunächst nur in einer
Testinstanz installiert werden.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Smart
   Heating**.
2. Name und Zeitzone festlegen.
3. Optional vorhandene Climate-/Helper-Entities ausdrücklich zuordnen.
4. Die Karte mit `entry_id` der Config Entry in ein Testdashboard aufnehmen:

```yaml
type: custom:smart-heating-card
entry_id: YOUR_CONFIG_ENTRY_ID
```

Die Karte bearbeitet ausschließlich den Zeitplan dieser Smart-Heating-Entry.
Sie schreibt keine bestehenden Heizungs-Entities.

## Referenzmigration

Die Referenzanlage nutzt `input_boolean.heizung` als Zeit-/Kalenderstatus und
hat Sondermodi mit einer dokumentierten Priorität. Die ursprünglichen Simple-
Scheduler-Zeitpläne werden als **unverifizierte Importquelle** behandelt, bis
ein unterstützter Export vorliegt:

- Montag–Freitag Heizbeginn 05:30
- Samstag–Sonntag Heizbeginn 07:00
- Sonntag–Donnerstag Absenkung 21:00
- Freitag–Samstag Absenkung 22:00

Beta 2 übernimmt diese Werte nicht automatisch und schreibt `input_boolean.heizung`
nicht. Die Migrations-Preview zeigt nur einen Konflikt-/Prüfstatus.

## Entwicklung

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q custom_components tests
git diff --check
```

Die HA-abhängigen Adapter werden in CI mit Home Assistant 2026.10.4 in einer
isolierten Fixture getestet. Eine Installation in produktiver VM 104 ist kein
Teil der Beta-2-Entwicklung.

## Status

Version: `0.1.0-beta.2`
Release-Typ: Entwicklungsrelease / HACS-Prerelease  
Produktive Migration: nicht enthalten  

Weitere Architektur- und Sicherheitsdetails stehen in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
