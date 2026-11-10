import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/harness.html");
  await expect(page.locator("smart-heating-card").first().locator(".sh-app")).toBeVisible();
  await page.evaluate(() => { const card=document.querySelector("smart-heating-card");card.setConfig({entry_id:"fixture-0",display_mode:"custom"});card.hass=window.hass; });
  await expect(page.getByTestId("status").first()).toContainText("Kompatibilitätsmodus");
  await expect(page.getByTestId("version").first()).toContainText("0.1.0-beta.40");
  await expect(page.locator("smart-heating-card").first().locator(".footer-note")).toContainText("Heizungs-, Thermostat-, Scheduler- und Sondermodus-Steuerung bleibt unverändert");
});

test("renders native JavaScript dashboard with compact schedule and rooms", async ({ page }, testInfo) => {
  await page.evaluate(() => { const card=document.querySelector("smart-heating-card");card.setConfig({entry_id:"fixture-0",display_mode:"dashboard"});card.hass=window.hass; });
  const card=page.locator("smart-heating-card").first();
  await expect(card.locator(".sh-app")).toBeVisible();
  await expect(card.locator(".sh-schedule-row")).toHaveCount(2);
  await expect(card.locator(".sh-room")).toContainText(["Badezimmer"]);
  await page.screenshot({path:`test-results/${testInfo.project.name}-native-dashboard.png`,fullPage:true});
});

test("supports compact and individual configuration modes without writes", async ({ page }) => {
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card.setConfig({ entry_id: "fixture-compact", display_mode: "compact" }); card.hass = window.hass; });
  await expect(page.locator("[data-display-mode=compact]")).toBeVisible();
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=schedule]")).toHaveCount(0);
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card.setConfig({ entry_id: "fixture-custom", display_mode: "custom", visible_sections: ["rooms", "diagnostics"] }); card.hass = window.hass; });
  await expect(page.locator("[data-display-mode=custom]").first().locator("section[data-section=rooms]")).toBeVisible();
  await expect(page.locator("[data-display-mode=custom]").first().locator("section[data-section=schedule]")).toHaveCount(0);
  const calls = await page.evaluate(() => window.__calls);
  expect(calls.every((call) => call.type === "smart_heating/plan/get")).toBeTruthy();
});

test("editor emits the complete visual configuration", async ({ page }) => {
  const result = await page.evaluate(async () => { await customElements.whenDefined("smart-heating-card-editor"); const editor = document.createElement("smart-heating-card-editor"); document.body.append(editor); editor.setConfig({ entry_id: "fixture" }); return await new Promise((resolve) => { editor.addEventListener("config-changed", (event) => resolve(event.detail.config), { once: true }); editor.querySelector("[data-mode]").value = "compact"; editor.querySelector("[data-mode]").dispatchEvent(new Event("change", { bubbles: true })); }); });
  expect(result.display_mode).toBe("compact"); expect(result.entry_id).toBe("fixture"); expect(result.visible_sections).toContain("rooms");
});

test("editor keeps IR automation disabled by default and persists passive settings", async ({ page }) => {
  const result = await page.evaluate(async () => { const editor = document.createElement("smart-heating-card-editor"); document.body.append(editor); editor.setConfig({ entry_id: "fixture" }); const fields = { auto: editor.querySelector("[data-ir-auto]"), entity: editor.querySelector("[data-ir-entity]"), strategy: editor.querySelector("[data-ir-strategy]"), comfort: editor.querySelector("[data-ir-comfort]"), setback: editor.querySelector("[data-ir-setback]") }; const initial = { auto: fields.auto.checked, strategy: fields.strategy.value }; return await new Promise(resolve => { editor.addEventListener("config-changed", event => resolve({ initial, config: event.detail.config }), { once: true }); fields.auto.checked = true; fields.entity.value = "climate.badezimmer_ir"; fields.strategy.value = "temperature"; fields.comfort.value = "24"; fields.setback.value = "17"; fields.auto.dispatchEvent(new Event("change", { bubbles: true })); }); });
  expect(result.initial.auto).toBeFalsy(); expect(result.initial.strategy).toBe("off"); expect(result.config.infrared_automatic_control).toBeTruthy(); expect(result.config.infrared_climate_entity).toBe("climate.badezimmer_ir"); expect(result.config.infrared_setback_strategy).toBe("temperature"); expect(result.config.infrared_comfort_temperature).toBe(24); expect(result.config.infrared_setback_temperature).toBe(17);
});

test("shows bathroom room target, radiator setpoint, and IR climate separately without writes", async ({ page }) => {
  await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    card._data.options.management.zones = [{ id: "bathroom", name: "Badezimmer", thermostat_entities: ["climate.heizthermostat_badezimmer"], infrared_climate_entities: ["climate.metal_panel_heater"] }];
    card._data.status.zones = [{ zone_id: "bathroom", name: "Badezimmer", desired_room_temperature: 24, thermostat_setpoint: 27, room_temperature: 23.5, thermostats: [{ entity_id: "climate.heizthermostat_badezimmer", state: "heat", hvac_action: "idle", setpoint_temperature: 27 }], infrared_thermostats: [{ entity_id: "climate.metal_panel_heater", state: "off", current_temperature: 22, setpoint_temperature: 24 }], infrared: { entity_ids: ["climate.metal_panel_heater"], automatic_control: false, comfort_temperature: 24, setback_strategy: "off" } }];
    window.hass.states = { "climate.heizthermostat_badezimmer": { state: "heat", attributes: { current_temperature: 23.5, temperature: 27, hvac_action: "idle" } }, "climate.metal_panel_heater": { state: "off", attributes: { current_temperature: 22, temperature: 24 } } };
    window.__serviceCalls = [];
    card._render();
  });
  const room = page.locator("smart-heating-card").first().locator('[data-section=rooms] [data-room=bathroom]');
  await expect(room).toContainText("Raumziel: 24 °C");
  await expect(room).toContainText("Zigbee-Thermostat");
  await expect(room).toContainText("Soll 27 °C");
  await expect(room).toContainText("Infrarotheizung");
  await expect(room).toContainText("Komfort 24 °C");
  expect(await page.evaluate(() => window.__serviceCalls.length)).toBe(0);
});

test("editor persists filter, order, sorting, visibility, and display options", async ({ page }) => {
  const result = await page.evaluate(async () => { const editor = document.createElement("smart-heating-card-editor"); document.body.append(editor); editor.setConfig({ entry_id: "fixture", visible_sections: ["rooms", "operation"] }); return await new Promise((resolve) => { editor.addEventListener("config-changed", event => resolve(event.detail.config), { once: true }); editor.querySelector("[data-room-filter]").value = "bathroom, Küche"; editor.querySelector("[data-order]").value = "rooms, operation"; editor.querySelector("[data-sort]").value = "name"; editor.querySelector("[data-windows]").checked = false; editor.querySelector("[data-windows]").dispatchEvent(new Event("change", { bubbles: true })); }); });
  expect(result.room_filter).toEqual(["bathroom", "Küche"]); expect(result.visible_sections.slice(0, 2)).toEqual(["rooms", "operation"]); expect(result.sort).toBe("name"); expect(result.show_windows).toBeFalsy();
});

test("deduplicates read-only calls for two cards using the same entry", async ({ page }) => {
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); const second = document.createElement("smart-heating-card"); document.body.append(second); second.setConfig({ entry_id: "shared-entry" }); second.hass = window.hass; card.setConfig({ entry_id: "shared-entry" }); card.hass = window.hass; });
  await page.waitForTimeout(50); const entries = await page.evaluate(() => window.__calls.filter(call => call.entry_id === "shared-entry")); expect(entries).toHaveLength(1); expect(entries[0].type).toBe("smart_heating/plan/get");
});

test("does not rerender or refetch on unrelated HA state object updates", async ({ page }) => {
  const before = await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    card.__renderCount = 0;
    const original = card._render.bind(card);
    card._render = (...args) => { card.__renderCount++; return original(...args); };
    return { calls: window.__calls.length, html: card.innerHTML };
  });
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card.hass = { ...window.hass }; });
  const after = await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    return { calls: window.__calls.length, html: card.innerHTML, renders: card.__renderCount };
  });
  expect(after.calls).toBe(before.calls);
  expect(after.renders).toBe(0);
  expect(after.html).toBe(before.html);
  const calls = await page.evaluate(() => window.__calls);
  expect(calls.every(call => call.type === "smart_heating/plan/get")).toBeTruthy();
});

test("updates live data without a polling loop", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await page.evaluate(() => { window.__fixtureState.status.zones[0].window_state = "open"; window.__fixtureState.status.observed.window_status = "open_or_tilted"; document.querySelector("smart-heating-card")._data = structuredClone(window.__fixtureState); document.querySelector("smart-heating-card")._render(); });
  await expect(card.locator("section[data-section=windows]")).toContainText("offen");
  const calls = await page.evaluate(() => window.__calls); expect(calls.every((call) => call.type === "smart_heating/plan/get")).toBeTruthy();
});

test("shows missing data instead of inventing temperatures", async ({ page }) => {
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card._data.status.zones[0].temperatures = [{ entity_id: "sensor.missing", state: "unavailable" }]; card._data.status.zones[0].target_temperature = null; card._render(); });
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=rooms]")).toContainText("nicht vorhanden"); await expect(page.locator("smart-heating-card").first().locator("section[data-section=rooms]")).toContainText("Daten teilweise nicht verfügbar");
});

test("keeps multiple card instances independent", async ({ page }) => { await expect(page.locator("smart-heating-card")).toHaveCount(2); const entries = await page.evaluate(() => window.__calls.map((call) => call.entry_id)); expect(entries).toContain("fixture-0"); expect(entries).toContain("fixture-1"); });

test("uses the full narrow viewport without horizontal overflow", async ({ page }) => { const widths = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: window.innerWidth })); expect(widths.body).toBeLessThanOrEqual(widths.viewport + 1); });

test("beta57 keeps bathroom room target, radiator setpoint, and infrared values separate", async ({ page }) => {
  await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    card._config.display_mode = "dashboard";
    card._data.options.management.zones = [{ id: "bathroom", name: "Badezimmer", thermostat_entities: ["climate.heizthermostat_badezimmer"], infrared_climate_entities: ["climate.metal_panel_heater"] }];
    card._data.status.zones = [{ zone_id: "bathroom", name: "Badezimmer", room_temperature: 23.5, desired_room_temperature: 24, thermostat_setpoint: 27, thermostats: [{ entity_id: "climate.heizthermostat_badezimmer", state: "heat", setpoint_temperature: 27 }], infrared_thermostats: [{ entity_id: "climate.metal_panel_heater", state: "off", current_temperature: 22, setpoint_temperature: 24 }], infrared: { entity_ids: ["climate.metal_panel_heater"], comfort_temperature: 24, automatic_control: false, commands: [] } }];
    window.hass.states = { "climate.heizthermostat_badezimmer": { state: "heat", attributes: { current_temperature: 23.5, temperature: 27, hvac_action: "idle" } }, "climate.metal_panel_heater": { state: "off", attributes: { current_temperature: 22, temperature: 24 } } };
    window.__serviceCalls = [];
    card._render();
  });
  const room = page.locator('smart-heating-card .sh-room[data-climate="climate.heizthermostat_badezimmer"]');
  await expect(room).toContainText("Ziel 24 °C");
  await expect(room).toContainText("Heizkörperthermostat");
  await expect(room).toContainText("Soll 27 °C");
  await expect(room).toContainText("Infrarotheizung");
  await expect(room).toContainText("Komfort 24 °C");
  await expect(page.locator("smart-heating-card > ha-card > .sh-app > .sh-section > h3", { hasText: "Temperaturen" })).toHaveCount(0);
  expect(await page.evaluate(() => window.__serviceCalls.length)).toBe(0);
});


test("beta46 renders responsive theme-aware rooms and collapsible special modes", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await expect(card.locator("section[data-section=rooms] .room-grid")).toBeVisible();
  await expect(card.locator("section[data-section=special_modes] .mode-grid")).toHaveCount(1);
  await expect(card.locator("section[data-section=special_modes] .scroll-area")).toBeVisible();
  await expect(card.locator("section[data-section=diagnostics] details.expandable")).toHaveCount(1);
  await expect(card.locator("section[data-section=schedule] .day-row").first()).toBeVisible();
  const style = await card.locator("style[data-smart-heating-card-style]").textContent();
  expect(style).toContain("var(--primary-text-color)");
  expect(style).toContain("var(--card-background-color");
});

test("beta46 schedule hides seconds and duplicate weekday abbreviations", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await page.evaluate(() => {const card=document.querySelector("smart-heating-card");card._data.schedule.monday=[{start:"05:30:00",end:"21:00:00"}];card._config.display_mode="dashboard";card._render();});
  await expect(card.locator(".sh-schedule-row").first()).toContainText("05:30–21:00");
  await expect(card.locator(".sh-schedule-row").first()).not.toContainText("05:30:00");
  await expect(card.locator(".sh-schedule-row")).toHaveCount(2);
});


test("beta46 priority chips navigate to the matching mode without writes", async ({ page }) => {
 const card=page.locator("smart-heating-card").first();
 await expect(card.locator("[data-priority-mode=party]")).toBeVisible();
 await card.locator("[data-priority-mode=party]").click();
 await expect(card.locator("[data-special-mode=party]")).toBeVisible();
 expect(await page.evaluate(()=>window.__calls.every(call=>call.type==="smart_heating/plan/get"))).toBeTruthy();
});

test("beta46 infrared zone is shown separately without thermostat write", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.options.management.zones.push({id:"ir",name:"Infrarotheizung",type:"infrared",switch_entities:["switch.ir"]});card._render();});
 const card=page.locator("smart-heating-card").first();
 await expect(card.locator('[data-section="rooms"] [data-room="ir"]')).toContainText("Infrarot");
 expect(await page.evaluate(()=>window.__calls.every(call=>call.type==="smart_heating/plan/get"))).toBeTruthy();
});


test("beta46 editor configures visible room count", async ({ page }) => {
 const result=await page.evaluate(async()=>{const editor=document.createElement("smart-heating-card-editor");document.body.append(editor);editor.setConfig({entry_id:"fixture",visible_room_count:2});return await new Promise(resolve=>{editor.addEventListener("config-changed",e=>resolve(e.detail.config),{once:true});const field=editor.querySelector("[data-visible-rooms]");field.value="4";field.dispatchEvent(new Event("change",{bubbles:true}));});});
 expect(result.visible_room_count).toBe(4);
});

test("beta46 prioritizes chimney sweep over numeric mode priorities", async ({ page }) => {
 const card=page.locator("smart-heating-card").first();
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.options.management.special_modes=[{id:"party",name:"Party",priority:9999},{id:"chimney_sweep",name:"Schornsteinfeger",priority:1}];card._render();});
 await expect(card.locator("[data-priority-mode]").first()).toHaveAttribute("data-priority-mode","chimney_sweep");
});


test("beta46 infrared switch shows actual HA on/off state without sending commands", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"switch.ir":{"state":"on"},"input_boolean.party":{"state":"on"}};card._data.options.management.zones.push({id:"ir",name:"Infrarotheizung",type:"infrared",switch_entities:["switch.ir"]});card._render();});
 const card=page.locator("smart-heating-card").first();
 await expect(card.locator('[data-section="rooms"] [data-room="ir"]')).toContainText("Eingeschaltet");
 expect(await page.evaluate(()=>window.__calls.every(call=>call.type==="smart_heating/plan/get"))).toBeTruthy();
});


test("beta46 current HA off state overrides stale special-mode active snapshot", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"input_boolean.party":{state:"off"}};card._data.options.management.special_modes=[{id:"party",name:"Party",active:true,status_source:"input_boolean.party",available:true}];card._render();});
 await expect(page.locator("smart-heating-card").first().locator("[data-special-mode=party]")).toContainText("Inaktiv");
});

test("beta46 editor persists visible special-mode count", async ({ page }) => {
 const result=await page.evaluate(async()=>{const editor=document.createElement("smart-heating-card-editor");document.body.append(editor);editor.setConfig({entry_id:"fixture"});return await new Promise(resolve=>{editor.addEventListener("config-changed",e=>resolve(e.detail.config),{once:true});const input=editor.querySelector("[data-visible-modes]");input.value="6";input.dispatchEvent(new Event("change",{bubbles:true}));});});
 expect(result.visible_mode_count).toBe(6);
});


test("beta46 additional special modes expand and collapse on demand", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._config.visible_mode_count=2;card._data.options.management.special_modes=Array.from({length:5},(_,i)=>({id:"mode"+i,name:"Modus "+i,available:true}));card._render();});
 const card=page.locator("smart-heating-card").first();
 const extra=card.locator("[data-extra-mode]");
 await expect(extra).toHaveCount(3);
 await expect(extra.first()).toBeHidden();
 await card.locator("[data-mode-more]").click();
 await expect(extra.first()).toBeVisible();
 await card.locator("[data-mode-more]").click();
 await expect(extra.first()).toBeHidden();
});

test("beta46 priority navigation expands hidden special mode", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._config.visible_mode_count=1;card._data.options.management.special_modes=[{id:"party",name:"Party",priority:100},{id:"visit",name:"Besuch",priority:50}];card._render();});
 const card=page.locator("smart-heating-card").first();
 await expect(card.locator("[data-special-mode=visit]")).toBeHidden();
 await card.locator("[data-priority-mode=visit]").click();
 await expect(card.locator("[data-special-mode=visit]")).toBeVisible();
});


test("beta46 pinned rooms appear before other configured rooms", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._config.pinned_rooms=["bedroom"];card._config.visible_room_count=1;card._data.options.management.zones=[{id:"bathroom",name:"Bad"},{id:"bedroom",name:"Schlafzimmer"}];card._render();});
 const first=page.locator("smart-heating-card").first().locator('[data-section="rooms"] .room').first();
 await expect(first).toHaveAttribute("data-room","bedroom");
});

test("beta46 editor saves pinned room selection", async ({ page }) => {
 const result=await page.evaluate(async()=>{const editor=document.createElement("smart-heating-card-editor");document.body.append(editor);editor.setConfig({entry_id:"fixture"});return await new Promise(resolve=>{editor.addEventListener("config-changed",e=>resolve(e.detail.config),{once:true});const input=editor.querySelector("[data-pinned-rooms]");input.value="bedroom, bathroom";input.dispatchEvent(new Event("change",{bubbles:true}));});});
 expect(result.pinned_rooms).toEqual(["bedroom","bathroom"]);
});


test("beta46 infrared controls remain disabled by default", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"switch.ir":{state:"off"}};card._data.options.management.zones=[{id:"ir",name:"IR",type:"infrared",switch_entities:["switch.ir"]}];card._render();});
 await expect(page.locator("smart-heating-card").first().locator("[data-ir-switch]")).toHaveCount(0);
});

test("beta46 explicitly enabled infrared control calls switch only on click", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"switch.ir":{state:"off"}};window.__serviceCalls=[];window.hass.callService=async(domain,service,data)=>window.__serviceCalls.push({domain,service,data});card._config.allow_manual_ir_control=true;card._data.options.management.zones=[{id:"ir",name:"IR",type:"infrared",switch_entities:["switch.ir"]}];card._render();});
 const button=page.locator("smart-heating-card").first().locator("[data-ir-switch]");
 await expect(button).toBeVisible();
 expect(await page.evaluate(()=>window.__serviceCalls.length)).toBe(0);
 await button.click();
 await expect.poll(()=>page.evaluate(()=>window.__serviceCalls.length)).toBe(1);
 expect(await page.evaluate(()=>window.__serviceCalls[0])).toEqual({domain:"switch",service:"turn_on",data:{entity_id:"switch.ir"}});
});


test("beta46 priority strip reflects live HA off state instead of stale snapshot", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"input_boolean.party":{state:"off"}};card._data.options.management.special_modes=[{id:"party",name:"Party",active:true,priority:50,status_source:"input_boolean.party"}];card._render();});
 const chip=page.locator("smart-heating-card").first().locator("[data-priority-mode=party]");
 await expect(chip).toContainText("Party");
 await expect(chip).not.toContainText("●");
});


test("beta46 footer distinguishes opt-in infrared control from passive heating controls", async ({ page }) => {
 const footer=page.locator("smart-heating-card").first().locator(".footer-note");
 await expect(footer).toContainText("Infrarot-Schaltflächen");
 await expect(footer).toContainText("manuelle Switch-Aktionen");
});


test("beta46 stale infrared button cannot reverse a newer HA state", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"switch.ir":{state:"off"}};window.__serviceCalls=[];window.hass.callService=async(...args)=>window.__serviceCalls.push(args);card._config.allow_manual_ir_control=true;card._data.options.management.zones=[{id:"ir",name:"IR",type:"infrared",switch_entities:["switch.ir"]}];card._render();window.hass.states["switch.ir"].state="on";});
 await page.locator("smart-heating-card").first().locator("[data-ir-switch]").first().click();
 expect(await page.evaluate(()=>window.__serviceCalls.length)).toBe(0);
});


test("beta46 pinned room matches display name when ID differs", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._config.pinned_rooms=["Schlafzimmer"];card._data.options.management.zones=[{id:"bathroom",name:"Bad"},{id:"bedroom",name:"Schlafzimmer"}];card._render();});
 await expect(page.locator("smart-heating-card").first().locator('[data-section="rooms"] .room').first()).toHaveAttribute("data-room","bedroom");
});


test("beta46 pinned room ordering remains stable for unpinned rooms", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._config.pinned_rooms=["Schlafzimmer"];card._data.options.management.zones=[{id:"bathroom",name:"Bad"},{id:"kitchen",name:"Küche"},{id:"bedroom",name:"Schlafzimmer"}];card._render();});
 const ids=await page.locator("smart-heating-card").first().locator('[data-section="rooms"] .room').evaluateAll(nodes=>nodes.map(node=>node.dataset.room));
 expect(ids).toEqual(["bedroom","bathroom","kitchen"]);
});


test("beta46 successful infrared retry clears prior service error", async ({ page }) => {
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"switch.ir":{state:"off"}};window.hass.callService=async()=>{};card._config.allow_manual_ir_control=true;card._data.options.management.zones=[{id:"ir",name:"IR",type:"infrared",switch_entities:["switch.ir"]}];card._error="Alter Schaltfehler";card._render();});
 await page.locator("smart-heating-card").first().locator("[data-ir-switch]").first().click();
 expect(await page.evaluate(()=>document.querySelector("smart-heating-card")._error)).toBeNull();
 await expect(page.locator("smart-heating-card").first().locator('[data-testid="error"]')).toHaveCount(0);
});


test("beta46 infrared-only zone is excluded from thermostat temperatures", async ({ page }) => {
 await page.evaluate(() => { const card=document.querySelector("smart-heating-card"); card._data.options.management.zones=[{id:"ir",name:"IR Panel",type:"infrared",switch_entities:["switch.ir"]}]; card._render(); });
 const card=page.locator("smart-heating-card").first();
 await expect(card.locator('[data-section="rooms"] [data-room="ir"]')).toHaveCount(1);
 await expect(card.locator('[data-section="temperatures"] [data-room="ir"]')).toHaveCount(0);
 await expect(card.locator('[data-section="temperatures"]')).toContainText("Heiztemperatur");
});


test("beta46 renders eight legacy priority stages without fabricating unavailable status", async ({ page }) => {
 const chain=page.locator("smart-heating-card").first().locator(".priority-chain");
 await expect(chain.locator("li")).toHaveCount(8);
 await expect(chain.locator("li").first()).toContainText("Schornsteinfeger");
 await expect(chain.locator("li").nth(1)).toContainText("Heizfreigabe");
 await expect(chain.locator("li").nth(7)).toContainText("Komfortbetrieb");
 await expect(chain).toContainText("unbekannt");
});


test("beta46 room settings link targets exact backend zone without write", async ({ page }) => {
 const card=page.locator("smart-heating-card").first();
 await expect(card.locator('[data-section="rooms"] [data-room="bathroom"] .room-settings-link')).toHaveAttribute("href", "/smart_heating#zone=bathroom");
 expect(await page.evaluate(()=>window.__calls.every(call=>call.type==="smart_heating/plan/get"))).toBeTruthy();
});


test("beta46 distinguishes open and tilted windows in priority chain", async ({ page }) => {
 const chain=page.locator("smart-heating-card").first().locator(".priority-chain");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.status.observed.window_status="open";card._render();});
 await expect(chain.locator("li").nth(2)).toContainText("offen");
 await expect(chain.locator("li").nth(3)).toContainText("nicht gekippt");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.status.observed.window_status="tilted";card._render();});
 await expect(chain.locator("li").nth(2)).toContainText("nicht offen");
 await expect(chain.locator("li").nth(3)).toContainText("gekippt");
});


test("beta46 chimney sweep priority uses actual helper state", async ({ page }) => {
 const first=page.locator("smart-heating-card").first().locator(".priority-chain li").first();
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"input_boolean.schornsteinfeger":{state:"on"}};card._render();});
 await expect(first).toContainText("aktiv");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states["input_boolean.schornsteinfeger"].state="off";card._render();});
 await expect(first).toContainText("inaktiv");
});


test("beta46 presence priority requires explicit backend evidence", async ({ page }) => {
 const item=page.locator("smart-heating-card").first().locator(".priority-chain li").nth(4);
 await expect(item).toContainText("Status nicht nachgewiesen");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.status.presence={status:"away"};card._render();});
 await expect(item).toContainText("abwesend");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.status.presence={status:"home"};card._render();});
 await expect(item).toContainText("anwesend");
});


test("beta46 night priority follows existing input_boolean.heizung without commands", async ({ page }) => {
 const night=page.locator("smart-heating-card").first().locator(".priority-chain li").nth(5);
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states={"input_boolean.heizung":{state:"off"}};card._render();});
 await expect(night).toContainText("Absenkbetrieb");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass.states["input_boolean.heizung"].state="on";card._render();});
 await expect(night).toContainText("Komfortzeit");
 expect(await page.evaluate(()=>window.__calls.every(call=>call.type==="smart_heating/plan/get"))).toBeTruthy();
});


test("beta46 comfort is explicitly a lower-priority fallback", async ({ page }) => {
 const last=page.locator("smart-heating-card").first().locator(".priority-chain li").last();
 await expect(last).toContainText("Komfortbetrieb");
 await expect(last).toContainText("nur wenn keine höhere Regel greift");
});


test("beta46 does not misrepresent combined backend window status", async ({ page }) => {
 const chain=page.locator("smart-heating-card").first().locator(".priority-chain li");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.status.observed.window_status="open_or_tilted";card._render();});
 await expect(chain.nth(2)).toContainText("nicht unterscheidbar");
 await expect(chain.nth(3)).toContainText("nicht unterscheidbar");
 await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._data.status.observed.window_status="closed_or_clear";card._render();});
 await expect(chain.nth(2)).toContainText("nicht offen");
 await expect(chain.nth(3)).toContainText("nicht gekippt");
});


test("all eight reference priorities link to known backend settings sections", async ({ page }) => {
 const links=page.locator("smart-heating-card").first().locator(".priority-chain li a");
 await expect(links).toHaveCount(8);
 const allowed=new Set(["safety","windows","persons","rooms"]);
 for (const link of await links.all()) {
   const href=await link.getAttribute("href");
   expect(href.startsWith("/smart_heating#section=")).toBe(true);
   expect(allowed.has(href.split("#section=")[1])).toBe(true);
 }
});


test("beta46 main card remains within viewport across phone tablet and desktop widths", async ({ page }) => {
 const card=page.locator("smart-heating-card").first();
 for (const width of [375,768,1280]) {
   await page.setViewportSize({width,height:900});
   await expect(card.locator("section[data-section=rooms]")).toBeVisible();
   const dimensions=await card.evaluate(node=>({right:node.getBoundingClientRect().right,bodyWidth:document.body.scrollWidth,viewport:window.innerWidth}));
   expect(dimensions.right).toBeLessThanOrEqual(width+2);
   expect(dimensions.bodyWidth).toBeLessThanOrEqual(width+2);
 }
});



test.describe("native dashboard beta.51", () => {
  test.beforeEach(async ({page}) => {
    await page.evaluate(() => {
      const card=document.querySelector("smart-heating-card");
      window.__services=[];
      window.hass={...window.hass,states:{
        "input_number.heiztemperatur":{state:"21",attributes:{min:5,max:30,step:0.5}},
        "input_number.absenktemperatur":{state:"17",attributes:{min:5,max:30,step:0.5}},
        "input_boolean.party":{state:"off"},
        "input_boolean.besuch":{state:"off"},
        "input_boolean.heimweg":{state:"off"},
        "input_boolean.heizung_sommermodus":{state:"off"},
        "automation.heizung_automatik_ersetzt_node_red":{state:"on"},
        "climate.bathroom":{state:"heat",attributes:{current_temperature:19.4,temperature:24}}
      },callService:async(domain,service,data)=>{window.__services.push({domain,service,data});}};
      card.setConfig({entry_id:"fixture-0",display_mode:"dashboard"});
      card.hass=window.hass;
    });
    await expect(page.locator("smart-heating-card").first().locator(".sh-app")).toBeVisible();
  });
  test("theme uses HA color variables rather than hardcoded white",async({page})=>{
    const card=page.locator("smart-heating-card").first();
    const css=await card.locator("style").first().evaluate(el=>el.textContent);
    expect(css).toContain("var(--ha-card-background");
    expect(css).toContain("var(--primary-text-color");
    expect(css).toContain("@container(max-width:540px)");
  });
  test("temperature buttons call only input_number.set_value",async({page})=>{
    const card=page.locator("smart-heating-card").first();
    await card.locator('[data-entity="input_number.heiztemperatur"][data-adjust="1"]').click();
    const calls=await page.evaluate(()=>window.__services);
    expect(calls).toEqual([{domain:"input_number",service:"set_value",data:{entity_id:"input_number.heiztemperatur",value:21.5}}]);
  });
  test("special modes only toggle the existing input_boolean helpers",async({page})=>{
    const card=page.locator("smart-heating-card").first();
    await card.locator('[data-toggle="input_boolean.party"]').click();
    expect(await page.evaluate(()=>window.__services)).toEqual([{domain:"input_boolean",service:"turn_on",data:{entity_id:"input_boolean.party"}}]);
  });
  test("unavailable helpers disable writes",async({page})=>{
    await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");delete window.hass.states["input_number.heiztemperatur"];delete window.hass.states["input_boolean.party"];card._render();});
    const card=page.locator("smart-heating-card").first();
    await expect(card.locator('[data-entity="input_number.heiztemperatur"][data-adjust="1"]')).toBeDisabled();
    await expect(card.locator('[data-mode-source="input_boolean.party"]')).toBeDisabled();
    expect(await page.evaluate(()=>window.__services)).toEqual([]);
  });
  test("diagnostics remain expanded after relevant state updates",async({page})=>{
    const card=page.locator("smart-heating-card").first();
    await card.locator('details[data-panel="diagnostics"] summary').click();
    await expect(card.locator('details[data-panel="diagnostics"]')).toHaveAttribute("open","");
    await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");window.hass={...window.hass,states:{...window.hass.states,"input_number.heiztemperatur":{state:"22",attributes:{min:5,max:30,step:0.5}}}};card.hass=window.hass;});
    await expect(card.locator('details[data-panel="diagnostics"]')).toHaveAttribute("open","");
  });
  test("updates helper states without rebuilding the DOM or losing scroll position",async({page})=>{
    const card=page.locator("smart-heating-card").first();
    await page.evaluate(()=>{
      const card=document.querySelector("smart-heating-card");
      card.__originalApp=card.querySelector(".sh-app");
      card.__originalButton=card.querySelector('[data-toggle="input_boolean.party"]');
      window.scrollTo(0,200);
      window.hass={...window.hass,states:{...window.hass.states,
        "input_number.heiztemperatur":{state:"22",attributes:{min:5,max:30,step:0.5}},
        "input_boolean.party":{state:"on"}}};
      card.hass=window.hass;
    });
    const result=await page.evaluate(()=>{
      const card=document.querySelector("smart-heating-card");
      return {sameApp:card.__originalApp===card.querySelector(".sh-app"),
        sameButton:card.__originalButton===card.querySelector('[data-toggle="input_boolean.party"]'),
        temp:card.querySelector('[data-temp="input_number.heiztemperatur"] strong')?.textContent,
        mode:card.querySelector('[data-toggle="input_boolean.party"]')?.getAttribute("aria-pressed")};
    });
    expect(result.sameApp).toBe(true);
    expect(result.sameButton).toBe(true);
    expect(result.temp).toContain("22");
    expect(result.mode).toBe("true");
  });
  test("opens climate room details through Home Assistant more-info",async({page})=>{
    const card=page.locator("smart-heating-card").first();
    await page.evaluate(()=>{window.__moreInfo=[];document.querySelector("smart-heating-card").addEventListener("hass-more-info",e=>window.__moreInfo.push(e.detail.entityId));});
    const room=card.locator(".sh-room[data-climate]").first();
    if(await room.count()){await room.click();expect((await page.evaluate(()=>window.__moreInfo)).length).toBe(1);}
  });
  test("renders configured custom special modes dynamically",async({page})=>{
    await page.evaluate(()=>{
      const card=document.querySelector("smart-heating-card");
      card._data.options={...(card._data.options||{}),management:{...(card._data.options?.management||{}),special_modes:[{id:"custom",name:"Zusatzbetrieb",status_source:"input_boolean.zusatzbetrieb",enabled:true}]}};
      window.hass={...window.hass,states:{...window.hass.states,"input_boolean.zusatzbetrieb":{state:"on"}}};
      card.hass=window.hass;card._render();
    });
    const card=page.locator("smart-heating-card").first();
    await expect(card.locator('[data-mode-source="input_boolean.zusatzbetrieb"]')).toContainText("Zusatzbetrieb");
    await expect(card.locator('[data-mode-source="input_boolean.zusatzbetrieb"]')).toHaveAttribute("aria-pressed","true");
    await expect(card.locator('[data-mode-source="input_boolean.party"]')).toHaveCount(0);
  });
  test("shows infrared panel in bathroom and respects opt-in control",async({page})=>{
    await page.evaluate(()=>{
      const card=document.querySelector("smart-heating-card");
      card._data.options={...(card._data.options||{}),management:{...(card._data.options?.management||{}),zones:[{id:"bathroom",name:"Badezimmer",type:"infrared",switch_entities:["switch.bad_ir"],thermostats:["climate.bathroom"]}]}};
      window.hass={...window.hass,states:{...window.hass.states,"switch.bad_ir":{state:"on"}}};
      card.hass=window.hass;card._render();
    });
    const card=page.locator("smart-heating-card").first();
    const ir=card.locator('[data-ir-switch="switch.bad_ir"]');
    await expect(ir).toContainText("Infrarot-Panel: Ein");
    await expect(ir).toBeDisabled();
    await page.evaluate(()=>{const card=document.querySelector("smart-heating-card");card._config={...card._config,allow_manual_ir_control:true};card._render();});
    await expect(ir).toBeEnabled();
    await ir.click();
    expect(await page.evaluate(()=>window.__services)).toContainEqual({domain:"switch",service:"turn_off",data:{entity_id:"switch.bad_ir"}});
  });
  test("does not overflow at mobile viewport widths",async({page},testInfo)=>{
    const card=page.locator("smart-heating-card").first();
    const result=await card.locator(".sh-app").evaluate(node=>({right:node.getBoundingClientRect().right,viewport:document.documentElement.clientWidth,overflow:node.scrollWidth-node.clientWidth}));
    expect(result.right).toBeLessThanOrEqual(result.viewport+2);
    if(result.overflow>2){const offenders=await card.locator(".sh-app").evaluate(root=>{const edge=root.getBoundingClientRect().right;return [...root.querySelectorAll("*")].map(el=>({tag:el.tagName,cls:el.className,right:Math.round(el.getBoundingClientRect().right),width:Math.round(el.getBoundingClientRect().width),scroll:el.scrollWidth,client:el.clientWidth})).filter(x=>x.right>edge+2||x.scroll>x.client+2).slice(0,12)});console.log("NATIVE_MOBILE_OVERFLOW",JSON.stringify(offenders));}
    expect(result.overflow).toBeLessThanOrEqual(2);
    await page.screenshot({path:`test-results/${testInfo.project.name}-native-mobile.png`,fullPage:true});
  });
});

test("internal dashboard settings persist without legacy helper service calls", async ({ page }) => {
  await page.evaluate(() => {
    const card=document.querySelector("smart-heating-card");
    card.setConfig({entry_id:"fixture-0",display_mode:"dashboard"});
    card.hass=window.hass;
    card._data.options=card._data.options||{};
    card._data.options.management={...(card._data.options.management||{}),internal:{enabled:true,operating_mode:"automatic",internal_only:false,comfort_temperature:21,night_temperature:18}};
    window.__internalCalls=[];
    const original=window.hass.callWS.bind(window.hass);
    window.hass.callWS=async msg=>{
      if(msg.type!=="smart_heating/admin/internal/set")return original(msg);
      window.__internalCalls.push(msg);
      return {internal:{...card._data.options.management.internal,...msg.item},active_control:false};
    };
    card._render();
  });
  const card=page.locator("smart-heating-card").first();
  await card.locator('[data-internal-isolation]').click();
  await card.locator('[data-internal-enabled]').click();
  await card.locator('[data-internal-operating="manual_setback"]').click();
  await card.locator('[data-internal-mode="party"]').click();
  const result=await page.evaluate(()=>({calls:window.__internalCalls,services:window.__services||[]}));
  expect(result.calls.map(call=>call.item)).toEqual([
    {internal_only:true},{enabled:false},{operating_mode:"manual_setback"},{internal_only:true,party:true}
  ]);
  expect(result.services).toHaveLength(0);
  await expect(card.locator('[data-internal-mode="party"]')).toHaveAttribute("aria-pressed","true");
});


test("all five internal special modes atomically activate passive isolation without service writes", async ({ page }) => {
  await page.evaluate(() => {
    const card=document.querySelector("smart-heating-card");
    card.setConfig({entry_id:"fixture-0",display_mode:"dashboard"});
    card._data.options=card._data.options||{};
    card._data.options.management={...(card._data.options.management||{}),internal:{enabled:true,internal_only:false,operating_mode:"automatic"}};
    window.__specialCalls=[];
    const original=window.hass.callWS.bind(window.hass);
    window.hass.callWS=async msg=>{
      if(msg.type!=="smart_heating/admin/internal/set")return original(msg);
      window.__specialCalls.push(msg.item);
      return {internal:{...card._data.options.management.internal,...msg.item},active_control:false};
    };
    window.__services=[];
    card._render();
  });
  const card=page.locator("smart-heating-card").first();
  for(const mode of ["party","visit","return_home","summer","chimney_sweep"]){
    await card.locator('[data-internal-mode="'+mode+'"]').click();
    await expect(card.locator('[data-internal-mode="'+mode+'"]')).toHaveAttribute("aria-pressed","true");
  }
  const result=await page.evaluate(()=>({calls:window.__specialCalls,services:window.__services||[]}));
  expect(result.calls).toEqual(["party","visit","return_home","summer","chimney_sweep"].map(mode=>({internal_only:true,[mode]:true})));
  expect(result.services).toHaveLength(0);
  await expect(card.getByTestId("internal-mode-preview-status")).toContainText("passive Vorschau");
});

test("per-room internal temperatures use zone-scoped websocket writes",async({page})=>{
  await page.evaluate(()=>{
    const card=document.querySelector("smart-heating-card");
    card.setConfig({entry_id:"fixture-0",display_mode:"dashboard"});
    card.hass=window.hass;
    card._data.options=card._data.options||{};
    card._data.options.management={
      ...(card._data.options.management||{}),
      zones:[{id:"bathroom",name:"Badezimmer"},{id:"bedroom",name:"Schlafzimmer"}],
      internal:{internal_only:true,enabled:true,comfort_temperature:21,night_temperature:18,zones:{bathroom:{comfort_temperature:24},bedroom:{comfort_temperature:18}}}
    };
    window.__zoneCalls=[];
    window.__services=[];
    const original=window.hass.callWS.bind(window.hass);
    window.hass.callWS=async msg=>{
      if(msg.type!=="smart_heating/admin/internal/set")return original(msg);
      window.__zoneCalls.push(msg.item);
      const internal=card._data.options.management.internal;
      const {zone_id,...patch}=msg.item;
      return {internal:{...internal,zones:{...internal.zones,[zone_id]:{...internal.zones[zone_id],...patch}}},active_control:false};
    };
    card._render();
  });
  const card=page.locator("smart-heating-card").first();
  await expect(card.locator('[data-zone-id="bathroom"][data-zone-key="comfort_temperature"]')).toHaveCount(2);
  await card.locator('[data-zone-id="bathroom"][data-zone-key="comfort_temperature"][data-zone-step="0.5"]').click();
  await card.locator('[data-zone-id="bedroom"][data-zone-key="comfort_temperature"][data-zone-step="-0.5"]').click();
  const result=await page.evaluate(()=>({calls:window.__zoneCalls,services:window.__services}));
  expect(result.calls).toEqual([
    {zone_id:"bathroom",comfort_temperature:24.5},
    {zone_id:"bedroom",comfort_temperature:17.5}
  ]);
  expect(result.services).toHaveLength(0);
});


test("shows room thermostat target diagnostics on mobile without service calls", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    card.setConfig({ entry_id: "fixture-0", display_mode: "dashboard" });
    card.hass = window.hass;
    card._data.options = card._data.options || {};
    card._data.options.management = {
      ...(card._data.options.management || {}),
      zones: [
        { id: "bathroom", name: "Badezimmer" },
        { id: "bedroom", name: "Schlafzimmer" },
        { id: "living", name: "Wohnzimmer" }
      ],
      internal: { internal_only: true, enabled: true, comfort_temperature: 21, night_temperature: 18 }
    };
    card._data.status = {
      ...(card._data.status || {}),
      zone_target_capability_summary: [
        { zone_id: "bathroom", target_temperature: 24, all_targets_supported: false,
          thermostats: [{ entity_id: "climate.bath", target_supported: false, reasons: ["target_out_of_range"] }] },
        { zone_id: "bedroom", target_temperature: 18, all_targets_supported: true,
          thermostats: [{ entity_id: "climate.bed", target_supported: true, reasons: [] }] },
        { zone_id: "living", target_temperature: null, all_targets_supported: false, thermostats: [] }
      ]
    };
    window.__services = [];
    card._render();
  });
  const card = page.locator("smart-heating-card").first();
  const panel = card.getByTestId("internal-panel");
  await expect(panel).toContainText("Thermostat-Eignung");
  await expect(panel).toContainText("Badezimmer");
  await expect(panel).toContainText("Sollwert außerhalb des Bereichs");
  await expect(panel).toContainText("Schlafzimmer");
  await expect(panel).toContainText("Geeignet");
  await expect(panel).toContainText("Kein Thermostat zugeordnet");
  const overflow = await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    return card.getBoundingClientRect().right - document.documentElement.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(2);
  expect(await page.evaluate(() => window.__services)).toHaveLength(0);
});


test("thermostat diagnostics remain safe with missing data and unavailable devices", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    card.setConfig({ entry_id: "fixture-0", display_mode: "dashboard" });
    card.hass = window.hass;
    card._data.status = { ...(card._data.status || {}), zone_target_capability_summary: null };
    window.__services = [];
    card._render();
  });
  const card = page.locator("smart-heating-card").first();
  await expect(card.getByTestId("internal-panel")).toContainText("Noch keine Raumdiagnose verfügbar");
  await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    card._data.status.zone_target_capability_summary = [
      { zone_id: "offline", target_temperature: 22, all_targets_supported: false,
        thermostats: [{ entity_id: "climate.offline", target_supported: false, reasons: ["unavailable"] }] },
      { zone_id: "step", target_temperature: 21.3, all_targets_supported: false,
        thermostats: [{ entity_id: "climate.step", target_supported: false, reasons: ["target_not_on_step"] }] },
      { zone_id: "invalid", target_temperature: null, all_targets_supported: false,
        thermostats: [{ entity_id: "climate.invalid", target_supported: false, reasons: ["invalid_target"] }] }
    ];
    card._render();
  });
  const panel = card.getByTestId("internal-panel");
  await expect(panel).toContainText("Nicht erreichbar");
  await expect(panel).toContainText("Sollwert passt nicht zum Einstellschritt");
  await expect(panel).toContainText("Kein gültiger Sollwert");
  expect(await page.evaluate(() => document.querySelector("smart-heating-card").getBoundingClientRect().right - document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
  expect(await page.evaluate(() => window.__services)).toHaveLength(0);
});


test("renders all four thermostat suitability categories without controls", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.evaluate(() => {
    const card = document.querySelector("smart-heating-card");
    card.setConfig({ entry_id: "fixture-0", display_mode: "dashboard" });
    card.hass = window.hass;
    const categories = [
      ["full", "fully_suitable", true],
      ["partial", "partially_suitable", false],
      ["unsupported", "not_suitable", false],
      ["unknown", "not_assessable", false]
    ];
    card._data.status = {
      ...(card._data.status || {}),
      zone_target_capability_summary: categories.map(([zone_id, suitability, all_targets_supported]) => ({
        zone_id, suitability, all_targets_supported, target_temperature: zone_id === "unknown" ? null : 24,
        thermostats: zone_id === "unknown" ? [] : [{ entity_id: "climate." + zone_id,
          target_supported: all_targets_supported, reasons: all_targets_supported ? [] : ["target_out_of_range"] }]
      }))
    };
    window.__services = [];
    card._render();
  });
  const panel = page.locator("smart-heating-card").first().getByTestId("internal-panel");
  for (const label of ["Vollständig geeignet", "Teilweise geeignet", "Nicht geeignet", "Nicht prüfbar"]) {
    await expect(panel).toContainText(label);
  }
  expect(await page.evaluate(() => window.__services)).toHaveLength(0);
});
