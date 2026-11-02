import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/harness.html");
  await expect(page.getByTestId("status").first()).toContainText("Kompatibilitätsmodus");
  await expect(page.getByTestId("version").first()).toContainText("0.1.0-beta.40");
  await expect(page.getByText("Diese Karte zeigt ausschließlich passive Daten.").first()).toBeVisible();
});

test("renders detailed passive overview and all weekdays", async ({ page }, testInfo) => {
  await expect(page.locator("[data-display-mode=detailed]").first()).toBeVisible();
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=schedule] .day-row")).toHaveCount(7);
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=rooms] .room strong").first()).toHaveText("Badezimmer");
  await page.screenshot({ path: `test-results/${testInfo.project.name}-lovelace-detailed.png`, fullPage: true });
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

test("editor persists filter, order, sorting, visibility, and display options", async ({ page }) => {
  const result = await page.evaluate(async () => { const editor = document.createElement("smart-heating-card-editor"); document.body.append(editor); editor.setConfig({ entry_id: "fixture", visible_sections: ["rooms", "operation"] }); return await new Promise((resolve) => { editor.addEventListener("config-changed", event => resolve(event.detail.config), { once: true }); editor.querySelector("[data-room-filter]").value = "bathroom, Küche"; editor.querySelector("[data-order]").value = "rooms, operation"; editor.querySelector("[data-sort]").value = "name"; editor.querySelector("[data-windows]").checked = false; editor.querySelector("[data-windows]").dispatchEvent(new Event("change", { bubbles: true })); }); });
  expect(result.room_filter).toEqual(["bathroom", "Küche"]); expect(result.visible_sections.slice(0, 2)).toEqual(["rooms", "operation"]); expect(result.sort).toBe("name"); expect(result.show_windows).toBeFalsy();
});

test("deduplicates read-only calls for two cards using the same entry", async ({ page }) => {
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); const second = document.createElement("smart-heating-card"); document.body.append(second); second.setConfig({ entry_id: "shared-entry" }); second.hass = window.hass; card.setConfig({ entry_id: "shared-entry" }); card.hass = window.hass; });
  await page.waitForTimeout(50); const entries = await page.evaluate(() => window.__calls.filter(call => call.entry_id === "shared-entry")); expect(entries).toHaveLength(1); expect(entries[0].type).toBe("smart_heating/plan/get");
});

test("refreshes only after a new HA state object and never writes", async ({ page }) => {
  const before = await page.evaluate(() => window.__calls.length);
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card.hass = { ...window.hass }; });
  await expect.poll(async () => page.evaluate(() => window.__calls.length)).toBeGreaterThan(before);
  const calls = await page.evaluate(() => window.__calls); expect(calls.every(call => call.type === "smart_heating/plan/get")).toBeTruthy();
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


test("beta46 renders responsive theme-aware rooms and collapsible special modes", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await expect(card.locator("section[data-section=rooms] .room-grid")).toBeVisible();
  await expect(card.locator("section[data-section=special_modes] details.expandable")).toHaveCount(1);
  await expect(card.locator("section[data-section=special_modes] .scroll-area")).toBeVisible();
  await expect(card.locator("section[data-section=diagnostics] details.expandable")).toHaveCount(1);
  await expect(card.locator("section[data-section=schedule] .day-row")).toHaveCount(7);
  const style = await card.locator("style[data-smart-heating-card-style]").textContent();
  expect(style).toContain("var(--primary-text-color)");
  expect(style).toContain("var(--card-background-color");
});

test("beta46 schedule hides seconds and duplicate weekday abbreviations", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await page.evaluate(() => {const card=document.querySelector("smart-heating-card");card._data.schedule.monday=[{start:"05:30:00",end:"21:00:00"}];card._render();});
  await expect(card.locator("[data-day=monday]")).toContainText("05:30–21:00");
  await expect(card.locator("[data-day=monday]")).not.toContainText("05:30:00");
  const shortDisplay = await card.locator("[data-day=monday] .day-short").evaluate(node=>getComputedStyle(node).display);
  expect(shortDisplay).toBe("none");
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
 await expect(card.locator("[data-room=ir]")).toContainText("Infrarot");
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
 await expect(card.locator("[data-room=ir]")).toContainText("Eingeschaltet");
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
