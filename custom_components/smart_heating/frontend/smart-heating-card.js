/* Smart Heating Beta 1: passive schedule editor for the integration's own store. */
class SmartHeatingCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entry_id) throw new Error("Smart Heating needs entry_id");
    this._config = config;
    this._render();
    this._load();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config && !this._loaded) this._load();
    this._render();
  }

  getCardSize() { return 5; }
  getGridOptions() { return { columns: 12, rows: "auto", min_rows: 3 }; }

  async _load() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try {
      this._data = await this._hass.callWS({ type: "smart_heating/plan/get", entry_id: this._config.entry_id });
      this._loaded = true;
    } catch (error) {
      this._error = error.message || String(error);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _render() {
    if (!this._config) return;
    const schedule = this._data?.schedule || {};
    const status = this._data?.status || {};
    const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
    const labels = { monday: "Montag", tuesday: "Dienstag", wednesday: "Mittwoch", thursday: "Donnerstag", friday: "Freitag", saturday: "Samstag", sunday: "Sonntag" };
    this.innerHTML = `<ha-card><div class="wrap"><header><strong>${this._config.title || "Smart Heating"}</strong><span class="badge">${status.mode || "—"}</span></header>${this._error ? `<p class="error">${this._error}</p>` : ""}<p class="status">Zeitplan: <b>${status.schedule_active ? "aktiv" : "inaktiv"}</b> · Nächste Umschaltung: ${status.next_switch || "—"}</p><div class="days">${days.map(day => this._day(day, labels[day], schedule[day] || [])).join("")}</div><p class="hint">Zeitplanstatus ist nicht gleich tatsächlicher Heizbetrieb. Freigabe, Fenster, Anwesenheit und Sondermodi bleiben außerhalb dieser Karte.</p></div></ha-card>`;
    this._style();
    this.querySelectorAll("button[data-add]").forEach(button => button.addEventListener("click", () => this._add(button.dataset.add)));
    this.querySelectorAll("button[data-remove]").forEach(button => button.addEventListener("click", () => this._remove(button.dataset.remove, Number(button.dataset.index))));
    this.querySelectorAll("button[data-copy]").forEach(button => button.addEventListener("click", () => this._copy(button.dataset.copy)));
  }

  _day(day, label, windows) {
    const rows = windows.map((window, index) => `<span>${window.start.slice(0, 5)}–${window.end.slice(0, 5)}</span><button aria-label="${label} entfernen" data-remove="${day}" data-index="${index}">×</button>`).join("");
    return `<section><h3>${label}</h3><div class="windows">${rows || "<em>keine</em>"}</div><div class="actions"><button data-add="${day}">+ Zeit</button><button data-copy="${day}">Tag kopieren</button></div></section>`;
  }

  async _add(day) {
    const start = prompt("Startzeit (HH:MM)", "06:00");
    const end = prompt("Endzeit (HH:MM)", "09:00");
    if (!start || !end) return;
    const schedule = structuredClone(this._data.schedule || {});
    schedule[day] = [...(schedule[day] || []), { start, end }];
    await this._save(schedule);
  }

  async _remove(day, index) {
    const schedule = structuredClone(this._data.schedule || {});
    schedule[day].splice(index, 1);
    await this._save(schedule);
  }

  async _copy(day) {
    const target = prompt(`Zieltag für ${day} (monday…sunday)`);
    if (!target || !this._data.schedule[target]) return;
    const schedule = structuredClone(this._data.schedule || {});
    schedule[target] = structuredClone(schedule[day] || []);
    await this._save(schedule);
  }

  async _save(schedule) {
    try {
      this._data = await this._hass.callWS({ type: "smart_heating/plan/set", entry_id: this._config.entry_id, schedule });
      this._error = null;
    } catch (error) { this._error = error.message || String(error); }
    this._render();
  }

  _style() {
    if (this.querySelector("style")) return;
    const style = document.createElement("style");
    style.textContent = ".wrap{padding:16px}header{display:flex;justify-content:space-between;gap:8px;font-size:1.05rem}.badge{font-size:.8rem;color:var(--secondary-text-color)}.status,.hint{font-size:.82rem;color:var(--secondary-text-color)}.days{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px}.days section{border:1px solid var(--divider-color);border-radius:12px;padding:8px}.days h3{font-size:.9rem;margin:0 0 6px}.windows{display:grid;grid-template-columns:1fr auto;gap:4px;min-height:24px}.windows button{border:0;background:none;color:var(--error-color);font-size:1rem}.actions{display:flex;gap:4px;margin-top:8px}.actions button{font:inherit;font-size:.78rem;padding:5px 7px;border:1px solid var(--divider-color);border-radius:8px;background:var(--secondary-background-color);color:var(--primary-text-color)}.error{color:var(--error-color)}em{color:var(--secondary-text-color);font-size:.8rem}@media(max-width:520px){.wrap{padding:12px}.days{grid-template-columns:1fr}}";
    this.appendChild(style);
  }
}

if (!customElements.get("smart-heating-card")) customElements.define("smart-heating-card", SmartHeatingCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "smart-heating-card")) window.customCards.push({ type: "smart-heating-card", name: "Smart Heating", description: "Weekly Smart Heating schedule and status" });

