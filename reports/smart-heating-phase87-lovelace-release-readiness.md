# Smart Heating – Phase 87: Lovelace-Integration und Release-Reife

## Status

**Lokal abgeschlossen, nicht veröffentlicht, nicht auf VM 104 installiert.**
Die Prüfung basiert auf dem Ausgangscommit `793587e12167de3e12c1316b4bffdba10791b493`.

## Registrierungs- und Ressourcenprüfung

- `custom_components/smart_heating/__init__.py` registriert den Frontend-
  Ordner über `StaticPathConfig("/smart_heating", ...)`.
- Die Karte wird über den öffentlichen HA-Pfad
  `frontend.add_extra_js_url(hass, "/smart_heating/smart-heating-card.js?v={VERSION}")`
  geladen. Die Ressource ist damit für eine HACS-Installation unter dem
  Integrationspfad vorbereitet; eine manuelle Lovelace-Ressource ist nicht
  erforderlich.
- `hass.data`-Guards verhindern doppelte statische, Panel- und WebSocket-
  Registrierung. `customElements.get(...)` und der `window.customCards`-
  Eintrag sind ebenfalls idempotent. Der Picker verwendet den korrekten
  Elementnamen ohne `custom:`; die eigentliche Lovelace-Konfiguration nutzt
  `custom:smart-heating-card`.
- Die statische Ressource nutzt jetzt `cache_headers=True`; die versionierte
  URL ist der Cache-Busting-Vertrag bei Updates.
- Mehrere Karteninstanzen bleiben unabhängig. Identische Instanzen teilen den
  laufenden read-only Request über einen HA-/Entry-Cache.

## Editor-Integration

Der native Karteneditor stellt darstellbare Konfiguration ohne YAML-
Voraussetzung bereit:

- ausführlich, kompakt oder individuell;
- Raumfilter nach ID/Name;
- Sortierung und Reihenfolge der Bereiche;
- sichtbare Bereiche;
- Ist-/Solltemperatur und Fensterstatus;
- kompakte Sondermodusdarstellung.

Änderungen werden unmittelbar als `config-changed` ausgegeben und können von
Lovelace persistiert werden. Der Editor besitzt keine Service- oder
Heizschnittstelle.

## Datenanbindung

Die Karte verwendet ausschließlich `smart_heating/plan/get` mit `entry_id`.
Es gibt keine Frontend-Berechnung von Heizentscheidungen, keine Schreib-
Endpunkte und keine dauerhafte Polling-Schleife. Beim Übergang auf ein neues
HA-Zustandsobjekt wird der read-only Datenabruf erneut ausgelöst; parallele
Karten für dieselbe Entry-ID werden dedupliziert. Fehler werden als sichtbarer
Kartenfehler dargestellt, unbekannte/unavailable Werte als unbekannt bzw.
nicht vorhanden.

## Sicherheitsnachweise

Die Kartenquelle enthält keinen Aufruf von `plan/set`, Thermostat-Services,
Sondermodus-Aktivierung, SMART-Umschaltung oder Legacy-Automationsänderung.
Die Fixture verweigert alle nicht-`plan/get`-Aufrufe. Die Karte zeigt den
passiven Kompatibilitäts-/LEGACY-Zustand und lässt die Steuerung bei der
bestehenden Heizungsautomatik.

## Testergebnisse

| Prüfung | Ergebnis |
|---|---:|
| Python-Tests in `.venv-beta2` | **108/108 bestanden** |
| Playwright vollständige Suite | **220/220 bestanden** |
| Geräteprojekte | Desktop, iPhone, iPad, Touchmonitor |
| JSON: HACS, Manifest, Strings, Übersetzungen | **bestanden** |
| Python `compileall` | **bestanden** |
| `git diff --check` | **bestanden** |
| Karteneditor, Picker-Vertrag, Mehrfachinstanzen, Live-Update, Passivität | **bestanden** |

Die Browserprüfung lief über die lokale Fixture-Umgebung, nicht über eine
produktive Home-Assistant-Instanz. Visuelle Screenshots wurden durch die
Playwright-Matrix auf allen vier Geräteprofilen erzeugt; horizontale
Überläufe wurden geprüft.

## HACS/Hassfest und bekannte Grenzen

- HACS- und Hassfest-Prüfungen sind in `.github/workflows/hacs.yml` und
  `.github/workflows/validate.yml` als CI-Gates vorhanden. Die ausführbaren
  lokalen Werkzeuge waren in dieser Umgebung nicht installiert; daher kein
  lokaler HACS-/Hassfest-PASS.
- Es wurde keine echte HACS-Installation, kein HA-Neustart und keine Prüfung
  der laufenden HA-Root-HTML auf VM 104 durchgeführt.
- Die Karte bleibt absichtlich passiv; spätere Bedienung ist nicht Teil dieser
  Phase.
- Die Ressourcen-/Picker-Verträge sind lokal und statisch nachgewiesen; eine
  echte Release-/Tag-/CI-Prüfung ist wegen der Vorgabe „kein Push, PR oder
  Release“ nicht Bestandteil dieser Phase.

## Änderungsumfang und Installation

Geändert wurden die Integrationsregistrierung, die passive Kartenlogik, der
Karteneditor, Frontend-Vertrags- und Playwright-Tests sowie README und
CHANGELOG. `tools/` blieb unverändert. VM 104, produktive Automationen,
Thermostate, Scheduler, Tokens und Berechtigungen blieben unverändert.

## Commit

Nach erfolgreicher Abschlussprüfung wird ein lokaler Phase-87-Commit erstellt.
Es erfolgt kein Push, kein PR und kein Release. Der exakte Commit wird im
Abschluss der lokalen Git-Historie ausgewiesen.
