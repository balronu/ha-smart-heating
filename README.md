# Smart Heating (Beta 6)

**Smart Heating** ist eine HACS-kompatible Home-Assistant-Integration für
Wochenzeitpläne, Status, Simulation und eine kompakte Lovelace-Karte.

> **Beta-6-Sicherheitsgrenze:** Die Integration berechnet die vollständige
> Heizungsentscheidung passiv. Sie schaltet
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
- Migrationsplan mit Single-Writer-Sperre, Bestätigungstoken, Snapshot,
  Read-back und isoliertem Rollback-Adapter
- erklärbare Entscheidung mit aktivem Modus, Grund, Zieltemperatur und HVAC-Ziel
- getrennter Kompatibilitäts- und Vollmodus
- isolierter Climate-Servicepfad mit Primär-/Tado-Fallback, Read-back und Rollback
- Kompatibilitäts-Sommermodus sowie ausdrücklich gesperrter HVAC-Off-Planung
- isolierter Home-Assistant-Lifecycle-Test für Flow, Entities und Neustart

## Installation

Beta 6 ist ein GitHub-Prerelease. In HACS muss die Vorabversion explizit
aktiviert werden. Danach über **HACS → Integrationen → Smart Heating**
installieren. Ein erforderlicher Home-Assistant-Neustart ist separat zu
prüfen und darf erst nach Freigabe durchgeführt werden.

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

### Beta-6-Installationsassistent

Die Migrations-Preview zeigt erkannte Entities und Konflikte. Der
Kompatibilitätsmodus ist der sichere Standard: Smart Heating beobachtet den
Zeitplan und lässt die bestehende Automation am Thermostat schreiben. Wenn
Simple Scheduler keinen unterstützten Export bereitstellt, verlangt die UI
einen validierten manuellen Vorschlag. Der Vollmodus bleibt gesperrt, bis ein
einzelner Schreiber in einer ausdrücklich isolierten Umgebung nachgewiesen ist.

Der Schornsteinfeger-Modus hat in der Entscheidungsansicht absolute Priorität.
Ein Sollwert oder `hvac_action` beweist jedoch keinen Brennerstart.

## Referenzmigration

Die Referenzanlage nutzt `input_boolean.heizung` als Zeit-/Kalenderstatus und
hat Sondermodi mit einer dokumentierten Priorität. Die ursprünglichen Simple-
Scheduler-Zeitpläne werden als **unverifizierte Importquelle** behandelt, bis
ein unterstützter Export vorliegt:

- Montag–Freitag Heizbeginn 05:30
- Samstag–Sonntag Heizbeginn 07:00
- Sonntag–Donnerstag Absenkung 21:00
- Freitag–Samstag Absenkung 22:00

Beta 6 übernimmt diese Werte nicht automatisch und schreibt `input_boolean.heizung`
nicht. Die Migrations-Preview zeigt nur einen Konflikt-/Prüfstatus. Der
ausführbare Adapter akzeptiert Schreibzugriffe ausschließlich über einen
isolierten Test-Transport; die Produktiv-Sperre verweigert die Aktivierung,
solange der alte Schreiber nicht nachweisbar abgelöst ist.

## Entscheidungslogik

Die Referenzreihenfolge ist unverändert: Schornsteinfeger → fehlende
Heizfreigabe → Fenster offen → Fenster gekippt → Abwesenheit → Nacht/Party →
Sommermodus ohne Komfortoverride → Komfort. Die Karte trennt Zeitplanstatus,
berechneten Heizmodus und tatsächliche Produktivsteuerung. Die Beta führt keine
Climate- oder Helper-Services aus.

**Schornsteinfeger hat absolute Priorität:** Auch bei 40 °C Außentemperatur,
Sommermodus, ausgeschalteter Heizfreigabe, Nacht, Abwesenheit und offenen
Fenstern wird im Planer `heat` mit der konfigurierten
Schornsteinfeger-Solltemperatur angefordert. Ein hoher Sollwert allein wird
nicht als Brennerstart behauptet; dafür muss das Gerät `hvac_action` oder einen
gleichwertigen Wärmeerzeugerstatus liefern.

## Entwicklung

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q custom_components tests
git diff --check
```

Die HA-abhängigen Adapter werden in CI mit Home Assistant 2026.10.4 in einer
isolierten Fixture getestet. Eine Installation in produktiver VM 104 ist kein
Teil der Beta-6-Entwicklung. Der Kompatibilitätsmodus ist passiv; der Vollmodus
bleibt bis zu einem gesondert geprüften Single-Writer-Nachweis gesperrt.

## Status

Version: `0.1.0-beta.6`
Release-Typ: Entwicklungsrelease / HACS-Prerelease  
Produktive Migration: gesperrt; nur isolierter Adapter-Test möglich

Weitere Architektur- und Sicherheitsdetails stehen in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
