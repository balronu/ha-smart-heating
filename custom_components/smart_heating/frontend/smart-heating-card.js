/* Smart Heating Beta 7: rendered, touch-friendly passive schedule editor. */
const SMART_HEATING_CARD_VERSION = "0.1.0-beta.7";
class SmartHeatingCard extends HTMLElement {
  static getConfigElement() { return document.createElement("smart-heating-card-editor"); }
  static getStubConfig() { return { entry_id: "" }; }
  setConfig(config) { if (!config || !config.entry_id) throw new Error("Smart Heating needs entry_id"); this._config = config; this._render(); this._load(); }
  set hass(hass) { this._hass = hass; if (this._config && !this._loaded) this._load(); this._render(); }
  getCardSize() { return 5; }
  getGridOptions() { return { columns: 12, rows: "auto", min_rows: 3 }; }
  async _load() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try { this._data = await this._hass.callWS({ type: "smart_heating/plan/get", entry_id: this._config.entry_id }); this._loaded = true; this._error = null; }
    catch (error) { this._error = error.message || String(error); }
    finally { this._loading = false; this._render(); }
  }
  _esc(value) { return String(value ?? "").replace(/[&<>\"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char])); }
  _render() {
    if (!this._config) return;
    const schedule = this._data?.schedule || {}, status = this._data?.status || {};
    const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
    const labels = { monday: "Montag", tuesday: "Dienstag", wednesday: "Mittwoch", thursday: "Donnerstag", friday: "Freitag", saturday: "Samstag", sunday: "Sonntag" };
    const specials = Object.entries(status.special_modes || {});
    const observed = status.observed || {};
    const windowStatus = observed.window_status || "unknown";
    const windowLabel = { unknown: "unbekannt", open_or_tilted: "offen/gekippt", closed_or_clear: "geschlossen" }[windowStatus] || "unbekannt";
    const outdoor = observed.outdoor_temperature?.state || "unbekannt";
    const heatDemand = observed.heat_demand_status || status.heat_demand_status || "unbekannt";
    const operationMode = this._data?.options?.operation_mode || status.operation_mode || "compatibility";
    const controlPlane = this._data?.options?.control_plane || {};
    const conflict = controlPlane.activation_allowed === false && operationMode === "full" ? "Aktivierung gesperrt: alter Schreibpfad nicht beweisbar" : "";
    const specialMarkup = specials.length ? specials.map(([key, value]) => `<button class="special" data-special="${this._esc(key)}" aria-pressed="${Boolean(value)}" disabled>${this._esc(key)}: ${value ? "an" : "aus"}</button>`).join("") : "<span>Keine Sondermodus-Zuordnung</span>";
    this.innerHTML = `<ha-card><div class="wrap"><header><strong>${this._esc(this._config.title || "Smart Heating")}</strong><span class="badge">Beta 7 · ${this._esc(status.mode || "—")}</span></header>${this._error ? `<p class="error" role="alert" data-testid="error">${this._esc(this._error)}</p>` : ""}${conflict ? `<p class="error" role="alert">${conflict}</p>` : ""}<p class="status" data-testid="status">Betriebsart: <b>${this._esc(operationMode)}</b> · Zeitplan: <b>${status.schedule_active ? "aktiv" : "inaktiv"}</b> · Entscheidungsmodus: <b>${this._esc(status.actual_mode || "—")}</b> · Nächste Umschaltung: ${this._esc(status.next_switch || "—")}</p><p class="status" data-testid="observed">Tatsächlicher Climate-Status: <b>${this._esc(observed.climate?.state || "unbekannt")}</b> · Wärmeanforderung: <b>${this._esc(heatDemand)}</b> · Fenster: <b>${this._esc(windowLabel)}</b> · Außen: <b>${this._esc(outdoor)} °C</b></p><p class="status">Vorschauziel: <b>${this._esc(status.target_temperature ?? "—")} °C</b> · Vorschau-HVAC: <b>${this._esc(status.target_hvac_mode || "—")}</b> · Steuerung: <b>${this._esc(status.control_state || "locked")}</b> · Grund: ${this._esc(status.reason || "—")}</p><div class="specials" aria-label="Sondermodi">${specialMarkup}</div><div class="days">${days.map(day => this._day(day, labels[day], schedule[day] || [])).join("")}</div><p class="hint">Zeitplanstatus ist nicht gleich tatsächlicher Heizungsbetrieb. Unbekannte Fensterzustände werden nicht als geschlossen bewertet. Im Kompatibilitätsmodus bleibt die bestehende Automation zuständig. Sondermodi werden hier nur angezeigt; ein Sollwert beweist keinen Brennerstart.</p></div></ha-card>`;
    this._style();
    this.querySelectorAll("button[data-add]").forEach(button => button.addEventListener("click", () => this._add(button.dataset.add)));
    this.querySelectorAll("button[data-remove]").forEach(button => button.addEventListener("click", () => this._remove(button.dataset.remove, Number(button.dataset.index))));
    this.querySelectorAll("button[data-copy]").forEach(button => button.addEventListener("click", () => this._copy(button.dataset.copy, this.querySelector(`select[data-copy-target='${button.dataset.copy}']`)?.value)));
    this.querySelectorAll("input[data-time]").forEach(input => input.addEventListener("change", () => this._edit(input.dataset.day, Number(input.dataset.index), input.dataset.part, input.value)));
  }
  _day(day, label, windows) {
    const rows = windows.map((window, index) => `<div class="window"><input aria-label="${label} Startzeit ${index + 1}" data-time data-day="${day}" data-index="${index}" data-part="start" type="time" value="${this._esc(window.start.slice(0, 5))}"><span aria-hidden="true">–</span><input aria-label="${label} Endzeit ${index + 1}" data-time data-day="${day}" data-index="${index}" data-part="end" type="time" value="${this._esc(window.end.slice(0, 5))}"><button aria-label="${label} entfernen" data-remove="${day}" data-index="${index}">×</button></div>`).join("");
    const options = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].map(target => `<option value="${target}">${target}</option>`).join("");
    return `<section data-day="${day}"><h3>${label}</h3><div class="windows">${rows || "<em>Keine Heizzeit</em>"}</div><div class="actions"><button data-add="${day}">+ Zeit</button><select aria-label="Zieltag für Kopie" data-copy-target="${day}">${options}</select><button data-copy="${day}">Tag kopieren</button></div></section>`;
  }
  async _add(day) { const schedule = structuredClone(this._data?.schedule || {}); schedule[day] = [...(schedule[day] || []), { start: "06:00", end: "09:00" }]; await this._save(schedule); }
  async _edit(day, index, part, value) { const schedule = structuredClone(this._data?.schedule || {}); schedule[day][index][part] = value; await this._save(schedule); }
  async _remove(day, index) { const schedule = structuredClone(this._data?.schedule || {}); schedule[day].splice(index, 1); await this._save(schedule); }
  async _copy(day, target) { if (!target || target === day) return; const schedule = structuredClone(this._data?.schedule || {}); schedule[target] = structuredClone(schedule[day] || []); await this._save(schedule); }
  async _save(schedule) { try { this._data = await this._hass.callWS({ type: "smart_heating/plan/set", entry_id: this._config.entry_id, schedule }); this._error = null; } catch (error) { this._error = error.message || String(error); } this._render(); }
  _style() { const style = document.createElement("style"); style.textContent = ".wrap{padding:16px}header{display:flex;justify-content:space-between;gap:8px;font-size:1.05rem}.badge{font-size:.8rem;color:var(--secondary-text-color)}.status,.hint{font-size:.82rem;color:var(--secondary-text-color)}.days{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px;align-items:start}.days section{min-width:0;min-height:150px;border:1px solid var(--divider-color);border-radius:12px;padding:8px;box-sizing:border-box}.days h3{font-size:.9rem;margin:0 0 6px}.windows{display:grid;gap:5px;min-height:28px}.window{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr) auto;align-items:center;gap:4px;min-width:0}.window button{border:0;background:none;color:var(--error-color);font-size:1.2rem}.window input,.actions select,.actions button{font:inherit;min-height:34px}.window input{width:100%;box-sizing:border-box}.actions{display:flex;gap:4px;flex-wrap:wrap;margin-top:8px}.actions button,.actions select{font-size:.78rem;padding:5px 7px;border:1px solid var(--divider-color);border-radius:8px;background:var(--secondary-background-color);color:var(--primary-text-color)}.specials{display:flex;gap:5px;flex-wrap:wrap;margin:8px 0}.special{font:inherit;font-size:.78rem;padding:5px 7px;border:1px solid var(--divider-color);border-radius:8px;background:var(--secondary-background-color);color:var(--secondary-text-color)}.error{color:var(--error-color)}em{color:var(--secondary-text-color);font-size:.8rem}@media(max-width:520px){.wrap{padding:12px}.days{grid-template-columns:1fr}.window input{min-width:0}}"; this.appendChild(style); }
}
class SmartHeatingCardEditor extends HTMLElement { setConfig(config) { this._config = { ...config }; this._render(); } _render() { this.innerHTML = `<div style="display:grid;gap:8px"><label>Smart Heating Config Entry ID<input data-entry value="${this._config?.entry_id || ""}" /></label><label>Titel (optional)<input data-title value="${this._config?.title || ""}" /></label></div>`; this.querySelectorAll("input").forEach(input => input.addEventListener("change", () => { const config = { ...this._config, entry_id: this.querySelector("[data-entry]").value.trim() }; const title = this.querySelector("[data-title]").value.trim(); if (title) config.title = title; else delete config.title; this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true })); })); } }
if (!customElements.get("smart-heating-card-editor")) customElements.define("smart-heating-card-editor", SmartHeatingCardEditor);
if (!customElements.get("smart-heating-card")) customElements.define("smart-heating-card", SmartHeatingCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "smart-heating-card")) window.customCards.push({ type: "smart-heating-card", name: "Smart Heating", description: "Weekly Smart Heating schedule and status", preview: true });
