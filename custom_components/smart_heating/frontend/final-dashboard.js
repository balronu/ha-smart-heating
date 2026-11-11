/* Final passive dashboard renderer. Loaded after smart-heating-card.js. */
(function () {
  const Card = customElements.get("smart-heating-card");
  if (!Card) { setTimeout(() => import("./final-dashboard.js"), 0); return; }
  Card.prototype._finalSetInternal = async function (values) {
    const entryId = this._config?.entry_id || this._data?.entry_id;
    if (!entryId || !this._hass?.callWS) return;
    try {
      const result = await this._hass.callWS({ type: "smart_heating/admin/internal/set", entry_id: entryId, item: values });
      if (result?.internal) this._data.options = { ...(this._data.options || {}), management: { ...(this._data.options?.management || {}), internal: result.internal } };
      this._error = null;
    } catch (error) { this._error = error?.message || String(error); }
    this._renderModern();
  };
  Card.prototype._finalNavigate = function (path) {
    if (this._hass?.navigate) this._hass.navigate(path);
    else this.dispatchEvent(new CustomEvent("location-changed", { detail: { path }, bubbles: true, composed: true }));
  };
  Card.prototype._renderModern = function () {
    if (!this._data && this._hass && !this._loading) this._load();
    const management = this._management(), internal = management.internal || {}, zones = this._rooms();
    const source = management.heating_sources || {}, state = id => id ? this._hass?.states?.[id] : null;
    const value = (value, fallback = "unbekannt") => this._unknown(value) ? fallback : String(value), esc = this._esc.bind(this);
    const climateId = source.primary_climate_entity || management.controller?.entity_id || this._data?.options?.climate_entity;
    const climate = state(climateId), operation = internal.operating_mode || "automatic", enabled = internal.enabled !== false && operation !== "off";
    const control = (id, label, active) => `<button type="button" class="sh-control ${active ? "active" : ""}" data-internal-mode="${id}" aria-pressed="${active}">${label}</button>`;
    const room = room => {
      const id = String(room.id || room.name || ""), settings = internal.zones?.[id] || {};
      const target = Number(settings.comfort_temperature ?? room.comfort_temperature ?? room.target_temperature);
      const tempId = (room.temperature_entities || room.temperatures || [])[0], thermostatId = (room.thermostat_entities || room.thermostats || [])[0];
      const thermostat = state(typeof thermostatId === "string" ? thermostatId : thermostatId?.entity_id);
      const irId = (room.infrared_climate_entities || room.infrared?.climate_entities || [])[0], ir = state(typeof irId === "string" ? irId : irId?.entity_id);
      const actual = value(state(typeof tempId === "string" ? tempId : tempId?.entity_id)?.state, "nicht verfügbar");
      return `<article class="sh-room"><header><h3>${esc(room.name || id || "Raum")}</h3><span>${esc(value(thermostat?.attributes?.hvac_action || thermostat?.state))}</span></header><div class="sh-room-facts"><span><b>Ist</b>${esc(actual)}${this._unknown(actual) ? "" : " °C"}</span><span><b>Raumziel</b>${Number.isFinite(target) ? `${target} °C` : "nicht festgelegt"}</span></div><div class="sh-room-control"><button type="button" data-room-target="${esc(id)}" data-delta="-0.5" aria-label="Raumziel verringern">−</button><output>${Number.isFinite(target) ? target : "—"} °C</output><button type="button" data-room-target="${esc(id)}" data-delta="0.5" aria-label="Raumziel erhöhen">+</button></div><p><b>Heizkörperthermostat</b><br>${esc(thermostatId || "nicht zugeordnet")} · ${esc(value(thermostat?.attributes?.temperature, "Soll unbekannt"))}</p><p><b>Infrarotheizung</b><br>${esc(irId || "nicht zugeordnet")} · ${esc(value(ir?.state, "nicht zugeordnet"))}</p><a href="/smart_heating#zone=${encodeURIComponent(id)}">Raumeinstellungen öffnen</a></article>`;
    };
    const modes = [["party", "Party"], ["visit", "Besuch"], ["return_home", "Heimweg"], ["chimney_sweep", "Schornsteinfeger"]];
    this.innerHTML = `<ha-card><main class="sh-final"><header class="sh-header"><div><p>SMART HEATING</p><h1>${esc(this._config.title || "Smart Heating")}</h1><small>Passiv · ${esc(value(this._data?.version))}</small></div><button type="button" class="sh-settings-button" data-settings>Einstellungen</button></header>${this._error ? `<p role="alert">${esc(this._error)}</p>` : ""}<section class="sh-section"><h2>Heizungssteuerung</h2><p>${enabled ? "Heizfreigabe aktiv · Smart Heating bleibt passiv" : "Heizfreigabe aus · keine Heizanforderung"}</p><div class="sh-buttons">${control("automatic", "Automatik", operation === "automatic" && enabled)}${control("manual_heat", "Dauerhaft Komfort", operation === "manual_heat" && enabled)}${control("manual_setback", "Dauerhaft Absenkung", operation === "manual_setback" && enabled)}${control("off", "Aus", !enabled)}</div><div class="sh-buttons">${modes.map(([id, label]) => control(id, label, internal[id] === true)).join("")}</div></section><section class="sh-section"><h2>Hauptheizung</h2><p><b>Status:</b> ${esc(value(climate?.state, "nicht erreichbar"))} · <b>Ist/Soll:</b> ${esc(value(climate?.attributes?.current_temperature))} / ${esc(value(climate?.attributes?.temperature))} · <b>Modus:</b> ${esc(value(climate?.attributes?.hvac_action || climate?.state))}</p><small>${esc(climateId || "Keine zentrale Tado-Heizung zugeordnet")}</small></section><section class="sh-section"><h2>Räume</h2><div class="sh-room-grid">${zones.length ? zones.map(room).join("") : "<p>Keine Räume konfiguriert.</p>"}</div></section><p class="sh-note">Wochenprogramm, Zuordnungen, IR-Automatik, Diagnose und Migration befinden sich ausschließlich in den Einstellungen.</p></main></ha-card>`;
    this._style(); this.querySelector("main.sh-final")?.classList.add("sh-app");
    if (!this.querySelector("style[data-final-dashboard]")) { const style = document.createElement("style"); style.dataset.finalDashboard = ""; style.textContent = `.sh-final{padding:16px;color:var(--primary-text-color)}.sh-header{display:flex;justify-content:space-between;gap:12px;align-items:center}.sh-header h1{margin:.2em 0}.sh-header p{margin:0;color:var(--secondary-text-color)}.sh-settings-button,.sh-control,.sh-room-control button{border:1px solid var(--divider-color);border-radius:10px;background:var(--secondary-background-color);color:var(--primary-text-color);padding:9px 12px;cursor:pointer;font:inherit}.sh-control.active{background:var(--primary-color);color:var(--text-primary-color,#fff)}.sh-buttons{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.sh-section{border:1px solid var(--divider-color);border-radius:14px;padding:14px;margin:12px 0}.sh-section h2{margin-top:0}.sh-main-facts,.sh-room-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.sh-room-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.sh-room{border:1px solid var(--divider-color);border-radius:12px;padding:12px;min-width:0}.sh-room header{display:flex;justify-content:space-between;gap:8px}.sh-room h3{margin:0}.sh-room-facts span{padding:8px;background:var(--secondary-background-color);border-radius:8px}.sh-room-facts b,.sh-room p b{display:block;font-size:.8em;color:var(--secondary-text-color)}.sh-room-control{display:flex;align-items:center;justify-content:space-between;margin:10px 0}.sh-room a{color:var(--primary-color)}.sh-note{color:var(--secondary-text-color);font-size:.85em}@media(max-width:900px){.sh-room-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.sh-header{align-items:flex-start;flex-direction:column}.sh-main-facts,.sh-room-facts{grid-template-columns:1fr 1fr}.sh-room-grid{grid-template-columns:1fr}}`; this.appendChild(style); }
    this.querySelector("[data-settings]")?.addEventListener("click", () => this._finalNavigate("/smart_heating"));
    this.querySelectorAll("[data-internal-mode]").forEach(button => button.addEventListener("click", () => { const id = button.dataset.internalMode; if (id === "off") this._finalSetInternal({ enabled: false, operating_mode: "off" }); else if (["automatic", "manual_heat", "manual_setback"].includes(id)) this._finalSetInternal({ enabled: true, operating_mode: id }); else this._finalSetInternal({ [id]: internal[id] !== true }); }));
    this.querySelectorAll("[data-room-target]").forEach(button => button.addEventListener("click", () => { const id = button.dataset.roomTarget, current = Number(internal.zones?.[id]?.comfort_temperature ?? 21); this._finalSetInternal({ zone_id: id, comfort_temperature: Math.max(5, Math.min(35, current + Number(button.dataset.delta))) }); }));
  };
})();
queueMicrotask(() => document.querySelectorAll("smart-heating-card").forEach(card => card._renderModern?.()));
