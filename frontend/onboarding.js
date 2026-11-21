(function (global) {
  "use strict";

  const VERSION = "1.0.0";
  const STORAGE_KEY = "ecobi.onboarding.v1";
  const SPOTLIGHT_PAD = 6;
  const TOOLTIP_GAP = 14;
  const VIEWPORT_MARGIN = 12;
  const ARROW_EDGE_PAD = 28;

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
    { chapter: "Vis\u00e3o Geral", title: "EcoBI Intelligence", body: "Plataforma local para analisar dados corporativos sem enviar infer\u00eancias a servi\u00e7os externos.", target: '[data-tour="page-title"]' },
    { chapter: "Vis\u00e3o Geral", title: "Barra de contexto", body: "O t\u00edtulo acompanha o m\u00f3dulo atual e os controles operacionais ficam sempre acess\u00edveis.", target: '[data-tour="topbar"]' },
    { chapter: "Vis\u00e3o Geral", title: "Projeto ativo", body: "Selecione o projeto que organiza seu trabalho e isola datasets e an\u00e1lises.", target: '[data-tour="project-selector"]' },
    { chapter: "Vis\u00e3o Geral", title: "Dataset ativo", body: "Escolha o conjunto de dados dispon\u00edvel no projeto selecionado.", target: '[data-tour="dataset-selector"]' },
    { chapter: "Vis\u00e3o Geral", title: "Navega\u00e7\u00e3o", body: "A barra lateral re\u00fane os 12 m\u00f3dulos organizados por etapa do fluxo anal\u00edtico.", target: '[data-tour="sidebar"]', fallbackTarget: '[data-tour="mobile-menu"]' },
    { chapter: "Dados", title: "Dashboard Executivo", body: modules[0][2], target: '[data-tour="header-view-dashboard"]', view: modules[0][0] },
    { chapter: "Dados", title: "Importa\u00e7\u00e3o", body: modules[2][2], target: '[data-tour="header-view-import"]', view: modules[2][0] },
    { chapter: "Dados", title: "Qualidade e Schema", body: modules[3][2], target: '[data-tour="header-view-quality"]', view: modules[3][0] },
    { chapter: "An\u00e1lises & IA", title: "An\u00e1lises financeiras e ESG", body: "As an\u00e1lises usam os dados dispon\u00edveis e mant\u00eam c\u00e1lculos determin\u00edsticos audit\u00e1veis.", target: '[data-tour="dashboard-workflow"]', view: modules[0][0] },
    { chapter: "An\u00e1lises & IA", title: "Assistente IA local", body: modules[4][2], target: '[data-tour="header-view-assistant"]', view: modules[4][0] },
    { chapter: "An\u00e1lises & IA", title: "Resultados Preditivos", body: modules[5][2], target: '[data-tour="header-view-predictive"]', view: modules[5][0] },
    { chapter: "An\u00e1lises & IA", title: "Simula\u00e7\u00f5es What-If", body: modules[6][2], target: '[data-tour="header-view-simulator"]', view: modules[6][0] },
    { chapter: "Governan\u00e7a", title: "Valida\u00e7\u00e3o", body: modules[7][2], target: '[data-tour="header-view-validation"]', view: modules[7][0] },
    { chapter: "Governan\u00e7a", title: "Power BI", body: modules[8][2], target: '[data-tour="header-view-powerbi"]', view: modules[8][0] },
    { chapter: "Governan\u00e7a", title: "Hist\u00f3rico e Auditoria", body: modules[9][2], target: '[data-tour="header-view-audit"]', view: modules[9][0] },
    { chapter: "Opera\u00e7\u00e3o", title: "Multiprojeto", body: modules[10][2], target: '[data-tour="header-view-multiproject"]', view: modules[10][0] },
    { chapter: "Opera\u00e7\u00e3o", title: "Automa\u00e7\u00f5es", body: modules[11][2], target: '[data-tour="header-view-scheduler"]', view: modules[11][0] },
    { chapter: "Opera\u00e7\u00e3o", title: "Governan\u00e7a e seguran\u00e7a", body: "O processamento permanece local, com teto de 8 GB de RAM e trilha de auditoria.", target: '[data-tour="ram-indicator"]' }
  ];

  const contextualGuides = {
    "view-dashboard": [
      { chapter: "Vis\u00e3o Executiva", title: "Painel Executivo", body: "Concentra indicadores financeiros, ESG e status de governan\u00e7a do projeto ativo.", target: '[data-tour="header-view-dashboard"]', view: "view-dashboard" },
      { chapter: "Vis\u00e3o Executiva", title: "Fluxo de governan\u00e7a", body: "Use os atalhos de etapas para navegar da importa\u00e7\u00e3o at\u00e9 a publica\u00e7\u00e3o no Power BI.", target: '[data-tour="dashboard-workflow"]', view: "view-dashboard" }
    ],
    "view-projects": [
      { chapter: "Projetos & LGPD", title: "Isolamento por projeto", body: "Cada projeto mant\u00e9m seus pr\u00f3prios datasets, an\u00e1lises, laudos e prazo de reten\u00e7\u00e3o.", target: '[data-tour="header-view-projects"]', view: "view-projects" },
      { chapter: "Projetos & LGPD", title: "Criar novo projeto", body: "Informe nome, setor, moeda e prazo LGPD para iniciar um novo espa\u00e7o isolado.", target: '[data-tour="projects-form"]', view: "view-projects" }
    ],
    "view-import": [
      { chapter: "Importa\u00e7\u00e3o", title: "Ingest\u00e3o segura", body: "Importe dados tabulares com hash SHA-256, chunking de mem\u00f3ria e varredura de PII.", target: '[data-tour="header-view-import"]', view: "view-import" },
      { chapter: "Importa\u00e7\u00e3o", title: "Bases de refer\u00eancia", body: "Carregue bases sint\u00e9ticas piloto, adversa ou curta para validar cada fluxo do sistema.", target: '[data-tour="import-samples"]', view: "view-import" },
      { chapter: "Importa\u00e7\u00e3o", title: "Upload CSV ou Excel", body: "Selecione arquivos .csv, .xlsx ou .xls para gerar perfilamento autom\u00e1tico de qualidade.", target: '[data-tour="import-upload"]', view: "view-import" }
    ],
    "view-quality": [
      { chapter: "Qualidade & Schema", title: "Diagn\u00f3stico do dataset", body: "Avalia completude, duplicidades, lacunas temporais e inconsist\u00eancias f\u00edsicas.", target: '[data-tour="header-view-quality"]', view: "view-quality" },
      { chapter: "Qualidade & Schema", title: "Preserva\u00e7\u00e3o de dados", body: "Valores suspeitos e outliers s\u00e3o sinalizados sem exclus\u00e3o silenciosa de registros.", target: '[data-tour="quality-profile"]', view: "view-quality" },
      { chapter: "Qualidade & Schema", title: "Mapeamento can\u00f4nico", body: "Associe colunas originais aos indicadores can\u00f4nicos e salve para reaplicar nas an\u00e1lises.", target: '[data-tour="quality-mapping"]', view: "view-quality" }
    ],
    "view-assistant": [
      { chapter: "Assistente IA & ESG", title: "C\u00e1lculo determin\u00edstico", body: "Os indicadores financeiros e emiss\u00f5es de Escopos 1, 2 e 3 s\u00e3o calculados em Python.", target: '[data-tour="header-view-assistant"]', view: "view-assistant" },
      { chapter: "Assistente IA & ESG", title: "Executar an\u00e1lise ESG", body: "Dispare o motor financeiro/ESG para gerar KPIs e laudo autom\u00e1tico de valida\u00e7\u00e3o.", target: '[data-tour="assistant-financial"]', view: "view-assistant" },
      { chapter: "Assistente IA & ESG", title: "Chat com IA local", body: "Envie perguntas em linguagem natural; o Ollama local aciona apenas as 6 tools permitidas.", target: '[data-tour="assistant-prompt"]', view: "view-assistant" }
    ],
    "view-predictive": [
      { chapter: "Resultados Preditivos", title: "Previs\u00e3o e backtesting", body: "Usa divis\u00e3o cronol\u00f3gica sem vazamento temporal e compara contra o baseline ing\u00eanuo.", target: '[data-tour="header-view-predictive"]', view: "view-predictive" },
      { chapter: "Resultados Preditivos", title: "Configurar modelo", body: "Escolha vari\u00e1vel alvo, algoritmo (Ridge ou RandomForest) e horizonte em meses.", target: '[data-tour="predictive-form"]', view: "view-predictive" }
    ],
    "view-simulator": [
      { chapter: "Simulador What-If", title: "Cen\u00e1rios condicionais", body: "Separa claramente hist\u00f3rico, previsto, simulado e impactos observados sem alterar a fonte.", target: '[data-tour="header-view-simulator"]', view: "view-simulator" },
      { chapter: "Simulador What-If", title: "Par\u00e2metros de sensibilidade", body: "Ajuste custos, energia, combust\u00edvel e reciclagem dentro dos limites validados.", target: '[data-tour="simulator-controls"]', view: "view-simulator" }
    ],
    "view-validation": [
      { chapter: "Valida\u00e7\u00e3o", title: "Port\u00e3o de governan\u00e7a", body: "Classifica an\u00e1lises em APROVADO, APROVADO_COM_RESSALVAS ou REJEITADO.", target: '[data-tour="header-view-validation"]', view: "view-validation" },
      { chapter: "Valida\u00e7\u00e3o", title: "Auditoria sob demanda", body: "Selecione uma an\u00e1lise executada para reavaliar regras matem\u00e1ticas e ESG.", target: '[data-tour="validation-trigger"]', view: "view-validation" }
    ],
    "view-powerbi": [
      { chapter: "Relat\u00f3rios Power BI", title: "Exporta\u00e7\u00e3o PBIP/PBIR", body: "Compila projeto tabular com medidas DAX, reconcilia\u00e7\u00e3o num\u00e9rica e pacote .zip.", target: '[data-tour="header-view-powerbi"]', view: "view-powerbi" },
      { chapter: "Relat\u00f3rios Power BI", title: "Compilar relat\u00f3rio", body: "Escolha apenas an\u00e1lises eleg\u00edveis; resultados rejeitados s\u00e3o bloqueados automaticamente.", target: '[data-tour="powerbi-form"]', view: "view-powerbi" }
    ],
    "view-audit": [
      { chapter: "Auditoria & Sistema", title: "Trilha local imut\u00e1vel", body: "Registra opera\u00e7\u00f5es no SQLite local para rastreabilidade completa sem envio externo.", target: '[data-tour="header-view-audit"]', view: "view-audit" },
      { chapter: "Auditoria & Sistema", title: "Modelo LLM e RAM", body: "Gerencie qwen3.5:4b/9b, descarregue da RAM ociosa e execute benchmark local.", target: '[data-tour="audit-models"]', view: "view-audit" },
      { chapter: "Auditoria & Sistema", title: "Expurgo LGPD e backup", body: "Execute expurgo por reten\u00e7\u00e3o e crie backups SQLite assinados com HMAC-SHA256.", target: '[data-tour="audit-lgpd"]', view: "view-audit" }
    ],
    "view-multiproject": [
      { chapter: "Multiprojeto", title: "Consolida\u00e7\u00e3o corporativa", body: "Agrega receitas, lucros e emiss\u00f5es apenas dos projetos com dados dispon\u00edveis.", target: '[data-tour="header-view-multiproject"]', view: "view-multiproject" },
      { chapter: "Multiprojeto", title: "Ranking de ecoefici\u00eancia", body: "Compare intensidade de carbono e conformidade metodol\u00f3gica entre unidades.", target: '[data-tour="multiproject-ranking"]', view: "view-multiproject" }
    ],
    "view-scheduler": [
      { chapter: "Automa\u00e7\u00f5es", title: "Agendador cooperativo", body: "Orquestra conectores, backups e auditorias locais com travas contra sobreposi\u00e7\u00e3o.", target: '[data-tour="header-view-scheduler"]', view: "view-scheduler" },
      { chapter: "Automa\u00e7\u00f5es", title: "Cadastrar rotina", body: "Defina tipo de tarefa, intervalo em minutos e reten\u00e7\u00e3o para agendar execu\u00e7\u00f5es.", target: '[data-tour="scheduler-form"]', view: "view-scheduler" }
    ]
  };

  function normalizeState(storage, version = VERSION) {
    let saved = {};
    try { saved = JSON.parse(storage.getItem(STORAGE_KEY) || "{}"); } catch (_) { saved = {}; }
    if (!saved || typeof saved !== "object" || Array.isArray(saved)) saved = {};
    return {
      version,
      introDismissed: saved.version === version && saved.introDismissed === true,
      completed: saved.version === version && saved.completed === true,
      progress: saved.version === version && Number.isInteger(saved.progress) && saved.progress >= 0 ? saved.progress : 0
    };
  }

  function clamp(value, min, max) {
    if (max < min) return min;
    return Math.max(min, Math.min(max, value));
  }

  function rectsIntersect(a, b) {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }

  function buildSpotlightRect(rect, viewport, pad = SPOTLIGHT_PAD) {
    const left = clamp(Math.floor(rect.left - pad), 0, Math.max(0, viewport.width - 2));
    const top = clamp(Math.floor(rect.top - pad), 0, Math.max(0, viewport.height - 2));
    const right = clamp(Math.ceil(rect.right + pad), left, viewport.width);
    const bottom = clamp(Math.ceil(rect.bottom + pad), top, viewport.height);
    return {
      left,
      top,
      right,
      bottom,
      width: Math.max(0, right - left),
      height: Math.max(0, bottom - top)
    };
  }

  function computeTooltipPlacement(spotRect, panelSize, viewport, options = {}) {
    const gap = options.gap ?? TOOLTIP_GAP;
    const margin = options.margin ?? VIEWPORT_MARGIN;
    const width = Math.min(panelSize.width, Math.max(240, viewport.width - margin * 2));
    const height = Math.min(panelSize.height, Math.max(180, viewport.height - margin * 2));
    const targetCenterX = spotRect.left + spotRect.width / 2;
    const targetCenterY = spotRect.top + spotRect.height / 2;

    const tallLeft = spotRect.height > viewport.height * 0.45 && spotRect.left < 120;
    const tallRight = spotRect.height > viewport.height * 0.45 && spotRect.right > viewport.width - 120;
    const order = tallLeft
      ? ["right", "bottom", "top", "left"]
      : tallRight
        ? ["left", "bottom", "top", "right"]
        : ["bottom", "top", "right", "left"];

    const candidates = {
      bottom: () => {
        const top = spotRect.bottom + gap;
        if (top + height > viewport.height - margin) return null;
        const left = clamp(Math.round(targetCenterX - width / 2), margin, viewport.width - width - margin);
        const arrowOffset = clamp(Math.round(targetCenterX - left), ARROW_EDGE_PAD, width - ARROW_EDGE_PAD);
        return { placement: "bottom", left, top, width, height, arrowOffset };
      },
      top: () => {
        const top = spotRect.top - gap - height;
        if (top < margin) return null;
        const left = clamp(Math.round(targetCenterX - width / 2), margin, viewport.width - width - margin);
        const arrowOffset = clamp(Math.round(targetCenterX - left), ARROW_EDGE_PAD, width - ARROW_EDGE_PAD);
        return { placement: "top", left, top, width, height, arrowOffset };
      },
      right: () => {
        const left = spotRect.right + gap;
        if (left + width > viewport.width - margin) return null;
        const top = clamp(Math.round(targetCenterY - height / 2), margin, viewport.height - height - margin);
        const arrowOffset = clamp(Math.round(targetCenterY - top), ARROW_EDGE_PAD, height - ARROW_EDGE_PAD);
        return { placement: "right", left, top, width, height, arrowOffset };
      },
      left: () => {
        const left = spotRect.left - gap - width;
        if (left < margin) return null;
        const top = clamp(Math.round(targetCenterY - height / 2), margin, viewport.height - height - margin);
        const arrowOffset = clamp(Math.round(targetCenterY - top), ARROW_EDGE_PAD, height - ARROW_EDGE_PAD);
        return { placement: "left", left, top, width, height, arrowOffset };
      }
    };

    for (const side of order) {
      const candidate = candidates[side]();
      if (!candidate) continue;
      const box = {
        left: candidate.left,
        top: candidate.top,
        right: candidate.left + candidate.width,
        bottom: candidate.top + candidate.height
      };
      if (!rectsIntersect(box, spotRect)) {
        return candidate;
      }
    }

    return null;
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
    let backdrop = null;
    let cutoutHole = null;
    let spot = null;
    let panel = null;
    let intro = null;
    let chooser = null;
    let resizeHandler = null;
    let scrollSettleTimer = null;
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

    function setBackdropHole(spotRect) {
      if (!backdrop) return;
      backdrop.hidden = false;
      if (backdrop.removeAttribute) backdrop.removeAttribute("hidden");
      if (backdrop.style) backdrop.style.display = "block";
      if (backdrop.setAttribute) {
        backdrop.setAttribute("viewBox", `0 0 ${global.innerWidth} ${global.innerHeight}`);
      }
      if (!cutoutHole || !cutoutHole.setAttribute) return;
      if (!spotRect) {
        cutoutHole.setAttribute("x", "0");
        cutoutHole.setAttribute("y", "0");
        cutoutHole.setAttribute("width", "0");
        cutoutHole.setAttribute("height", "0");
        return;
      }
      cutoutHole.setAttribute("x", String(spotRect.left));
      cutoutHole.setAttribute("y", String(spotRect.top));
      cutoutHole.setAttribute("width", String(spotRect.width));
      cutoutHole.setAttribute("height", String(spotRect.height));
    }

    function hideBackdrop() {
      if (cutoutHole && cutoutHole.setAttribute) {
        cutoutHole.setAttribute("x", "0");
        cutoutHole.setAttribute("y", "0");
        cutoutHole.setAttribute("width", "0");
        cutoutHole.setAttribute("height", "0");
      }
      if (backdrop) {
        backdrop.hidden = true;
        if (backdrop.setAttribute) backdrop.setAttribute("hidden", "");
        if (backdrop.style) backdrop.style.display = "none";
      }
      if (spot) spot.hidden = true;
    }

    function buildUi() {
      const root = document.createElement("div");
      root.id = "ecobi-onboarding";
      root.innerHTML = [
        '<svg class="eco-tour-backdrop" aria-hidden="true" hidden>',
        '<defs><mask id="eco-tour-cutout-mask">',
        '<rect x="0" y="0" width="100%" height="100%" fill="white"></rect>',
        '<rect id="eco-tour-cutout-hole" x="0" y="0" width="0" height="0" rx="10" ry="10" fill="black"></rect>',
        "</mask></defs>",
        '<rect class="eco-tour-backdrop-fill" x="0" y="0" width="100%" height="100%" mask="url(#eco-tour-cutout-mask)"></rect>',
        "</svg>",
        '<div class="eco-tour-spotlight" aria-hidden="true" hidden></div>',
        '<section class="eco-tour-panel" role="dialog" aria-modal="false" aria-labelledby="eco-tour-title" aria-describedby="eco-tour-body" hidden>',
        '<div class="eco-tour-panel-inner">',
        '<div class="eco-tour-header">',
        '<span class="eco-tour-progress"></span>',
        '<button type="button" class="eco-tour-close-btn" data-action="close" aria-label="Encerrar tutorial" title="Encerrar tutorial">&times;</button>',
        "</div>",
        '<div class="eco-tour-content">',
        '<h2 id="eco-tour-title"></h2>',
        '<p id="eco-tour-body"></p>',
        '<p class="eco-tour-recovery" aria-live="polite" hidden></p>',
        "</div>",
        '<div class="eco-tour-actions">',
        '<button type="button" class="eco-tour-btn-skip" data-action="skip-step">Pular</button>',
        '<div class="eco-tour-nav-group">',
        '<button type="button" data-action="back">Voltar</button>',
        '<button type="button" data-action="next">Avan\u00e7ar</button>',
        "</div>",
        "</div>",
        "</div>",
        "</section>",
        '<section class="eco-tour-intro" role="dialog" aria-modal="false" aria-labelledby="eco-intro-title" aria-describedby="eco-intro-body" hidden>',
        '<h2 id="eco-intro-title">Bem-vindo ao EcoBI Intelligence</h2>',
        '<p id="eco-intro-body">Conhe\u00e7a a plataforma, entenda seus m\u00f3dulos e aprenda a transformar seus dados em informa\u00e7\u00f5es estrat\u00e9gicas.</p>',
        '<div class="eco-tour-actions eco-tour-dialog-actions">',
        '<button type="button" data-action="start">Come\u00e7ar tutorial</button>',
        '<button type="button" data-action="defer">Fazer depois</button>',
        '<button type="button" data-action="dismiss">Pular apresenta\u00e7\u00e3o</button>',
        "</div>",
        "</section>",
        '<section class="eco-tour-chooser" role="dialog" aria-modal="true" aria-labelledby="eco-help-title" hidden>',
        '<h2 id="eco-help-title">Ajuda e tutorial</h2>',
        "<p>Escolha uma apresenta\u00e7\u00e3o guiada da interface.</p>",
        '<div class="eco-tour-actions eco-tour-dialog-actions">',
        '<button type="button" data-action="general-help">Tour geral</button>',
        '<button type="button" data-action="context-help">Guia deste m\u00f3dulo</button>',
        '<button type="button" data-action="help-close">Fechar</button>',
        "</div>",
        "</section>"
      ].join("");
      document.body.appendChild(root);
      backdrop = root.querySelector(".eco-tour-backdrop");
      cutoutHole = root.querySelector("#eco-tour-cutout-hole");
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
      if (!state.introDismissed) {
        returnFocus = document.activeElement;
        intro.hidden = false;
        intro.querySelector('[data-action="start"]').focus({ preventScroll: true });
      }
    }

    function openHelp() {
      if (!panel) return;
      if (!panel.hidden) closeTour();
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

    function isElementUsable(element) {
      if (!element || !element.getClientRects().length) return false;
      const computed = getComputedStyle(element);
      if (computed.visibility === "hidden" || computed.display === "none") return false;
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.right > 0 && rect.left < global.innerWidth;
    }

    function resolveStepTarget(step) {
      if (!step) return null;
      const primary = document.querySelector(step.target);
      if (isElementUsable(primary)) return primary;
      if (step.fallbackTarget) {
        const fallback = document.querySelector(step.fallbackTarget);
        if (isElementUsable(fallback)) return fallback;
      }
      return null;
    }

    function startContext(viewId) {
      const steps = contextualGuides[viewId] || contextualGuides["view-dashboard"];
      start(steps);
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

    function showCenteredFallback(message) {
      if (spot) spot.hidden = true;
      setBackdropHole(null);
      panel.style.top = "50%";
      panel.style.left = "50%";
      panel.style.transform = "translate(-50%, -50%)";
      if (panel.style.removeProperty) panel.style.removeProperty("--eco-arrow-offset");
      panel.dataset.placement = "center";
      const recovery = panel.querySelector(".eco-tour-recovery");
      if (recovery) {
        recovery.hidden = !message;
        recovery.textContent = message || "";
      }
    }

    function renderCurrent() {
      if (!activeSteps.length) return closeTour();
      const step = activeSteps[currentStep];
      if (step.view && step.view !== currentView && viewSwitcher) {
        currentView = step.view;
        viewSwitcher(step.view);
      }
      global.requestAnimationFrame(() => {
        if (!activeSteps.length || activeSteps[currentStep] !== step) return;
        panel.hidden = false;
        const chapterPrefix = step.chapter ? `${step.chapter} \u00b7 ` : "";
        panel.querySelector(".eco-tour-progress").textContent = `${chapterPrefix}Etapa ${currentStep + 1} de ${activeSteps.length}`;
        panel.querySelector("#eco-tour-title").textContent = step.title;
        panel.querySelector("#eco-tour-body").textContent = step.body;
        panel.querySelector('[data-action="back"]').disabled = currentStep === 0;
        panel.querySelector('[data-action="next"]').textContent = currentStep === activeSteps.length - 1 ? "Concluir" : "Avan\u00e7ar";
        const target = resolveStepTarget(step);
        const recovery = panel.querySelector(".eco-tour-recovery");
        if (!target) {
          showCenteredFallback("Destaque indispon\u00edvel aqui. Avance ou encerre.");
        } else {
          target.scrollIntoView({ block: "center", inline: "nearest", behavior: "auto" });
          let positioned = positionTarget(target);
          if (!positioned) {
            target.scrollIntoView({ block: "start", inline: "nearest", behavior: "auto" });
            positioned = positionTarget(target);
          }
          if (!positioned) {
            showCenteredFallback("");
          } else if (recovery) {
            recovery.hidden = true;
            recovery.textContent = "";
          }
          if (scrollSettleTimer) global.clearTimeout(scrollSettleTimer);
          if (typeof global.setTimeout === "function") {
            scrollSettleTimer = global.setTimeout(() => positionCurrent(), 60);
          }
        }
        panel.querySelector('[data-action="next"]').focus({ preventScroll: true });
      });
    }

    function positionTarget(target) {
      if (!target) return false;
      const rect = target.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return false;
      const viewport = { width: global.innerWidth, height: global.innerHeight };
      const spotRect = buildSpotlightRect(rect, viewport, SPOTLIGHT_PAD);
      if (spotRect.width <= 0 || spotRect.height <= 0) return false;

      panel.style.transform = "none";
      const measured = panel.getBoundingClientRect();
      const panelSize = {
        width: measured.width > 0 ? measured.width : Math.min(392, viewport.width - VIEWPORT_MARGIN * 2),
        height: measured.height > 0 ? measured.height : (viewport.width <= 480 ? 240 : 228)
      };

      const layout = computeTooltipPlacement(spotRect, panelSize, viewport);
      if (!layout) {
        showCenteredFallback("");
        return false;
      }

      setBackdropHole(spotRect);
      spot.style.left = `${spotRect.left}px`;
      spot.style.top = `${spotRect.top}px`;
      spot.style.width = `${spotRect.width}px`;
      spot.style.height = `${spotRect.height}px`;
      spot.hidden = false;

      panel.style.left = `${layout.left}px`;
      panel.style.top = `${layout.top}px`;
      if (panel.style.setProperty) {
        panel.style.setProperty("--eco-arrow-offset", `${layout.arrowOffset}px`);
      } else {
        panel.style["--eco-arrow-offset"] = `${layout.arrowOffset}px`;
      }
      panel.dataset.placement = layout.placement;
      return true;
    }

    function positionCurrent() {
      if (panel && !panel.hidden && activeSteps[currentStep]) {
        const target = resolveStepTarget(activeSteps[currentStep]);
        if (!target) {
          showCenteredFallback("Destaque indispon\u00edvel aqui. Avance ou encerre.");
          return;
        }
        positionTarget(target);
      }
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
      else if (action === "back") { currentStep = Math.max(0, currentStep - 1); if (activeIsGeneral) persist({ progress: currentStep }); renderCurrent(); }
      else if (action === "next" || action === "skip-step") {
        if (currentStep < activeSteps.length - 1) { currentStep += 1; if (activeIsGeneral) persist({ progress: currentStep }); renderCurrent(); }
        else { if (activeIsGeneral) persist({ introDismissed: true, completed: true, progress: 0 }); closeTour(); }
      } else if (action === "close") closeTour();
    }

    function closeTour() {
      if (scrollSettleTimer && typeof global.clearTimeout === "function") {
        global.clearTimeout(scrollSettleTimer);
        scrollSettleTimer = null;
      }
      if (panel) panel.hidden = true;
      hideBackdrop();
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
      if (scrollSettleTimer && typeof global.clearTimeout === "function") {
        global.clearTimeout(scrollSettleTimer);
        scrollSettleTimer = null;
      }
      setBackgroundInert(false);
      const root = document.getElementById("ecobi-onboarding");
      if (root) root.remove();
      document.removeEventListener("keydown", onKeyDown);
      global.removeEventListener("resize", resizeHandler);
      global.removeEventListener("scroll", resizeHandler, true);
      backdrop = cutoutHole = spot = panel = intro = chooser = null;
    }

    return {
      init,
      openHelp,
      startGeneral: () => start(generalSteps),
      startContext,
      setCurrentView: (viewId) => { currentView = viewId; },
      close: closeTour,
      getGeneralSteps: () => generalSteps.map((step) => ({ ...step })),
      getContextualSteps: (viewId) => (contextualGuides[viewId] || []).map((step) => ({ ...step })),
      getModules: () => modules.map(([id, title, body]) => ({ id, title, body })),
      normalizeState,
      computeTooltipPlacement,
      rectsIntersect,
      destroy,
      version: VERSION
    };
  }

  const api = createApi();
  global.EcoBIOnboarding = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
