/* Casca comum do painel: barra de cima (computador) e barra de abas embaixo (celular).
   Uso: <script src="/casca.js"></script> logo depois de abrir o <body>. */
(function () {
  var ABAS = [
    { href: "/", longo: "Visão geral", curto: "Visão", icone: "squares-four" },
    { href: "/terminal", longo: "Cripto", curto: "Cripto", icone: "chart-line-up" },
    { href: "/acoes", longo: "Ações EUA", curto: "Ações", icone: "trend-up" },
    { href: "/investidores", longo: "Investidores", curto: "Fundos", icone: "users-three" },
    { href: "/relatorios", longo: "Relatórios", curto: "Diário", icone: "file-text" },
    { href: "/conta", longo: "Configurações", curto: "Ajustes", icone: "gear" },
  ];
  var CAMINHO_ATUAL = location.pathname === "/senha" ? "/conta" : location.pathname.replace(/\/+$/, "") || "/";

  // ícones Phosphor (estilo regular), versão fixa com integridade
  var css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = "https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css";
  css.integrity = "sha384-6p9AefaqUhEVheRlj1mpAkbngHXy9mbYMrIdcIt4Jlc9lOLIablJq3bBsLOjGwZ7";
  css.crossOrigin = "anonymous";
  document.head.appendChild(css);

  document.body.classList.add("casca");
  var topo = document.createElement("header");
  topo.className = "casca-topo";
  topo.innerHTML =
    '<a class="casca-marca" href="/"><img src="/icone.png" alt=""><span>Robô de Trade</span></a>' +
    '<nav class="casca-abas" aria-label="Seções do painel">' +
    ABAS.map(function (a) {
      var atual = a.href === CAMINHO_ATUAL ? ' aria-current="page"' : "";
      return '<a href="' + a.href + '"' + atual + '><i class="ph ph-' + a.icone + ' ic" aria-hidden="true"></i>' +
        '<span class="l-longo">' + a.longo + '</span><span class="l-curto">' + a.curto + "</span></a>";
    }).join("") +
    "</nav>" +
    '<a class="casca-selo" id="cascaSelo" href="/" data-s="" aria-live="polite"><span class="ponto"></span><span id="cascaSeloTxt">Conectando</span></a>';
  document.body.insertBefore(topo, document.body.firstChild);

  var selo = document.getElementById("cascaSelo"), seloTxt = document.getElementById("cascaSeloTxt");
  function mostrar(estado, texto, real) {
    selo.dataset.s = estado;
    if (real) selo.dataset.real = "1"; else delete selo.dataset.real;
    seloTxt.textContent = texto;
  }
  async function consultar() {
    try {
      var r = await fetch("/api/resumo");
      if (!r.ok) throw new Error("http");
      var d = await r.json();
      var g = d.guarda || {};
      var pausada = !!(d.pausa_arquivo || g.pausa || (d.travas || []).some(function (t) { return t.active && t.pair === "*"; }));
      if (!d.robo_ligado) return mostrar("off", "Robô desligado", false);
      if (d.estado !== "running") return mostrar("off", "Robô parado", false);
      var real = d.dry_run === false;
      mostrar(pausada ? "pausa" : "ok",
        (real ? "DINHEIRO REAL" : "Teste") + " · " + (pausada ? "compras pausadas" : "operando"), real);
    } catch (e) {
      mostrar("off", "Painel sem conexão", false);
    }
  }
  consultar();
  setInterval(consultar, 15000);
})();
