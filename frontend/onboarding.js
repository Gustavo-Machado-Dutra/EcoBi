(function (global) {
  "use strict";

  const VERSION = "1.0.0";
  const STORAGE_KEY = "ecobi.onboarding.v1";
  const modules = [
    ["view-dashboard", "Visão Executiva", "Acompanhe somente indicadores disponíveis no projeto e dataset selecionados."],
    ["view-projects", "Projetos", "Crie e selecione projetos locais para organizar análises."],
    ["view-import", "Importação", "Importe CSV ou XLSX e confira o perfil do dataset antes de analisar."],
    ["view-quality", "Qualidade e Schema", "Revise qualidade, mapeamento de colunas e dados acessíveis."],
    ["view-assistant", "Assistente IA local", "Consulte o assistente local; respostas analíticas continuam apoiadas pelos serviços determinísticos."],
    ["view-predictive", "Resultados Preditivos", "Consulte previsões, backtesting e métricas quando o histórico for suficiente."],
    ["view-simulator", "What-If", "Explore cenários com parâmetros validados sem alterar a fonte original."],
    ["view-validation", "Validação", "Revise pareceres e reconciliações antes de publicar resultados."],
    ["view-powerbi", "Power BI", "Gere e consulte artefatos locais elegíveis, preservando reconciliação."],
    ["view-audit", "Histórico e Auditoria", "Consulte eventos e trilhas registrados localmente."],
    ["view-multiproject", "Multiprojeto", "Compare somente métricas efetivamente disponíveis nos projetos."],
    ["view-scheduler", "Automações", "Gerencie rotinas locais e consulte status e histórico de execução."]
  ];
  const generalSteps = [
    { title: "EcoBI Intelligence", body: "Plataforma local para analisar dados corporativos sem enviar inferências a serviços externos.", target: '[data-tour="page-title"]' },
    { title: "Barra de contexto", body: "O título acompanha o módulo atual e os controles operacionais permanecem acessíveis.", target: '[data-tour="topbar"]' },
    { title: "Projeto ativo", body: "Selecione o projeto que organiza seu trabalho.", target: '[data-tour="project-selector"]' },
    { title: "Dataset ativo", body: "Escolha o conjunto de dados disponível no projeto selecionado.", target: '[data-tour="dataset-selector"]' },
    { title: "Navegação", body: "A barra lateral reúne os módulos por etapa do trabalho.", target: '[data-tour="sidebar"]' },
    { title: "Dashboard Executivo", body: modules[0][2], target: '[data-tour="module-view-dashboard"]', view: modules[0][0] },
    { title: "Importação", body: modules[2][2], target: '[data-tour="module-view-import"]', view: modules[2][0] },
    { title: "Qualidade e Schema", body: modules[3][2], target: '[data-tour="module-view-quality"]', view: modules[3][0] },
    { title: "Análises financeiras e ESG", body: "As análises usam os dados e filtros disponíveis e mantêm cálculos determinísticos.", target: '[data-tour="module-view-dashboard"]', view: modules[0][0] },
    { title: "Assistente IA local", body: modules[4][2], target: '[data-tour="module-view-assistant"]', view: modules[4][0] },
    { title: "Resultados Preditivos", body: modules[5][2], target: '[data-tour="module-view-predictive"]', view: modules[5][0] },
    { title: "Simulações What-If", body: modules[6][2], target: '[data-tour="module-view-simulator"]', view: modules[6][0] },
    { title: "Validação", body: modules[7][2], target: '[data-tour="module-view-validation"]', view: modules[7][0] },
    { title: "Power BI", body: modules[8][2], target: '[data-tour="module-view-powerbi"]', view: modules[8][0] },
    { title: "Histórico e Auditoria", body: modules[9][2], target: '[data-tour="module-view-audit"]', view: modules[9][0] },
    { title: "Multiprojeto", body: modules[10][2], target: '[data-tour="module-view-multiproject"]', view: modules[10][0] },
    { title: "Automações", body: modules[11][2], target: '[data-tour="module-view-scheduler"]', view: modules[11][0] },
    { title: "Governança e segurança", body: "O processamento permanece local, com controle de memória e trilha de auditoria.", target: '[data-tour="ram-indicator"]' }
  ];

  function normalizeState(storage, version = VERSION) {
    let saved = {};
    try { saved = JSON.parse(storage.getItem(STORAGE_KEY) || "{}"); } catch (_) { saved = {}; }
    return {
      version,
      introDismissed: saved.version === version && saved.introDismissed === true,
      completed: saved.version === version && saved.completed === true,
      progress: saved.version === version && Number.isInteger(saved.progress) && saved.progress >= 0 ? saved.progress : 0
    };
  }

  function createApi() {
    let viewSwitcher = null;
    let currentView = "view-dashboard";
    let state = null;
    let activeSteps = [];
    let activeIsGeneral = false;
    let currentStep = 0;
    let returnFocus = null;
    let introWasVisible = false;
    let introReturnFocus = null;
    let spot = null;
    let panel = null;
    let intro = null;
    let chooser = null;
    let resizeHandler = null;
    let inertBackground = new Map();

    function setBackgroundInert(active) {
      const root = document.getElementById("ecobi-onboarding");
      if (active) {
        if (inertBackground.size) return;
        Array.from(document.body.children).filter((element) => element !== root).forEach((element) => {
          inertBackground.set(element, element.inert);
          element.inert = true;
        });
        return;
      }
      inertBackground.forEach((wasInert, element) => { element.inert = wasInert; });
      inertBackground.clear();
    }

    function persist(patch = {}) {
      state = { ...state, ...patch, version: VERSION };
      try { global.localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (_) { /* Non-persistent storage remains usable. */ }
    }

    function buildUi() {
      const root = document.createElement("div");
      root.id = "ecobi-onboarding";
      root.innerHTML = '<div class="eco-tour-spotlight" hidden></div><section class="eco-tour-panel" role="dialog" aria-modal="false" aria-labelledby="eco-tour-title" aria-describedby="eco-tour-body" hidden><span class="eco-tour-progress"></span><h2 id="eco-tour-title"></h2><p id="eco-tour-body"></p><p class="eco-tour-recovery" aria-live="polite" hidden></p><div class="eco-tour-actions"><button type="button" data-action="back">Voltar</button><button type="button" data-action="skip-step">Pular etapa</button><button type="button" data-action="next">Avançar</button><button type="button" data-action="close">Encerrar</button></div></section><section class="eco-tour-intro" role="dialog" aria-modal="false" aria-labelledby="eco-intro-title" aria-describedby="eco-intro-body" hidden><h2 id="eco-intro-title">Bem-vindo ao EcoBI Intelligence</h2><p id="eco-intro-body">Conheça a plataforma, entenda seus módulos e aprenda a transformar seus dados em informações estratégicas.</p><div class="eco-tour-actions"><button type="button" data-action="start">Começar tutorial</button><button type="button" data-action="defer">Fazer depois</button><button type="button" data-action="dismiss">Pular apresentação</button></div></section><section class="eco-tour-chooser" role="dialog" aria-modal="true" aria-labelledby="eco-help-title" hidden><h2 id="eco-help-title">Ajuda e tutorial</h2><p>Escolha uma apresentação.</p><div class="eco-tour-actions"><button type="button" data-action="general-help">Tour geral</button><button type="button" data-action="context-help">Guia deste módulo</button><button type="button" data-action="help-close">Fechar</button></div></section>';
      document.body.appendChild(root);
      spot = root.querySelector(".eco-tour-spotlight");
      panel = root.querySelector(".eco-tour-panel");
      intro = root.querySelector(".eco-tour-intro");
      chooser = root.querySelector(".eco-tour-chooser");
      root.addEventListener("click", onAction);
      document.addEventListener("keydown", onKeyDown);
      resizeHandler = () => positionCurrent();
      global.addEventListener("resize", resizeHandler);
      global.addEventListener("scroll", resizeHandler, true);
    }

    function init(options = {}) {
      if (typeof document === "undefined" || document.getElementById("ecobi-onboarding")) return;
      viewSwitcher = options.switchView || null;
      currentView = options.currentView || "view-dashboard";
      state = normalizeState(global.localStorage);
      buildUi();
      document.querySelectorAll("#btn-open-onboarding, #btn-open-onboarding-sidebar").forEach((button) => button.addEventListener("click", openHelp));
      if (!state.introDismissed) { returnFocus = document.activeElement; intro.hidden = false; intro.querySelector('[data-action="start"]').focus({ preventScroll: true }); }
    }

    function openHelp() {
      if (!panel) return;
      introWasVisible = intro && !intro.hidden;
      introReturnFocus = introWasVisible ? returnFocus : null;
      returnFocus = document.activeElement;
      if (introWasVisible) intro.hidden = true;
      setBackgroundInert(true);
      chooser.hidden = false;
      chooser.querySelector('[data-action="general-help"]').focus({ preventScroll: true });
    }

    function closeHelp() {
      const restoreIntro = introWasVisible;
      chooser.hidden = true;
      setBackgroundInert(false);
      if (restoreIntro) intro.hidden = false;
      introWasVisible = false;
      if (returnFocus && returnFocus.isConnected) returnFocus.focus({ preventScroll: true });
      returnFocus = restoreIntro ? introReturnFocus : null;
      introReturnFocus = null;
    }

    function startContext(viewId) {
      const module = modules.find((item) => item[0] === viewId) || modules[0];
      start([{ title: module[1], body: module[2], target: `[data-tour="module-${module[0]}"]`, view: module[0] }]);
    }

    function start(steps = generalSteps) {
      if (!panel) return;
      intro.hidden = true;
      returnFocus = returnFocus || document.activeElement;
      activeSteps = steps.slice();
      activeIsGeneral = steps === generalSteps;
      currentStep = steps === generalSteps ? Math.min(state.progress, steps.length - 1) : 0;
      renderCurrent();
    }

    function renderCurrent() {
      if (!activeSteps.length) return closeTour();
      const step = activeSteps[currentStep];
      if (step.view && step.view !== currentView && viewSwitcher) {
        currentView = step.view;
        viewSwitcher(step.view);
      }
      global.requestAnimationFrame(() => {
        panel.hidden = false;
        panel.querySelector(".eco-tour-progress").textContent = `Etapa ${currentStep + 1} de ${activeSteps.length}`;
        panel.querySelector("#eco-tour-title").textContent = step.title;
        panel.querySelector("#eco-tour-body").textContent = step.body;
        panel.querySelector('[data-action="back"]').disabled = currentStep === 0;
        panel.querySelector('[data-action="next"]').textContent = currentStep === activeSteps.length - 1 ? "Concluir" : "Avan\u00e7ar";
        const target = document.querySelector(step.target);
        const visible = target && target.getClientRects().length && getComputedStyle(target).visibility !== "hidden";
        const recovery = panel.querySelector(".eco-tour-recovery");
        if (!visible || !positionTarget(target)) {
          spot.hidden = true;
          panel.style.top = "50%";
          panel.style.left = "50%";
          panel.style.transform = "translate(-50%, -50%)";
          panel.dataset.placement = "center";
          recovery.hidden = false;
          recovery.textContent = "Este destaque não está disponível neste momento. Você pode pular a etapa ou encerrar o tutorial.";
        } else {
          target.scrollIntoView({ block: "center", inline: "nearest", behavior: global.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
          positionTarget(target);
          recovery.hidden = true;
        }
        panel.querySelector('[data-action="next"]').focus({ preventScroll: true });
      });
    }

    function positionTarget(target) {
      if (!target) return false;
      const rect = target.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      const pad = 6;
      const spotLeft = Math.max(0, Math.min(global.innerWidth - pad, rect.left - pad));
      const spotTop = Math.max(0, Math.min(global.innerHeight - pad, rect.top - pad));
      spot.style.left = `${spotLeft}px`;
      spot.style.top = `${spotTop}px`;
      spot.style.width = `${Math.max(0, Math.min(global.innerWidth, rect.right + pad) - spotLeft)}px`;
      spot.style.height = `${Math.max(0, Math.min(global.innerHeight, rect.bottom + pad) - spotTop)}px`;
      spot.hidden = false;
      panel.style.transform = "none";
      const panelRect = panel.getBoundingClientRect();
      const left = Math.max(12, Math.min(global.innerWidth - panelRect.width - 12, rect.left));
      const below = rect.bottom + panelRect.height + 16 < global.innerHeight;
      const desiredTop = below ? rect.bottom + 12 : rect.top - panelRect.height - 12;
      const maxTop = Math.max(12, global.innerHeight - panelRect.height - 12);
      const top = Math.max(12, Math.min(maxTop, desiredTop));
      panel.style.left = `${left}px`;
      panel.style.top = `${top}px`;
      panel.dataset.placement = below ? "below" : "above";
      return true;
    }

    function positionCurrent() {
      if (panel && !panel.hidden && activeSteps[currentStep]) positionTarget(document.querySelector(activeSteps[currentStep].target));
    }

    function onAction(event) {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const action = button.dataset.action;
      if (action === "start") { persist({ progress: 0 }); start(generalSteps); }
      else if (action === "general-help") { chooser.hidden = true; setBackgroundInert(false); introWasVisible = false; start(generalSteps); }
      else if (action === "context-help") { chooser.hidden = true; setBackgroundInert(false); introWasVisible = false; startContext(currentView); }
      else if (action === "help-close") closeHelp();
      else if (action === "defer") { intro.hidden = true; if (returnFocus && returnFocus.isConnected) returnFocus.focus({ preventScroll: true }); returnFocus = null; }
      else if (action === "dismiss") { persist({ introDismissed: true }); intro.hidden = true; if (returnFocus && returnFocus.isConnected) returnFocus.focus({ preventScroll: true }); returnFocus = null; }
      else if (action === "back") { currentStep = Math.max(0, currentStep - 1); persist({ progress: currentStep }); renderCurrent(); }
      else if (action === "next" || action === "skip-step") {
        if (currentStep < activeSteps.length - 1) { currentStep += 1; persist({ progress: currentStep }); renderCurrent(); }
        else { if (activeIsGeneral) persist({ introDismissed: true, completed: true, progress: 0 }); closeTour(); }
      } else if (action === "close") closeTour();
    }

    function closeTour() {
      if (panel) panel.hidden = true;
      if (spot) spot.hidden = true;
      activeSteps = [];
      const focused = returnFocus;
      returnFocus = null;
      if (focused && focused.isConnected) focused.focus({ preventScroll: true });
    }

    function onKeyDown(event) {
      if (event.key === "Escape") {
        if (chooser && !chooser.hidden) {
          closeHelp();
          return;
        } else if (intro && !intro.hidden) {
          intro.hidden = true;
          if (returnFocus && returnFocus.isConnected) returnFocus.focus({ preventScroll: true });
          returnFocus = null;
        }
        closeTour();
        return;
      }
      if (event.key !== "Tab") return;
      const dialog = chooser && !chooser.hidden ? chooser : null;
      if (!dialog) return;
      const controls = Array.from(dialog.querySelectorAll("button:not([disabled])"));
      if (controls.length && !controls.includes(document.activeElement)) {
        event.preventDefault();
        controls[event.shiftKey ? controls.length - 1 : 0].focus();
        return;
      }
      if (controls.length && event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls[controls.length - 1].focus(); }
      else if (controls.length && !event.shiftKey && document.activeElement === controls[controls.length - 1]) { event.preventDefault(); controls[0].focus(); }
    }
    function destroy() {
      setBackgroundInert(false);
      const root = document.getElementById("ecobi-onboarding");
      if (root) root.remove();
      document.removeEventListener("keydown", onKeyDown);
      global.removeEventListener("resize", resizeHandler);
      global.removeEventListener("scroll", resizeHandler, true);
      spot = panel = intro = chooser = null;
    }

    return { init, openHelp, startGeneral: () => start(generalSteps), startContext, setCurrentView: (viewId) => { currentView = viewId; }, close: closeTour, getGeneralSteps: () => generalSteps.map((step) => ({ ...step })), getModules: () => modules.map(([id, title, body]) => ({ id, title, body })), normalizeState, destroy, version: VERSION };
  }

  const api = createApi();
  global.EcoBIOnboarding = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
