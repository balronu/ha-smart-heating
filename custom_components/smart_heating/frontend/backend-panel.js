const VERSION = "0.1.0-beta.13";
class SmartHeatingBackendPanel extends HTMLElement {
  set hass(value) {
    this._hass = value;
    if (!this._loaded) this._load();
  }

  async _load() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try {
      const response = await this._hass.callWS({ type: "config_entries/get" });
      const candidates = [response, response?.result, response?.data, response?.result?.entries, response?.data?.entries];
      const entries = candidates.find((value) => Array.isArray(value)) || (Array.isArray(response?.entries) ? response.entries : []);
      const active = entries.filter((item) => item && item.domain === "smart_heating" && !item.disabled_by);
      if (active.length === 0) throw new Error("Keine Smart-Heating-Konfiguration gefunden. Bitte zuerst die Integration unter Einstellungen → Geräte & Dienste einrichten.");
      if (active.length > 1) throw new Error(`Mehrere Smart-Heating-Konfigurationen gefunden (${active.map((item) => item.entry_id).join(", ")}). Keine Instanz wurde automatisch ausgewählt; bitte die Duplikatprüfung/Migration durchführen.`);
      const entry = active[0];
      this._entryId = entry.entry_id;
      this._data = await this._hass.callWS({ type: "smart_heating/admin/get", entry_id: this._entryId });
      this._loaded = true;
      this._error = null;
    } catch (error) {
      this._error = error.message || String(error);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _esc(value) {
    return String(value ?? "").replace(/[&<>\"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  }

  _entityOptions(items, selected = []) {
    const values = new Set(selected || []);
    return (items || []).map((item) => `<option value="${this._esc(item.entity_id)}" ${values.has(item.entity_id) ? "selected" : ""}>${this._esc(item.name || item.entity_id)} (${this._esc(item.entity_id)})</option>`).join("");
  }

  _render() {
    if (!this._hass) return;
    const openSections = [...this.querySelectorAll("details[data-section], details[data-room], details[data-zone]")].filter((node) => node.open).map((node) => node.dataset.section || node.dataset.room || node.dataset.zone);
    const management = this._data?.management || { zones: [], persons: [], sensors: {}, controller: {}, outdoor_temperature: {} };
    const areas = this._data?.areas || [];
    const persons = this._data?.persons_discovered || [];
    const areaEntities = areas.flatMap((area) => (area.entity_ids || []).map((entity_id) => ({ entity_id, name: entity_id }))) ;
    const climates = areaEntities.filter((item) => item.entity_id.startsWith("climate."));
    const temperatures = areaEntities.filter((item) => item.entity_id.startsWith("sensor."));
    const windows = areaEntities.filter((item) => item.entity_id.startsWith("binary_sensor.") && /fenster|window|opening|kontakt|kippen/i.test(`${item.name} ${item.entity_id}`));
    const zoneCards = (management.zones || []).map((zone) => `<details data-zone="zone-${this._esc(zone.id)}"><summary>${this._esc(zone.name || "Klimazone")} · ${zone.enabled === false ? "deaktiviert" : "aktiv"}</summary><p>Räume: ${(zone.area_ids || []).length || "keine"} · Thermostate: ${(zone.thermostat_entities || []).length || "keine"}</p><button data-zone-delete="${this._esc(zone.id)}">Zone entfernen</button></details>`).join("") || "<p class=hint>Keine Klimazone konfiguriert.</p>";
    const roomCards = areas.map((area) => `<details data-room="room-${this._esc(area.area_id)}"><summary>${this._esc(area.name)}</summary><p>Thermostate: ${this._esc((area.suggestions?.thermostat_entities || []).join(", ") || "keine")}</p><p>Temperaturfühler: ${this._esc((area.suggestions?.temperature_entities || []).join(", ") || "keine")}</p><p>Fensterkandidaten: ${this._esc((area.suggestions?.window_entities || []).join(", ") || "keine")}</p></details>`).join("") || "<p class=hint>Keine HA-Räume erkannt.</p>";
    const personRows = persons.map((person) => { const selected = (management.persons || []).some((item) => (item.presence_entities || []).includes(person.entity_id)); return `<li>${this._esc(person.name)} · ${this._esc(person.state)} ${selected ? "· berücksichtigt" : `<button data-person-add="${this._esc(person.entity_id)}" data-person-name="${this._esc(person.name)}">berücksichtigen</button>`}</li>`; }).join("") || "<li>Keine native person.*-Entity erkannt.</li>";
    const section = (id, title, body) => `<details data-section="${id}"><summary>${title}</summary><div class="section-body">${body}</div></details>`;
    const error = this._loading ? `<p class="hint" role="status">Smart Heating wird geladen …</p>` : this._error ? `<p class="error" role="alert">${this._esc(this._error)}</p>` : "";
    const version = this._data?.version || VERSION;
    this.innerHTML = `<main class="smart-heating-backend"><header><h1>Smart Heating</h1><p>Backend-Verwaltung · ${this._esc(version)} · passiver Kompatibilitätsmodus</p></header>${error}<p class="hint">Diese Verwaltungsoberfläche speichert technische Smart-Heating-Zuordnungen in der Config Entry. Home-Assistant-Räume, Geräte, Personen und Tracker werden nicht verändert.</p>${section("rooms", "Räume &amp; Klimazonen", `<div class="rooms">${roomCards}</div><h2>Klimazonen</h2>${zoneCards}<form data-zone-form><label>Name<input name=name required></label><label>Räume<select name=area_ids multiple>${areas.map((area) => `<option value="${this._esc(area.area_id)}">${this._esc(area.name)}</option>`).join("")}</select></label><label>Thermostate<select name=thermostat_entities multiple>${this._entityOptions(climates)}</select></label><label>Temperaturfühler<select name=temperature_entities multiple>${this._entityOptions(temperatures)}</select></label><button>Zone speichern</button></form>`)}${section("windows", "Fenster &amp; Kippsensoren", `<p>Nur als Fenster markierte Binary-Sensoren werden als Vorschläge angezeigt; unbekannte Zustände bleiben unbekannt.</p><form data-sensor-form><label>Fensterkontakt<select name=entity_id>${this._entityOptions(windows)}</select></label><label>Art<select name=state_semantics><option value=open>Offen</option><option value=tilt>Gekippt</option><option value=open_or_tilted>Offen und gekippt</option></select></label><button>Sensor speichern</button></form>`)}${section("persons", "Personen &amp; Anwesenheit", `<ul>${personRows}</ul><p class=hint>Es werden ausschließlich native person.*-Entities verwendet.</p>`)}${section("outdoor", "Außentemperatur", `<form data-outdoor-form><label>Temperaturquelle<select name=entity_id>${this._entityOptions(temperatures, management.outdoor_temperature?.entity_id ? [management.outdoor_temperature.entity_id] : [])}</select></label><button>Quelle speichern</button></form>`)}${section("controller", "Heizungscontroller", `<form data-controller-form><label>Controller<select name=entity_id>${this._entityOptions(climates, management.controller?.entity_id ? [management.controller.entity_id] : [])}</select></label><button>Controller speichern</button></form>`)}${section("safety", "Sondermodi &amp; Sicherheit", `<p>Schornsteinfeger bleibt in der Entscheidungslogik absolut priorisiert. Im passiven Modus werden keine Helper oder Thermostate geschaltet.</p>`)}${section("diagnostics", "Diagnose &amp; Migration", `<p>Config Entry: ${this._esc(this._entryId || "unbekannt")}</p><p>Validierung: ${this._data?.validation?.length ? this._esc(this._data.validation.join(", ")) : "keine Konflikte"}</p>`)}<style>${this._style()}</style></main>`;
    this.querySelectorAll("details[data-section], details[data-room], details[data-zone]").forEach((node) => { node.open = openSections.includes(node.dataset.section || node.dataset.room || node.dataset.zone); });
    this.querySelector("form[data-zone-form]")?.addEventListener("submit", (event) => { event.preventDefault(); const form = event.currentTarget; this._admin("smart_heating/admin/zone/set", { item: { name: form.name.value.trim(), area_ids: [...form.area_ids.selectedOptions].map((item) => item.value), thermostat_entities: [...form.thermostat_entities.selectedOptions].map((item) => item.value), temperature_entities: [...form.temperature_entities.selectedOptions].map((item) => item.value) } }); });
    this.querySelector("form[data-sensor-form]")?.addEventListener("submit", (event) => { event.preventDefault(); const form = event.currentTarget; this._admin("smart_heating/admin/sensor/set", { item: { type: form.state_semantics.value === "tilt" ? "tilt" : "window", entity_id: form.entity_id.value, state_semantics: form.state_semantics.value, zone_ids: [] } }); });
    this.querySelector("form[data-outdoor-form]")?.addEventListener("submit", (event) => { event.preventDefault(); this._admin("smart_heating/admin/outdoor/set", { item: { entity_id: event.currentTarget.entity_id.value } }); });
    this.querySelector("form[data-controller-form]")?.addEventListener("submit", (event) => { event.preventDefault(); this._admin("smart_heating/admin/controller/set", { item: { entity_id: event.currentTarget.entity_id.value } }); });
    this.querySelectorAll("button[data-zone-delete]").forEach((button) => button.addEventListener("click", () => this._admin("smart_heating/admin/zone/delete", { item_id: button.dataset.zoneDelete })));
    this.querySelectorAll("button[data-person-add]").forEach((button) => button.addEventListener("click", () => this._admin("smart_heating/admin/person/set", { item: { name: button.dataset.personName, presence_entities: [button.dataset.personAdd] } })));
  }

  async _admin(type, data) {
    try { await this._hass.callWS({ type, entry_id: this._entryId, ...data }); this._data = await this._hass.callWS({ type: "smart_heating/admin/get", entry_id: this._entryId }); this._error = null; } catch (error) { this._error = error.message || String(error); } this._render();
  }

  _style() { return ".smart-heating-backend{max-width:1100px;margin:0 auto;padding:24px;box-sizing:border-box}.smart-heating-backend details{border:1px solid var(--divider-color);border-radius:12px;margin:8px 0;padding:12px;background:var(--card-background-color)}.smart-heating-backend summary{cursor:pointer;font-size:1.05rem;font-weight:600}.section-body{padding:12px 0}.rooms details{margin:6px 0}.smart-heating-backend form{display:grid;gap:8px;margin-top:12px}.smart-heating-backend label{display:grid;gap:4px}.smart-heating-backend input,.smart-heating-backend select,.smart-heating-backend button{font:inherit;min-height:38px;padding:6px;border-radius:8px;border:1px solid var(--divider-color);background:var(--secondary-background-color);color:var(--primary-text-color)}.smart-heating-backend select[multiple]{min-height:90px}.smart-heating-backend button{cursor:pointer}.hint{color:var(--secondary-text-color)}.error{color:var(--error-color)}@media(max-width:600px){.smart-heating-backend{padding:12px}}"; }
}

if (!customElements.get("smart-heating-backend-panel")) customElements.define("smart-heating-backend-panel", SmartHeatingBackendPanel);
