const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const onboarding = require("../../frontend/onboarding.js");
function loadRealSwitchView(onboarding, document, localStorage, requests) {
  const appSource = fs.readFileSync("frontend/app.js", "utf8");
  const bootstrap = '  if (document.readyState === "loading") {';
  assert.equal(appSource.split(bootstrap).length - 1, 1);
  const instrumented = appSource.replace(bootstrap, "  globalThis.__testSwitchView = switchView;\n" + bootstrap);
  const context = {
    document,
    localStorage,
    window: { EcoBIOnboarding: onboarding },
    fetch: async (url, options = {}) => {
      requests.push({ url, method: (options.method || "GET").toUpperCase() });
      return { status: 200, ok: true, headers: { get: () => "application/json" }, json: async () => ({}), text: async () => "" };
    },
    FormData: class FormData {}
  };
  vm.runInNewContext(instrumented, context, { filename: "frontend/app.js" });
  return context.__testSwitchView;
}

test("general guide covers all 18 documented topics and module targets", () => {
  const steps = onboarding.getGeneralSteps();
  const expectedTitles = JSON.parse("[\"EcoBI Intelligence\",\"Barra de contexto\",\"Projeto ativo\",\"Dataset ativo\",\"Navega\u00e7\u00e3o\",\"Dashboard Executivo\",\"Importa\u00e7\u00e3o\",\"Qualidade e Schema\",\"An\u00e1lises financeiras e ESG\",\"Assistente IA local\",\"Resultados Preditivos\",\"Simula\u00e7\u00f5es What-If\",\"Valida\u00e7\u00e3o\",\"Power BI\",\"Hist\u00f3rico e Auditoria\",\"Multiprojeto\",\"Automa\u00e7\u00f5es\",\"Governan\u00e7a e seguran\u00e7a\"]");
  assert.deepEqual(steps.map((step) => step.title), expectedTitles);
  assert.deepEqual(steps.slice(5, 8).map((step) => step.view), ["view-dashboard", "view-import", "view-quality"]);
  assert.ok(steps.every((step) => step.chapter && step.body && step.body.length <= 145 && step.target.startsWith("[data-tour=\"")));
  assert.ok(steps.every((step) => !step.target.includes("module-view-")));
  const shell = fs.readFileSync("frontend/index.html", "utf8");
  for (const step of steps) {
    assert.ok(shell.includes(step.target.slice(1, -1)), `Missing target ${step.target}`);
    if (step.fallbackTarget) assert.ok(shell.includes(step.fallbackTarget.slice(1, -1)), `Missing fallback ${step.fallbackTarget}`);
  }
});

test("contextual guides cover all twelve existing views", () => {
  const modules = onboarding.getModules();
  assert.equal(modules.length, 12);
  assert.equal(new Set(modules.map((module) => module.id)).size, 12);
  assert.ok(modules.every((module) => module.id.startsWith("view-") && module.title && module.body));
  const shell = fs.readFileSync("frontend/index.html", "utf8");
  for (const module of modules) {
    assert.ok(shell.includes(`data-tour=\"module-${module.id}\"`));
    const steps = onboarding.getContextualSteps(module.id);
    assert.ok(steps.length >= 2, `Expected multi-step guide for ${module.id}`);
    for (const step of steps) {
      assert.equal(step.view, module.id);
      assert.ok(step.chapter && step.title && step.body && step.body.length <= 145);
      assert.ok(!step.target.includes("module-view-"), `Avoid full-section target ${step.target}`);
      assert.ok(shell.includes(step.target.slice(1, -1)), `Missing contextual target ${step.target}`);
    }
  }
});

test("stored onboarding preferences are versioned and non-sensitive", () => {
  const values = new Map([["ecobi.onboarding.v1", JSON.stringify({ version: "1.0.0", introDismissed: true, completed: true, progress: 3, prompt: "secret" })]]);
  const state = onboarding.normalizeState({ getItem: (key) => values.get(key) || null });
  assert.deepEqual(state, { version: "1.0.0", introDismissed: true, completed: true, progress: 3 });
  assert.deepEqual(onboarding.normalizeState({ getItem: () => "invalid" }), { version: "1.0.0", introDismissed: false, completed: false, progress: 0 });
  assert.deepEqual(onboarding.normalizeState({ getItem: () => JSON.stringify({ version: "0.9", introDismissed: true, progress: 9 }) }), { version: "1.0.0", introDismissed: false, completed: false, progress: 0 });
});

test("welcome and tour preserve non-modal keyboard navigation while help remains modal", () => {
  const saved = Object.fromEntries(["document", "localStorage", "addEventListener", "removeEventListener"].map((key) => [key, Object.getOwnPropertyDescriptor(global, key)]));
  const handlers = new Map();
  const rootHandlers = new Map();
  let root;
  const document = { activeElement: null };
  const makeButton = () => ({ isConnected: true, focus() { document.activeElement = this; } });
  const introButtons = [makeButton(), makeButton(), makeButton()];
  const intro = {
    hidden: true,
    querySelector(selector) { return selector.includes('"start"') ? introButtons[0] : null; },
    querySelectorAll() { return introButtons; }
  };
  const tourButtons = [makeButton(), makeButton()];
  const panel = { hidden: true, querySelectorAll() { return tourButtons; } };
  const helpButtons = [makeButton(), makeButton(), makeButton()];
  const chooser = {
    hidden: true,
    querySelector(selector) { return selector.includes("general-help") ? helpButtons[0] : null; },
    querySelectorAll() { return helpButtons; }
  };
  const spot = { hidden: true };
  const appShell = { inert: false };
  const opener = makeButton();
  document.activeElement = opener;
  const elements = {
    ".eco-tour-spotlight": spot,
    ".eco-tour-panel": panel,
    ".eco-tour-intro": intro,
    ".eco-tour-chooser": chooser
  };
  const rootElement = {
    id: "ecobi-onboarding",
    set innerHTML(_value) {},
    querySelector(selector) { return elements[selector]; },
    addEventListener(type, handler) { rootHandlers.set(type, handler); },
    remove() { root = null; document.body.children = document.body.children.filter((child) => child !== rootElement); }
  };
  Object.assign(document, {
    body: { children: [appShell], appendChild(element) { root = element; this.children.push(element); } },
    createElement() { return rootElement; },
    getElementById(id) { return root && id === root.id ? root : null; },
    querySelectorAll() { return []; },
    addEventListener(type, handler) { handlers.set(type, handler); },
    removeEventListener() {}
  });
  global.document = document;
  const stored = new Map();
  global.localStorage = { getItem(key) { return stored.get(key) || null; }, setItem(key, value) { stored.set(key, value); } };
  global.addEventListener = () => {};
  global.removeEventListener = () => {};

  try {
    onboarding.init();
    const fire = (action) => rootHandlers.get("click")({ target: { closest: () => ({ dataset: { action } }) } });
    assert.equal(intro.hidden, false);
    assert.equal(document.activeElement, introButtons[0]);

    onboarding.openHelp();
    assert.equal(intro.hidden, true);
    assert.equal(chooser.hidden, false);
    assert.equal(appShell.inert, true);
    handlers.get("keydown")({ key: "Escape" });
    assert.equal(chooser.hidden, true);
    assert.equal(intro.hidden, false);
    assert.equal(appShell.inert, false);
    assert.equal(document.activeElement, introButtons[0]);

    document.activeElement = introButtons[2];
    let prevented = false;
    handlers.get("keydown")({ key: "Tab", shiftKey: false, preventDefault() { prevented = true; } });
    assert.equal(prevented, false);
    assert.equal(document.activeElement, introButtons[2]);

    document.activeElement = introButtons[0];
    prevented = false;
    handlers.get("keydown")({ key: "Tab", shiftKey: true, preventDefault() { prevented = true; } });
    assert.equal(prevented, false);
    assert.equal(document.activeElement, introButtons[0]);

    handlers.get("keydown")({ key: "Escape" });
    assert.equal(intro.hidden, true);
    assert.equal(document.activeElement, opener);
    onboarding.destroy();
    onboarding.init();
    assert.equal(intro.hidden, false);

    fire("defer");
    assert.equal(intro.hidden, true);
    assert.equal(stored.size, 0);
    onboarding.destroy();
    onboarding.init();
    assert.equal(intro.hidden, false);

    fire("dismiss");
    assert.equal(intro.hidden, true);
    assert.equal(JSON.parse(stored.get("ecobi.onboarding.v1")).introDismissed, true);
    onboarding.destroy();
    onboarding.init();
    assert.equal(intro.hidden, true);

    onboarding.openHelp();
    assert.equal(chooser.hidden, false);
    assert.equal(appShell.inert, true);
    assert.equal(document.activeElement, helpButtons[0]);

    document.activeElement = opener;
    prevented = false;
    handlers.get("keydown")({ key: "Tab", shiftKey: false, preventDefault() { prevented = true; } });
    assert.equal(prevented, true);
    assert.equal(document.activeElement, helpButtons[0]);

    handlers.get("keydown")({ key: "Escape" });
    assert.equal(chooser.hidden, true);
    assert.equal(appShell.inert, false);
    assert.equal(document.activeElement, opener);

    panel.hidden = false;
    document.activeElement = opener;
    prevented = false;
    handlers.get("keydown")({ key: "Tab", shiftKey: false, preventDefault() { prevented = true; } });
    assert.equal(prevented, false);
    assert.equal(document.activeElement, opener);
    panel.hidden = true;
  } finally {
    onboarding.destroy();
    for (const [key, descriptor] of Object.entries(saved)) {
      if (descriptor) Object.defineProperty(global, key, descriptor);
      else delete global[key];
    }
  }
});

test("tour spotlight and panel remain within the viewport after resize", () => {
  const saved = Object.fromEntries(["document", "localStorage", "addEventListener", "removeEventListener", "requestAnimationFrame", "innerWidth", "innerHeight", "matchMedia", "getComputedStyle", "setTimeout", "clearTimeout"].map((key) => [key, Object.getOwnPropertyDescriptor(global, key)]));
  const handlers = new Map();
  const document = { activeElement: null };
  let root;
  let panelMeasuredWhileHidden = false;
  let targetAvailable = true;
  let panelHeight = 228;
  const focusable = () => ({ focus() { document.activeElement = this; } });
  const introButton = focusable();
  const intro = { hidden: true, querySelector() { return introButton; }, querySelectorAll() { return [introButton]; } };
  const recovery = { hidden: true, textContent: "" };
  const progress = { textContent: "" };
  const title = { textContent: "" };
  const body = { textContent: "" };
  const back = { disabled: false };
  const next = focusable();
  const panelElements = { ".eco-tour-recovery": recovery, ".eco-tour-progress": progress, "#eco-tour-title": title, "#eco-tour-body": body, '[data-action="back"]': back, '[data-action="next"]': next };
  const panel = {
    hidden: true,
    style: {
      setProperty(name, value) { this[name] = value; },
      removeProperty(name) { delete this[name]; }
    },
    dataset: {},
    querySelector(selector) { return panelElements[selector]; },
    querySelectorAll() { return []; },
    getBoundingClientRect() {
      panelMeasuredWhileHidden ||= this.hidden;
      return this.hidden ? { width: 0, height: 0 } : { width: 300, height: panelHeight };
    }
  };
  const backdropAttrs = new Map();
  const backdrop = { hidden: true, setAttribute(name, value) { backdropAttrs.set(name, value); } };
  const cutoutAttrs = new Map();
  const cutoutHole = { setAttribute(name, value) { cutoutAttrs.set(name, value); } };
  const spot = { hidden: true, style: {} };
  const chooser = { hidden: true, querySelector() { return focusable(); }, querySelectorAll() { return []; } };
  let targetRect = { left: 50, top: 80, right: 170, bottom: 110, width: 120, height: 30 };
  const target = {
    getClientRects() { return [{}]; },
    getBoundingClientRect() { return targetRect; },
    scrollIntoView() {}
  };
  const elements = {
    ".eco-tour-backdrop": backdrop,
    "#eco-tour-cutout-hole": cutoutHole,
    ".eco-tour-spotlight": spot,
    ".eco-tour-panel": panel,
    ".eco-tour-intro": intro,
    ".eco-tour-chooser": chooser
  };
  const appShell = { inert: false };
  const rootElement = {
    id: "ecobi-onboarding",
    set innerHTML(_value) {},
    querySelector(selector) { return elements[selector]; },
    addEventListener() {},
    remove() { root = null; document.body.children = document.body.children.filter((child) => child !== rootElement); }
  };
  Object.assign(document, {
    body: { children: [appShell], appendChild(element) { root = element; this.children.push(element); } },
    createElement() { return rootElement; },
    getElementById(id) { return root && id === root.id ? root : null; },
    querySelectorAll() { return []; },
    querySelector() { return targetAvailable ? target : null; },
    addEventListener(type, handler) { handlers.set(type, handler); },
    removeEventListener() {}
  });
  global.document = document;
  global.localStorage = { getItem() { return JSON.stringify({ version: "1.0.0", introDismissed: true }); }, setItem() {} };
  global.addEventListener = (type, handler) => handlers.set(`global:${type}`, handler);
  global.removeEventListener = () => {};
  global.requestAnimationFrame = (callback) => callback();
  global.setTimeout = () => 1;
  global.clearTimeout = () => {};
  global.innerWidth = 390;
  global.innerHeight = 844;
  global.matchMedia = () => ({ matches: false });
  global.getComputedStyle = () => ({ visibility: "visible" });

  try {
    onboarding.init();
    onboarding.startGeneral();
    assert.equal(panelMeasuredWhileHidden, false);
    assert.equal(panel.dataset.placement, "bottom");
    assert.equal(backdrop.hidden, false);
    assert.equal(spot.hidden, false);
    assert.equal(cutoutAttrs.get("x"), "44");
    assert.equal(cutoutAttrs.get("y"), "74");
    assert.equal(cutoutAttrs.get("width"), "132");
    assert.equal(cutoutAttrs.get("height"), "42");
    assert.equal(panel.style.top, "130px");
    assert.equal(document.activeElement, next);

    // Near bottom edge -> switches to top without overlapping spotlight
    targetRect = { left: 310, top: 760, right: 380, bottom: 800, width: 70, height: 40 };
    handlers.get("global:resize")();
    assert.equal(panel.dataset.placement, "top");
    const topPos = Number.parseInt(panel.style.top, 10);
    const leftPos = Number.parseInt(panel.style.left, 10);
    assert.equal(
      onboarding.rectsIntersect(
        { left: leftPos, top: topPos, right: leftPos + 300, bottom: topPos + panelHeight },
        { left: 304, top: 754, right: 386, bottom: 806 }
      ),
      false
    );

    // Tall sidebar on desktop -> places tooltip to the right without overlapping
    global.innerWidth = 1280;
    global.innerHeight = 800;
    targetRect = { left: 0, top: 0, right: 260, bottom: 800, width: 260, height: 800 };
    handlers.get("global:resize")();
    assert.equal(panel.dataset.placement, "right");
    assert.ok(Number.parseInt(panel.style.left, 10) >= 266 + 14);

    // Tall target on right edge -> places tooltip to the left without overlapping
    targetRect = { left: 960, top: 60, right: 1260, bottom: 760, width: 300, height: 700 };
    handlers.get("global:resize")();
    assert.equal(panel.dataset.placement, "left");
    assert.ok(Number.parseInt(panel.style.left, 10) + 300 <= 954 - 14);

    // Viewport too tight to avoid overlap -> centered fallback hides spotlight instead of overlapping
    global.innerWidth = 390;
    global.innerHeight = 220;
    panelHeight = 200;
    targetRect = { left: 0, top: 40, right: 390, bottom: 180, width: 390, height: 140 };
    handlers.get("global:resize")();
    assert.equal(panel.dataset.placement, "center");
    assert.equal(spot.hidden, true);

    // CSS contract: no vertical scrollbar, fixed height, no 9999px shadow dimming spotlight, single-row footer
    const styles = fs.readFileSync("frontend/styles.css", "utf8");
    assert.doesNotMatch(styles, /\.eco-tour-panel\s*\{[^}]*overflow-y:\s*auto/);
    assert.doesNotMatch(styles, /\.eco-tour-panel\s*\{[^}]*9999px/);
    assert.doesNotMatch(styles, /\.eco-tour-spotlight\s*\{[^}]*9999px/);
    assert.match(styles, /\.eco-tour-backdrop-fill\s*\{[^}]*fill:/);
    assert.match(styles, /\.eco-tour-panel\s*\{[^}]*height:\s*228px/);
    assert.match(styles, /\.eco-tour-actions\s*\{[^}]*flex-wrap:\s*nowrap/);

    targetAvailable = false;
    onboarding.startContext("view-dashboard");
    assert.equal(panel.dataset.placement, "center");
    assert.equal(recovery.hidden, false);
  } finally {
    onboarding.destroy();
    for (const [key, descriptor] of Object.entries(saved)) {
      if (descriptor) Object.defineProperty(global, key, descriptor);
      else delete global[key];
    }
  }
});

test("general tour controls navigate only existing views, issue no controller-owned fetches, and persist completion", () => {
  const globalKeys = ["document", "localStorage", "addEventListener", "removeEventListener", "requestAnimationFrame", "innerWidth", "innerHeight", "matchMedia", "getComputedStyle", "fetch"];
  const savedGlobals = Object.fromEntries(globalKeys.map((key) => [key, Object.getOwnPropertyDescriptor(global, key)]));
  const documentHandlers = new Map();
  const rootHandlers = new Map();
  const stored = new Map([["ecobi.onboarding.v1", JSON.stringify({ version: "1.0.0", introDismissed: true, progress: 0 })]]);
  const views = [];
  let activeView = "view-dashboard";
  let fetchCalls = 0;
  let root;
  const document = { activeElement: null };
  const makeButton = () => ({ disabled: false, isConnected: true, focus() { document.activeElement = this; } });
  const introButton = makeButton();
  const intro = { hidden: true, querySelector() { return introButton; }, querySelectorAll() { return [introButton]; } };
  const recovery = { hidden: true, textContent: "" };
  const progress = { textContent: "" };
  const title = { textContent: "" };
  const body = { textContent: "" };
  const back = makeButton();
  const next = makeButton();
  const panelNodes = { ".eco-tour-recovery": recovery, ".eco-tour-progress": progress, "#eco-tour-title": title, "#eco-tour-body": body, '[data-action="back"]': back, '[data-action="next"]': next };
  const panel = {
    hidden: true,
    style: {},
    dataset: {},
    querySelector(selector) { return panelNodes[selector]; },
    querySelectorAll() { return []; },
    getBoundingClientRect() { return { width: 280, height: 100 }; }
  };
  const spot = { hidden: true, style: {} };
  const chooser = { hidden: true, querySelector() { return makeButton(); }, querySelectorAll() { return []; } };
  const target = {
    getClientRects() { return [{}]; },
    getBoundingClientRect() { return { left: 40, top: 60, right: 160, bottom: 90, width: 120, height: 30 }; },
    scrollIntoView() {}
  };
  const elements = { ".eco-tour-spotlight": spot, ".eco-tour-panel": panel, ".eco-tour-intro": intro, ".eco-tour-chooser": chooser };
  const rootElement = {
    id: "ecobi-onboarding",
    set innerHTML(_value) {},
    querySelector(selector) { return elements[selector]; },
    addEventListener(type, handler) { rootHandlers.set(type, handler); },
    remove() { root = null; document.body.children = document.body.children.filter((child) => child !== rootElement); }
  };
  Object.assign(document, {
    body: { children: [], appendChild(element) { root = element; this.children.push(element); } },
    createElement() { return rootElement; },
    getElementById(id) { return root && id === root.id ? root : null; },
    querySelectorAll() { return []; },
    querySelector() { return target; },
    addEventListener(type, handler) { documentHandlers.set(type, handler); },
    removeEventListener() {}
  });
  global.document = document;
  global.localStorage = { getItem(key) { return stored.get(key) || null; }, setItem(key, value) { stored.set(key, value); } };
  global.addEventListener = () => {};
  global.removeEventListener = () => {};
  global.requestAnimationFrame = (callback) => callback();
  global.innerWidth = 1280;
  global.innerHeight = 800;
  global.matchMedia = () => ({ matches: true });
  global.getComputedStyle = () => ({ visibility: "visible" });
  global.fetch = () => { fetchCalls += 1; throw new Error("Tour must not call application APIs"); };

  try {
    onboarding.init({ currentView: activeView, switchView(viewId) { activeView = viewId; views.push(viewId); } });
    const click = (action) => rootHandlers.get("click")({ target: { closest: () => ({ dataset: { action } }) } });
    onboarding.startGeneral();
    click("next");
    click("back");
    click("skip-step");
    assert.equal(JSON.parse(stored.get("ecobi.onboarding.v1")).progress, 1);
    click("close");
    assert.equal(panel.hidden, true);

    onboarding.startGeneral();
    for (let index = 0; index < 4; index += 1) click("next");
    assert.equal(activeView, "view-dashboard");
    click("next");
    assert.equal(activeView, "view-import");
    click("close");
    assert.equal(activeView, "view-import");
    assert.deepEqual(views, ["view-import"]);
    assert.ok(views.every((viewId) => onboarding.getModules().some((module) => module.id === viewId)));
    assert.equal(fetchCalls, 0);

    onboarding.startGeneral();
    for (let index = 6; index < 17; index += 1) click("next");
    click("next");
    assert.equal(panel.hidden, true);
    assert.deepEqual(JSON.parse(stored.get("ecobi.onboarding.v1")), { version: "1.0.0", introDismissed: true, completed: true, progress: 0 });
    onboarding.startContext("view-assistant");
    click("next");
    click("back");
    click("next");
    click("next");
    click("next");
    assert.deepEqual(JSON.parse(stored.get("ecobi.onboarding.v1")), { version: "1.0.0", introDismissed: true, completed: true, progress: 0 });
  } finally {
    onboarding.destroy();
    for (const [key, descriptor] of Object.entries(savedGlobals)) {
      if (descriptor) Object.defineProperty(global, key, descriptor);
      else delete global[key];
    }
  }
});

test("general tour uses real navigation without business writes or project changes", async () => {
  const savedGlobals = Object.fromEntries(["document", "localStorage", "addEventListener", "removeEventListener", "requestAnimationFrame", "innerWidth", "innerHeight", "matchMedia", "getComputedStyle"].map((key) => [key, Object.getOwnPropertyDescriptor(global, key)]));
  const rootHandlers = new Map();
  const stored = new Map([["ecobi.onboarding.v1", JSON.stringify({ version: "1.0.0", introDismissed: true, progress: 0 })]]);
  const writes = [];
  const requests = [];
  let activeView = "view-dashboard";
  const visitedViews = [];
  const makeNode = (id = "") => {
    const classes = new Set();
    const attributes = new Map();
    return {
      id, hidden: true,
      classList: {
        add: (name) => classes.add(name), remove: (name) => classes.delete(name), contains: (name) => classes.has(name),
        toggle(name, force) { if (force ?? !classes.has(name)) classes.add(name); else classes.delete(name); }
      },
      setAttribute: (name, value) => attributes.set(name, value), removeAttribute: (name) => attributes.delete(name),
      getAttribute: (name) => attributes.get(name),
      querySelector(selector) { return selector === "h1" ? { textContent: id } : null; }
    };
  };
  const views = onboarding.getModules().map((module) => makeNode(module.id));
  const navItems = onboarding.getModules().map((module) => {
    const node = makeNode();
    node.getAttribute = (name) => name === "data-view" ? module.id : null;
    return node;
  });
  const title = { textContent: "" };
  const sidebar = makeNode("app-sidebar");
  const makeButton = () => ({ disabled: false, isConnected: true, focus() {}, setAttribute() {} });
  const intro = { hidden: true, querySelector: () => makeButton(), querySelectorAll: () => [] };
  const recovery = { hidden: true, textContent: "" };
  const panelNodes = {
    ".eco-tour-recovery": recovery, ".eco-tour-progress": { textContent: "" },
    "#eco-tour-title": { textContent: "" }, "#eco-tour-body": { textContent: "" },
    '[data-action="back"]': makeButton(), '[data-action="next"]': makeButton()
  };
  const panel = { hidden: true, style: {}, dataset: {}, querySelector: (selector) => panelNodes[selector], querySelectorAll: () => [], getBoundingClientRect: () => ({ width: 280, height: 100 }) };
  const spot = { hidden: true, style: {} };
  const chooser = { hidden: true, querySelector: () => makeButton(), querySelectorAll: () => [] };
  const target = { getClientRects: () => [{}], getBoundingClientRect: () => ({ left: 40, top: 60, right: 160, bottom: 90, width: 120, height: 30 }), scrollIntoView() {} };
  const elements = { ".eco-tour-spotlight": spot, ".eco-tour-panel": panel, ".eco-tour-intro": intro, ".eco-tour-chooser": chooser };
  let root;
  const appDocument = {
    readyState: "loading", documentElement: makeNode("html"),
    body: { children: [], appendChild(element) { root = element; this.children.push(element); } },
    createElement: () => ({ id: "ecobi-onboarding", set innerHTML(_value) {}, querySelector: (selector) => elements[selector], addEventListener: (type, handler) => rootHandlers.set(type, handler), remove() { root = null; } }),
    getElementById(id) { if (id === "topbar-page-title") return title; if (id === "app-sidebar") return sidebar; return views.find((view) => view.id === id) || null; },
    querySelectorAll(selector) { return selector === ".view-section" ? views : selector === ".nav-item[data-view]" ? navItems : []; },
    querySelector: (selector) => selector.startsWith(".workflow-step-btn") ? null : target, addEventListener() {}, removeEventListener() {}
  };
  const localStorage = { getItem: (key) => stored.get(key) || null, setItem(key, value) { writes.push(key); stored.set(key, value); } };
  global.document = appDocument;
  global.localStorage = localStorage;
  global.addEventListener = () => {};
  global.removeEventListener = () => {};
  global.requestAnimationFrame = (callback) => callback();
  global.innerWidth = 1280;
  global.innerHeight = 800;
  global.matchMedia = () => ({ matches: true });
  global.getComputedStyle = () => ({ visibility: "visible" });

  try {
    const realSwitchView = loadRealSwitchView(onboarding, appDocument, localStorage, requests);
    onboarding.init({ currentView: activeView, switchView(viewId) { activeView = viewId; visitedViews.push(viewId); realSwitchView(viewId); } });
    const clickNext = () => rootHandlers.get("click")({ target: { closest: () => ({ dataset: { action: "next" } }) } });
    onboarding.startGeneral();
    for (let index = 1; index < onboarding.getGeneralSteps().length; index += 1) clickNext();
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(activeView, "view-scheduler");
    assert.equal(views.find((view) => view.id === activeView).hidden, false);
    assert.ok(visitedViews.includes("view-import"));
    assert.ok(visitedViews.includes("view-quality"));
    assert.ok(requests.length > 0);
    assert.ok(requests.every((request) => request.method === "GET"), JSON.stringify(requests));
    assert.ok(writes.every((key) => key === "ecobi.onboarding.v1"), JSON.stringify(writes));
    assert.equal(stored.has("ecobi_active_project_id"), false);
    assert.equal(stored.has("ecobi_active_dataset_id"), false);
  } finally {
    onboarding.destroy();
    for (const [key, descriptor] of Object.entries(savedGlobals)) {
      if (descriptor) Object.defineProperty(global, key, descriptor); else delete global[key];
    }
  }
});