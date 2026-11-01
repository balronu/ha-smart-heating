# Smart Heating (Beta 38)

## Phase 81 – Passiver Aktorvertrag

Die passive Shadow-Auswertung erzeugt jetzt je Raum einen strikt nicht
ausführenden Aktorplan. Er dokumentiert Zielentität, Fallback-Auswahl,
`climate.set_hvac_mode`/`climate.set_temperature`, Parameter, Entscheidung,
Sondermodus, Priorität, Begründung, Datenqualität und fehlende Nachweise.
Primary und Fallback werden nicht gleichzeitig geplant; der Fallback wird nur
bei nicht verfügbarer Primary-Entität gewählt. Geplante Aktionen bleiben als
Daten mit `execution_status: not_executed` sichtbar und können keine
Home-Assistant-Services auslösen. Eine beobachtete Climate-
`hvac_action` oder ein Tado-Heizbedarf ersetzt weiterhin keinen unabhängigen
Brötje-/Kessel-Rückkanal.

The passive shadow evaluation now emits a strictly non-executing actuator plan
per room. It records the target, deterministic primary/fallback selection,
known climate services, parameters, decision, special mode, priority,
rationale, data quality, and missing evidence. Primary and fallback are never
planned together; fallback is selected only when primary is unavailable.
Planned actions remain data with `execution_status: not_executed` and cannot
call Home Assistant services. Observed `hvac_action` or Tado demand still do
not replace independent boiler/burner feedback.

## Phase 78 – Wochenzeitplan passiv auswerten

Der Wochenplan unterstützt Montag bis Sonntag, mehrere Komfortfenster pro Tag
und Fenster über Mitternacht. Außerhalb der Fenster gilt passiv die
Absenktemperatur; optionale Fenster-Solltemperaturen werden nur in der
Shadow-Entscheidung berücksichtigt. Der Resolver meldet Tages-/Nachtstatus und
die nächste lokale Umschaltung einschließlich Zeitzone/DST. Ein fehlender oder
nicht verifizierter Scheduler blockiert weiterhin die SMART-Umschaltung; es
werden keine Heizbefehle gesendet.

## Phase 78 – Passive weekly schedule evaluation

The weekly plan supports Monday through Sunday, multiple comfort windows per
day, and windows crossing midnight. Outside those windows the passive
setback-temperature decision applies; optional window targets are used only by
the shadow decision. The resolver reports day/night state and the next local
switch including timezone/DST. A missing or unverified scheduler still blocks
SMART cutover, and no heating command is sent.

## Phase 77 – Sondermodus-Wirkungen passiv konfigurieren

Die Verwaltung bietet für Built-in- und benutzerdefinierte Sondermodi ein
gemeinsames, responsives Formular. Räume, Temperaturverhalten, Zeitplan-
Übersteuerung, Fenster-/Anwesenheitsbedingungen, Dauer, Rückkehr zum
Normalbetrieb und zulässige Prioritäten werden im Schema 6 gespeichert und
nach dem erneuten Laden wieder angezeigt. Eine Zusammenfassung und die
passive Resolver-Vorschau zeigen die erwartete Wirkung, ohne Heizbefehle zu
erzeugen. Der Schornsteinfeger bleibt unveränderlich auf Priorität 1000;
Helper und Automationen werden nicht erstellt oder geschaltet.

## Phase 77 – Passive special-mode effects

Built-in and custom special modes share a responsive editor for rooms,
temperature behavior, schedule override, window/presence conditions, duration,
return to normal operation, and allowed priorities. Schema-6 values survive
reload and are summarized with the passive resolver preview; no heating command
is issued. Chimney-sweep remains fixed at priority 1000, and helpers or
automations are never created or switched.

## Phase 76 – passiver Sondermodus-Resolver

Die passive Engine berechnet je Raum, welcher Sondermodus wirksam wäre und
welche Zieltemperatur bzw. Wirkung daraus folgt. Unterstützt werden
Komfort-/Absenk-/feste/relative Temperaturen, Zeitplanübersteuerung,
Fenster- und Anwesenheitsbedingungen, Ablauf und Rückkehr zum Normalbetrieb.
Prioritäten werden deterministisch aufgelöst; Schornsteinfeger bleibt mit
Priorität 1000 absolut vorrangig. Fehlende oder unbekannte Statusquellen
blockieren die Wirkung und werden sichtbar begründet.

Das Ergebnis ist eine Shadow-Entscheidung mit Datenqualität und fehlenden
Scheduler-/Aktorvoraussetzungen. Es werden keine Heizbefehle, Helper- oder
Automationsänderungen ausgeführt; die bestehende Heizungsautomation bleibt
alleinige produktive Steuerungsinstanz.

## Phase 75 – passives Migrationsdatenmodell

Das Management-Modell wird intern als Schema 6 rückwärtskompatibel aus älteren
Konfigurationen normalisiert. Bestehende Räume, Thermostate, Raumfühler,
Fensterkontaktrollen, Wochenpläne und Anwesenheitszuordnungen werden nicht
verworfen. Sondermodi besitzen zusätzlich einen strukturierten passiven
Wirkungsvertrag für Aktivierung, Bedingungen, Zieltemperatur, Zeitplan-
Übersteuerung, Dauer und Rückkehr zum Normalbetrieb.

Der `control_plane`-Zustand ist sicher eingezäunt: `LEGACY` ist der einzige
durch Migration erreichbare Zustand; `TRANSITIONING` und `SMART` bleiben bis zu
einer späteren, separat geprüften Umschaltung blockiert. Das Modell beschreibt
Steuerungshoheit, Bereitschaft, Fehler und Rückfall, führt aber keine
Heizbefehle aus und verändert keine produktiven Home-Assistant-Komponenten.
Unbekannte Entitäten werden nicht automatisch ergänzt. Der Schornsteinfeger-
Modus behält die unveränderliche höchste Priorität.

## Phase 71 – Sondermodus-Draft und mobile UX

Die Verwaltung zeigt vordefinierte und benutzerdefinierte Sondermodi kompakt
und standardmäßig eingeklappt. Verfügbarkeit („zur Verwendung angeboten“) und
der tatsächliche Aktivzustand bleiben getrennt. Neue benutzerdefinierte Modi
werden zunächst nur als lokaler Entwurf erstellt; erst „Anlegen“ speichert sie,
„Abbrechen“ verwirft sie ohne Backend-Schreibzugriff. Fehlende oder unbekannte
Statusquellen werden sichtbar gekennzeichnet. Die Integration bleibt passiv,
erstellt keine Helper und verändert keine Prioritäten.

## Phase 71 – Special-mode drafts and mobile UX

The administration presents built-in and custom special modes as compact,
collapsed entries. Availability (“offered for use”) remains separate from the
actual active state. New custom modes start as local drafts; only “Create”
persists them and “Cancel” performs no backend write. Missing or unknown status
sources are shown explicitly. The integration remains passive, creates no
helpers, and does not change priorities.

## Phase 68 – Raumkontaktrollen erhalten (Beta 38)

Die Raumverwaltung übernimmt gespeicherte Fensterkontaktrollen unverändert in
die Raumdarstellung. Rollen wie `tilt` und `open` bleiben dadurch beim Laden
und erneuten Speichern erhalten; Kontakte ohne gespeicherte Rolle werden nicht
automatisch umgedeutet. Der Betrieb bleibt passiv.

## Phase 57 – Diagnosewerte bleiben sichtbar (Beta 37)

Die Fensterkontakt-Diagnose zeigt vorhandene Kontakte auch dann weiter an,
wenn das Diagnosefeld fehlt oder leer ist. Für ConfigEntry.options, Runtime und
admin/get werden fehlende Werte ausdrücklich als „Nicht vorhanden“ dargestellt;
die Diagnose meldet die fehlende Datenquelle sichtbar. Der Readback akzeptiert
auch verschachtelte Verwaltungsantworten. Speicherlogik, Entities und
produktive Werte bleiben unverändert; der Betrieb bleibt passiv.

## Phase 55 – Diagnosewerte für Fensterkontakte (Beta 36)

Die Verwaltung zeigt für jeden konfigurierten Fensterkontakt eine einklappbare,
rein lesende Quellenprüfung. Sie vergleicht die Rolle aus `ConfigEntry.options`,
dem geladenen Runtime-Snapshot und dem `admin/get`-Readback. Die Anzeige hängt
nicht von `area_id`, `zone_ids` oder einer bereits gesetzten Rolle ab; fehlende
Werte werden ausdrücklich als „Nicht vorhanden“ angezeigt. Wenn das Backend
keine Diagnosewerte liefert, wird dies sichtbar gemeldet. Der passive
Kompatibilitätsmodus, bestehende Zuordnungen und Home-Assistant-Entities
bleiben unverändert.

## Phase 44 – Atomare Raumspeicherung (Beta 33)

Der Raum-Speichervorgang speichert Raumdaten und Fensterkontaktrollen jetzt
atomar über `admin/room/save` und prüft den tatsächlich zurückgelesenen
Config-Entry-Zustand. Abweichungen werden sichtbar als Fehler gemeldet, bevor
eine Erfolgsmeldung erscheint. Bestehende Kontakte und Raumzuordnungen bleiben
erhalten; der Betrieb bleibt passiv und führt keine Heizbefehle aus.

## Phase 42 – Persistenzkorrektur für Fensterkontaktrollen (Beta 32)

Die Rollen **Gekippt-Sensor**, **Offen-Sensor** und **Nicht zugeordnet** bleiben
nach der Auswahl im Raumformular sichtbar und werden erst mit **Raum speichern**
übernommen. Die Speicherung erfolgt geordnet mit anschließendem Readback, damit
mobile Auswahländerungen nicht durch ältere Raumdaten überschrieben werden.
Bestehende Kontakte und Raumzuordnungen bleiben erhalten; der Betrieb bleibt
passiv und es werden keine Heizbefehle ausgeführt.

## Phase 40 – Fensterkontakt-Funktionen (Beta 31)

Die Raumverwaltung erlaubt pro Fensterkontakt die manuelle Funktion
**Gekippt-Sensor**, **Offen-Sensor** oder **Nicht zugeordnet**. Mehrere Kontakte
je Funktion sind möglich. **Offen** hat Vorrang vor **Gekippt**. `unknown` und
`unavailable` bleiben technisch sichtbar und werden ausdrücklich als „Für
Heizungsautomatik ignoriert“ diagnostiziert; ohne gültiges Signal gilt der
Zustand für die passive Automatik als geschlossen. Bestehende Zuordnungen
werden rückwärtskompatibel migriert und nicht anhand von Namen vermutet.

Diese Beta verändert keine Home-Assistant-Entities, Helper, Bereiche,
Zigbee2MQTT-Daten oder Heizungsbefehle.

## Phase 38 backend boundary (Beta 29)

Die Raumverwaltung verwendet für Heizkörper und Thermostate ausschließlich die
Mehrfachauswahl mit Häkchen. Gespeicherte Thermostate werden nach dem Öffnen
wieder ausgewählt und kompakt mit Name, Entity-ID und Verfügbarkeit angezeigt;
der Raumtemperaturfühler bleibt separat. Übernommen wird erst mit „Raum
speichern“. Diese UX-Nachbesserung ist Teil der laufenden Phase 38 und erzeugt
keine neue Release-Version.

Rooms can retain multiple `climate.*` entities while room temperature sensors
remain separate. Legacy single-thermostat data migrates losslessly and
idempotently; duplicate ownership is reported. Window contacts use explicit
semantics and physical groups, with conservative states and deterministic
delays. Special-mode expiry, effects, window handling, and priority are
read-only previews. Compatibility mode remains locked and no HA service is
called by this backend.

## Phase 36 – universeller Sondermodus-Manager

Beta 28 führt eigenständige, stabile Sondermodus-Objekte ein. Die vordefinierten
Modi übernehmen vorhandene Zuordnungen rückwärtskompatibel; benutzerdefinierte
Modi können intern und passiv verwaltet oder lesend an geeignete
`input_boolean`-Entities gebunden werden. Die Auswahl durchsucht Anzeigename
und Entity-ID, trennt Verfügbarkeit, Aktivität und Steuerbarkeit und erstellt
keine HA-Helper automatisch. Die produktive Heizungssteuerung bleibt gesperrt.

Die Lovelace-Karte und eine VM-104-Installation sind nicht Bestandteil dieser Phase.

Globale Betriebs- und Sicherheitswerte werden im Abschnitt „System & Betriebsmodus“
der Smart-Heating-Verwaltung gepflegt. Der native HA-Optionsdialog zeigt nur noch
den Verweis auf diese zentrale Verwaltung und lässt bestehende Werte unverändert.

## Phase 35 – letzter iPhone-UX-Feinschliff

Beta 27 zeigt passende Sondermodus-Helfer als kompakte Empfehlungen und öffnet
weitere `input_boolean`-Quellen erst über die Suche. Gespeicherte, fehlende und
nicht verfügbare Quellen bleiben sichtbar; keine Quelle wird automatisch
gespeichert oder aktiviert. Der Wochenplan startet als kompakte Übersicht mit
kurzen Tageszusammenfassungen, öffnet nur einen Tag zur Bearbeitung und kehrt
nach dem Speichern zur Übersicht zurück. Alle Änderungen bleiben passiv.

Die Lovelace-Karte ist weiterhin nicht Bestandteil dieser Phase.

## Phase 34 – Sondermodi, Außentemperatur und mobile Zuordnungen

Beta 26 bietet für Sondermodi ausschließlich passende `input_boolean`-
Statusquellen mit getrennten Anzeigen für Verfügbarkeit, Aktivität und Status.
Geeignete Party-, Besuch-, Heimweg-, Sommer- und Schornsteinfeger-Helfer werden
passiv vorgeschlagen; bestehende Zuordnungen bleiben auch bei vorübergehender
Nichtverfügbarkeit erhalten. Außentemperaturfühler werden separat priorisiert,
einschließlich gespeicherter, aktuell nicht verfügbarer Quellen.

Die Lovelace-Karte ist weiterhin nicht Bestandteil dieser Phase.

## Phase 32 – kompakter Wochenplan und raumbezogene Fensterverwaltung

Beta 25 veröffentlicht die Phase-32-Änderungen. Der Wochenplan zeigt alle sieben Tage kompakt;
nur der ausgewählte Tag öffnet seine Bearbeitung. Zeitfenster können weiterhin
hinzugefügt, entfernt, kopiert und mit optionaler Zieltemperatur gespeichert
werden. Validierung und Persistenz bleiben serverseitig wirksam.

Fenster- und Türkontakte werden direkt im Smart-Heating-Raum mit Name, Zustand
und Verfügbarkeit verwaltet. Die gespeicherte Smart-Heating-Raum-ID wird von
der aktuellen HA-Bereichszuordnung getrennt ausgewertet, sodass Zuordnungen nach
Reload korrekt im Zielraum erscheinen. Mehrere Kontakte, Suche, Verschieben,
Entfernen und ignorierte Kontakte werden unterstützt; HA-Bereiche und originale
Sensoren bleiben unverändert. Die zentrale Kontaktliste zeigt nur noch
ungeklärte, nicht verfügbare oder fehlerhafte Kontakte sowie die kompakte Liste
ignorierter Sensoren.

Die Lovelace-Karte ist nicht Bestandteil dieser Phase.

## Beta-25-Installationshinweis

Beta 25 wird als Vorabversion über HACS veröffentlicht. Die produktive
Installation bleibt im passiven Kompatibilitätsmodus; eine echte iPhone-
Abnahme erfolgt separat durch den Betreiber. Die neue Lovelace-Karte ist nicht
Bestandteil dieser Phase.

## Beta-24-iPhone-Abnahme

Die Verwaltung ist für schmale iPhone-Ansichten gehärtet: Zeitfelder werden
bei Bedarf untereinander dargestellt, deutsche Begriffe umbrechen nicht mitten
im Wort, und der Wochenplan meldet ungespeicherte beziehungsweise gespeicherte
Änderungen ausdrücklich. Raum-/Klimazonen-Zuordnungen zeigen gespeicherte Werte
und übernehmen neue Auswahl erst nach dem Speichern.

Fensterkontakte zeigen Raum, Zustand und Eignung getrennt. `unknown` und
`unavailable` werden als **unbekannt** beziehungsweise **nicht verfügbar**
angezeigt; ignorierte Sensoren bleiben separat einklappbar. Sondermodi trennen
Verfügbarkeit, Aktivität und Statusquelle. Alle Funktionen bleiben passiv.

## Beta-23-UX-Abnahme

Die Versionsanzeige verwendet die vom Backend-WebSocket gelieferte zentrale
Integrationsversion. Frontend-Fallbacks zeigen keine erfundene Release-Version
mehr an; dadurch werden veraltete JavaScript-Caches sichtbar statt als aktuelle
Version ausgegeben. Die mobile Verwaltung gruppiert Geräte zuerst nach dem
aktuellen HA-Bereich, bietet geeignete Geräte anderer Bereiche danach an und
trennt Raum-, Kontakt-, Außen- und technische Temperaturquellen. Wochenplan,
Fensterkontakte, ignorierte Sensoren, Personen und Sondermodi bleiben passiv;
bestehende Zuordnungen werden nicht automatisch verändert.

## Beta-23-Verwaltungsoberfläche

Die Verwaltungsoberfläche bietet eine kompakte, mobile Wochenplanbearbeitung
mit nativen Zeitfeldern, nicht überlappenden Komfortfenstern, Tageskopie und
sichtbarer Speicher-/Validierungsrückmeldung. Raumthermostate und geeignete
Raumtemperaturfühler werden zuerst aus dem HA-Bereich und zusätzlich aus
„Weitere geeignete Geräte“ angeboten; Geräte ohne HA-Bereich bleiben damit
manuell auswählbar. Technische Temperaturquellen werden nicht als Raumfühler
vorgeschlagen, und gespeicherte, aktuell nicht verfügbare Zuordnungen werden
zur Prüfung erhalten.

Die HA-Bereichsrelevanz ist von der Aktivierung eines Smart-Heating-Raums
getrennt. Die Oberfläche verändert keine HA-Bereiche und bleibt im passiven
Kompatibilitätsmodus.

## Verbindliche Begriffe und Oberflächen

- **Frontend – Lovelace-Karte:** Heizungsstatus, Visualisierung und passive Wochenplanvorschau.
- **Verwaltungsoberfläche – Smart Heating im HA-Seitenmenü:** Wochenpläne, Klimazonen, Räume, Temperaturfühler, Fensterkontakte, Personen und beobachtbare Steuerungssignale.
- **Integrationskonfiguration – HA-Optionsdialog:** technische Optionen wie Betriebsmodus, Sommerstrategie sowie Schornsteinfeger- und Frostschutzwerte.
- **Smart Heating Integration:** technische Home-Assistant-Integration.
- **Smart Heating Verwaltung:** eigenständige Oberfläche im HA-Seitenmenü.
- **Smart Heating Einstellungen:** nativer Home-Assistant-Optionsdialog.
- **Smart Heating Dashboard-Karte:** Lovelace-Frontend zur Anzeige und späteren Bedienung.

Im Optionsdialog ist **Nur beobachten (aktuell)** voreingestellt. Smart Heating berechnet Heizbedarf und Empfehlungen, ohne Thermostate, Automationen oder andere Geräte zu verändern. **Heizung aktiv steuern** ist noch nicht verfügbar und serverseitig gesperrt. Die Sommerstrategie ist davon getrennt und schaltet im Beobachtungsmodus keine Thermostate aus.

**Smart Heating** ist eine HACS-kompatible Home-Assistant-Integration für
Wochenzeitpläne, Status, Simulation und eine kompakte Lovelace-Karte.

> **Beta-11-Sicherheitsgrenze:** Die Integration berechnet die vollständige
> Heizungsentscheidung passiv. Sie schaltet
> keine Climate-Entity, keinen bestehenden Helper, keinen Scheduler und keinen
> Sondermodus. Eine Migration in eine produktive Heizungssteuerung ist nicht
> enthalten.

> **Phase-26-Sicherheitsgrenze (01.11.2026):** Beta 19 ist ausschließlich im
> Entwicklungsrepository veröffentlicht und wird nicht automatisch auf VM 104
> installiert. Die produktive Instanz wurde nur lesend untersucht; beide
> vorhandenen Config Entries bleiben unverändert.

## Beta-19-Verwaltung und Klimazonen

Beta 19 führt die eigenständige, passive Smart Heating Verwaltung für Personen,
Klimazonen, Thermostate, Fenster-/Kippkontakte, Raumtemperaturfühler,
Außentemperatur und einen zentralen Controller. Änderungen werden über
Config-Entry-Optionen beziehungsweise die unterstützte WebSocket-API
gespeichert; Home-Assistant-Entities werden niemals angelegt oder gelöscht.
Personen stammen ausschließlich aus `person.*`. Unbekannte Anwesenheit wird
nicht als Abwesenheit interpretiert. Ein Thermostat darf nicht zwei aktiven
Zonen zugeordnet sein. Die Verwaltungsbereiche sind unabhängig aufklappbar; HA-Bereiche werden nur gelesen, getrennt dargestellt und erst nach ausdrücklicher interner Auswahl als heizungsrelevant geführt.

## Funktionen

- UI-basierter Config Flow und Options Flow
- persistenter Wochenplan in der Config Entry
- mehrere nicht überlappende Fenster pro Wochentag
- serverseitige Zeitberechnung und `next_switch`
- Simulation der dokumentierten Prioritätsreihenfolge
- read-only Diagnose und Migration-Preview
- kompakte responsive Lovelace-Karte mit eigener, validierter Planverwaltung
- deutsche und englische Übersetzungen
- vorsichtige automatische Entity-Erkennung mit sichtbaren Mehrdeutigkeiten und Klassifikation technischer Temperaturquellen
- Migrationsplan mit Single-Writer-Sperre, Bestätigungstoken, Snapshot,
  Read-back und isoliertem Rollback-Adapter
- erklärbare Entscheidung mit aktivem Modus, Grund, Zieltemperatur und HVAC-Ziel
- getrennter Kompatibilitäts- und Vollmodus
- isolierter Climate-Servicepfad mit Primär-/Tado-Fallback, Read-back und Rollback
- Kompatibilitäts-Sommermodus sowie ausdrücklich gesperrter HVAC-Off-Planung
- isolierter Home-Assistant-Lifecycle-Test für Flow, Entities und Neustart
- explizite Entity-Zuordnung im Options Flow mit persistenter Rückwärtskompatibilität
- unbekannte Fensterzustände werden in der Vorschau als unbekannt statt geschlossen gezeigt
- eigener persistenter interner Betriebszustand mit nativen Switch-/Select-/Number-/Sensor-Entitäten
- eigener passiver Wochenplaner; Simple Scheduler und manuell angelegte Helfer sind für Smart Heating nicht erforderlich
- grafischer Wochenplan mit sieben Tagen, mehreren Zeitfenstern und optionalen Zieltemperaturen
- nativer Options-Dialog mit verständlichen Betriebs-/Sicherheitsfeldern statt YAML-Objekteditor

## Branding

Die eigenständigen Branding-Dateien liegen unter [`brand/`](brand/):
quadratische Marke ohne Schriftzug als SVG/PNG, transparente Variante und
GitHub-Banner. Sie greifen Haus, Thermometer, Wärme, Blau und Orange der
Designvorlage auf. Die Grafiken sind Projekt-Assets; eine offizielle
Marketplace- oder HACS-Branding-Aufnahme wird hier nicht behauptet.

## Oberflächen

Die normale Lovelace-Karte enthält ausschließlich Heizstatus, Sondermodi und
Wochenzeitplan. Die technische Verwaltung ist davon getrennt und wird als
eigenständiges Home-Assistant-Seitenmenü **Smart Heating** geöffnet. Sie enthält
die sieben geschlossenen Bereiche Räume & Klimazonen, Fenster & Kippsensoren,
Personen & Anwesenheit, Außentemperatur, Heizungscontroller, Sondermodi &
Sicherheit sowie Diagnose & Migration. Die gerenderten Oberflächen wurden in
den UI-Fixtures auf Desktop, iPhone, iPad und engem Touchmonitor geprüft:

![Smart Heating Desktop](docs/screenshots/smart-heating-card-desktop.png)
![Smart Heating iPhone](docs/screenshots/smart-heating-card-iphone.png)

Das Panel gruppiert Fensterkontakte nach HA-Räumen und bietet Suche sowie
Statusfilter. Automatisch erkannt werden ausschließlich `binary_sensor`-
Entities mit `window`, `door` oder `opening`; Batterie-, Diagnose-,
Temperatur- und andere Neben-Entities werden ausgeschlossen. Bestehende
ungeeignete Zuordnungen bleiben erhalten und werden nur zur manuellen Prüfung
markiert.

Der native Options-Dialog enthält bewusst nur die vier sicheren Betriebs- und
Sicherheitswerte. Der Wochenplan wird im Panel grafisch bearbeitet; dadurch
bleiben bestehende Zeitfenster und optionale Zieltemperaturen beim Speichern
anderer Optionen vollständig erhalten.

## Installation

Beta 19 ist ein GitHub-Prerelease. In HACS muss die Vorabversion explizit
aktiviert werden. Danach über **HACS → Integrationen → Smart Heating**
installieren. Ein erforderlicher Home-Assistant-Neustart ist separat zu
prüfen und darf erst nach Freigabe durchgeführt werden.

Alternativ kann das Repository als benutzerdefiniertes HACS-Repository
(`Integration`) hinzugefügt werden. Die Integration darf zunächst nur in einer
Testinstanz installiert werden.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Smart
   Heating**.
2. Nur Name und Zeitzone festlegen. Legacy-Helper erscheinen nicht im initialen Flow.
3. Erkannte Vorschläge auf der Bestätigungsseite prüfen und ausdrücklich bestätigen.
4. Im Seitenmenü **Smart Heating** die technische Verwaltung öffnen. Alle sieben
   Bereiche sind zunächst geschlossen und unabhängig aufklappbar; Räume und
   Zonen sind zusätzlich einzeln aufklappbar. Die Lovelace-Karte bleibt davon
   getrennt und enthält keine technische Geräteverwaltung.
5. Die Karte mit `entry_id` der Config Entry in ein Testdashboard aufnehmen:

```yaml
type: custom:smart-heating-card
entry_id: YOUR_CONFIG_ENTRY_ID
```

Die Karte bearbeitet ausschließlich den Zeitplan dieser Smart-Heating-Entry.
Sie schreibt keine bestehenden Heizungs-Entities.

### Beta-19-Smart-Heating-Verwaltung

Das Seitenpanel zeigt den Wochenplan als kompakte Tagesübersicht. Nur der
ausgewählte Tag wird bearbeitet; Fenster können mit optionaler Zieltemperatur
hinzugefügt, geändert und entfernt werden. Speichern erfolgt ausdrücklich und
meldet Erfolg oder Validierungsfehler sichtbar zurück. Die sieben
Verwaltungsbereiche bleiben unabhängig aufklappbar und zeigen Leerzustände.

### Beta-12-Installationsassistent

Die Migrations-Preview zeigt erkannte Entities und Konflikte. Der
Kompatibilitätsmodus ist der sichere Standard: Smart Heating beobachtet den
Zeitplan und lässt die bestehende Automation am Thermostat schreiben. Wenn
Simple Scheduler keinen unterstützten Export bereitstellt, verlangt die UI
einen validierten manuellen Vorschlag. Der Vollmodus bleibt gesperrt, bis ein
einzelner Schreiber in einer ausdrücklich isolierten Umgebung nachgewiesen ist.

Der Schornsteinfeger-Modus hat in der Entscheidungsansicht absolute Priorität.
Ein Sollwert oder `hvac_action` beweist jedoch keinen Brennerstart.

Der Options Flow kann die eindeutigen Zuordnungen der Bestandsanlage nachträglich
speichern: Primär-Climate, Tado-Fallback, Zeitstatus, Heizfreigabe, Sollwerte,
Außentemperatur, Fenster, Anwesenheit und Sondermodi. Vorschläge werden erst
nach ausdrücklicher Bestätigung gespeichert; Mehrdeutigkeiten bleiben offen.
Fenster werden auf geeignete `binary_sensor`-Entities mit Öffnungs-Device-Class
beschränkt. Personen stammen ausschließlich aus `person.*`; Tracker, Batterie-,
Temperatur-, Diagnose- und Fahrzeug-Entities werden ausgeschlossen. Unbekannte
Fensterzustände werden nicht als geschlossen bewertet.

## Referenzmigration

Die Referenzanlage nutzt `input_boolean.heizung` als Zeit-/Kalenderstatus und
hat Sondermodi mit einer dokumentierten Priorität. Die ursprünglichen Simple-
Scheduler-Zeitpläne werden als **unverifizierte Importquelle** behandelt, bis
ein unterstützter Export vorliegt:

- Montag–Freitag Heizbeginn 05:30
- Samstag–Sonntag Heizbeginn 07:00
- Sonntag–Donnerstag Absenkung 21:00
- Freitag–Samstag Absenkung 22:00

Beta 13 übernimmt diese Werte nicht automatisch und schreibt `input_boolean.heizung`
nicht. Die Migrations-Preview zeigt nur einen Konflikt-/Prüfstatus. Der
ausführbare Adapter akzeptiert Schreibzugriffe ausschließlich über einen
isolierten Test-Transport; die Produktiv-Sperre verweigert die Aktivierung,
solange der alte Schreiber nicht nachweisbar abgelöst ist.

## Entscheidungslogik

Die Referenzreihenfolge ist unverändert: Schornsteinfeger → fehlende
Heizfreigabe → Fenster offen → Fenster gekippt → Abwesenheit → Nacht/Party →
Sommermodus ohne Komfortoverride → Komfort. Die Karte trennt Zeitplanstatus,
berechneten Heizmodus und tatsächliche Produktivsteuerung. Die Beta führt keine
Climate- oder Helper-Services aus. Smart Heating verwaltet seinen eigenen
Zustand und Wochenplan persistent in der Config Entry und stellt dafür native
HA-Entitäten bereit; Simple Scheduler und manuell angelegte Helper sind daher
für den Integrationsbetrieb nicht erforderlich. Im Kompatibilitätsmodus bleibt
die Heizungs- und Controller-Steuerung gesperrt.

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
Teil der Beta-11-Entwicklung. Der Kompatibilitätsmodus ist passiv; der Vollmodus
bleibt bis zu einem gesondert geprüften Single-Writer-Nachweis gesperrt.

## Status

Version: `0.1.0-beta.34`
Release-Typ: Entwicklungsrelease / HACS-Prerelease  
Produktive Migration: gesperrt; nur isolierter Adapter-Test möglich

Weitere Architektur- und Sicherheitsdetails stehen in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
