(function () {
  "use strict";

  var pagina = document.body.getAttribute("data-pagina");
  var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
               "setembro", "outubro", "novembro", "dezembro"];

  function esc(t) {
    return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function dataBonita(iso) {
    if (!iso) return "";
    var p = iso.slice(0, 10).split("-");
    return parseInt(p[2], 10) + " de " + MESES[parseInt(p[1], 10) - 1] + " de " + p[0];
  }
  function carregar(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url);
      return r.json();
    });
  }
  function el(id) { return document.getElementById(id); }

  function preencherOnde(select, locais, valor) {
    var html = '<option value="">Mostrar tudo</option>';
    locais.forEach(function (l) {
      html += '<option value="' + esc(l.id) + '"' + (l.id === valor ? " selected" : "") + ">" + esc(l.rotulo) + "</option>";
    });
    select.innerHTML = html;
  }

  function botoesOpcoes(ul, necessidades, escolhidas, aoMudar) {
    ul.innerHTML = necessidades.map(function (n) {
      var on = escolhidas.indexOf(n.id) >= 0;
      return '<li><button type="button" class="opcao" data-id="' + esc(n.id) + '" aria-pressed="' + on + '">' +
        esc(n.rotulo) + "</button></li>";
    }).join("");
    ul.addEventListener("click", function (ev) {
      var b = ev.target.closest("button.opcao");
      if (!b) return;
      var id = b.getAttribute("data-id");
      var i = escolhidas.indexOf(id);
      if (i >= 0) escolhidas.splice(i, 1); else escolhidas.push(id);
      b.setAttribute("aria-pressed", i < 0);
      aoMudar();
    });
  }

  function noticiaHtml(n, comData) {
    var meta = esc(n.fonte);
    if (n.idioma_original && n.idioma_original !== "pt") meta += ", em inglês";
    if (comData && n.data) meta = dataBonita(n.data) + ", " + meta;
    return '<li class="noticia"><h3><a href="' + esc(n.link) + '" rel="noopener">' + esc(n.titulo) + "</a></h3>" +
      "<p>" + esc(n.resumo) + '</p><p class="meta">' + meta + "</p></li>";
  }

  // ------------------------------------------------------------ Página inicial
  function inicio(site) {
    var escolhidas = [];
    var onde = el("inicio-onde");
    var ver = el("inicio-ver");
    function atualizar() {
      var q = [];
      if (escolhidas.length) q.push("quero=" + escolhidas.join(","));
      if (onde.value) q.push("onde=" + onde.value);
      ver.href = "cursos.html" + (q.length ? "?" + q.join("&") : "");
    }
    botoesOpcoes(el("inicio-opcoes"), site.necessidades, escolhidas, atualizar);
    preencherOnde(onde, site.locais, "");
    onde.addEventListener("change", atualizar);

    carregar("dados/noticias.json").then(function (d) {
      var itens = [];
      (d.dias || []).forEach(function (dia) { dia.itens.forEach(function (n) { itens.push(n); }); });
      el("inicio-noticias").innerHTML = itens.length
        ? itens.slice(0, 5).map(function (n) { return noticiaHtml(n, false); }).join("")
        : '<li class="vazio">As primeiras notícias aparecem aqui amanhã de manhã.</li>';
    }).catch(function () {
      el("inicio-noticias").innerHTML = '<li class="vazio">As primeiras notícias aparecem aqui em breve.</li>';
    });
  }

  // ------------------------------------------------------------ Cursos
  function cursos(site) {
    var params = new URLSearchParams(location.search);
    var escolhidas = (params.get("quero") || "").split(",").filter(Boolean);
    var onde = el("cursos-onde");
    var texto = el("cursos-texto");
    var lista = el("cursos-lista");
    var contagem = el("cursos-contagem");
    var todos = [];
    var rotulos = {};
    site.necessidades.forEach(function (n) { rotulos[n.id] = n.rotulo; });
    var nomesLocal = {};
    site.locais.forEach(function (l) { nomesLocal[l.id] = l.rotulo; });

    function semAcentos(t) {
      return String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }

    function cursoHtml(c) {
      var factos = [];
      if (c.modalidade === "online") factos.push("Online");
      else {
        var partes = [c.cidade, c.regiao].filter(Boolean).filter(function (v, i, a) { return a.indexOf(v) === i; });
        var sitio = partes.join(", ") || nomesLocal[c.local] || "";
        factos.push((c.modalidade === "misto" ? "Presencial e online" : "Presencial") + (sitio ? ": " + sitio : ""));
      }
      if (c.certificado === "gratuito") factos.push('<span class="bom">Certificado gratuito</span>');
      else if (c.certificado === "pago") factos.push('<span class="atencao">Certificado pago</span>');
      if (c.inscricoes_ate) factos.push('<span class="atencao">Inscrições até ' + esc(dataBonita(c.inscricoes_ate)) + "</span>");
      if (c.inicio) factos.push("Começa a " + esc(dataBonita(c.inicio)));
      if (c.duracao) factos.push(esc(c.duracao));
      var factosHtml = factos.map(function (f) {
        var m = f.match(/^<span class="(\w+)">(.*)<\/span>$/);
        return m ? '<li class="' + m[1] + '">' + m[2] + "</li>" : "<li>" + (f.indexOf("<") >= 0 ? f : esc(f)) + "</li>";
      }).join("");
      var condicoes = [];
      if (c.exclusivo_para) condicoes.push(esc(c.exclusivo_para));
      if (c.requisitos) condicoes.push("Requisitos: " + esc(c.requisitos));
      return '<li class="curso"><h3><a href="' + esc(c.url) + '" rel="noopener">' + esc(c.titulo) + "</a></h3>" +
        (c.entidade ? '<p class="entidade">' + esc(c.entidade) + "</p>" : "") +
        (c.descricao ? "<p>" + esc(c.descricao) + "</p>" : "") +
        '<ul class="factos">' + factosHtml + "</ul>" +
        (condicoes.length ? '<p class="condicao">' + condicoes.join(". ") + "</p>" : "") +
        '<a class="botao secundario" href="' + esc(c.url) + '" rel="noopener">Ver curso e inscrever-se</a></li>';
    }

    function filtrar() {
      var o = onde.value;
      var t = semAcentos(texto.value.trim());
      var res = todos.filter(function (c) {
        if (escolhidas.length && !c.necessidades.some(function (n) { return escolhidas.indexOf(n) >= 0; })) return false;
        if (o === "online" && c.modalidade !== "online") return false;
        if (o && o !== "online" && c.modalidade !== "online" && c.local !== o) return false;
        if (t) {
          var alvo = semAcentos([c.titulo, c.descricao, c.entidade, c.cidade, c.regiao].join(" "));
          if (alvo.indexOf(t) < 0) return false;
        }
        return true;
      });
      res.sort(function (a, b) {
        var pa = a.modalidade === "online" ? 1 : 0, pb = b.modalidade === "online" ? 1 : 0;
        if (pa !== pb) return pa - pb;
        return (b.primeiro_visto || "").localeCompare(a.primeiro_visto || "");
      });
      var presenciais = res.filter(function (c) { return c.modalidade !== "online"; }).length;
      var resumo = res.length === 1 ? "1 curso" : res.length + " cursos";
      if (o && o !== "online" && res.length) resumo += " (" + presenciais + (presenciais === 1 ? " presencial, " : " presenciais, ") + (res.length - presenciais) + " online)";
      contagem.textContent = res.length ? resumo : "";
      lista.innerHTML = res.length ? res.map(cursoHtml).join("") :
        '<li class="vazio">Não há cursos com estas opções neste momento. Experimente escolher menos opções ou "Mostrar tudo" em "Onde está?". A lista é atualizada todas as semanas.</li>';

      var q = new URLSearchParams();
      if (escolhidas.length) q.set("quero", escolhidas.join(","));
      if (o) q.set("onde", o);
      history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q.toString() : ""));
    }

    botoesOpcoes(el("cursos-opcoes"), site.necessidades, escolhidas, filtrar);
    preencherOnde(onde, site.locais, params.get("onde") || "");
    onde.addEventListener("change", filtrar);
    texto.addEventListener("input", filtrar);

    lista.innerHTML = '<li class="discreto">A carregar os cursos…</li>';
    carregar("dados/cursos.json").then(function (d) {
      todos = d.cursos || [];
      filtrar();
    }).catch(function () {
      lista.innerHTML = '<li class="vazio">Não foi possível carregar os cursos. Atualize a página daqui a pouco.</li>';
    });
  }

  // ------------------------------------------------------------ Notícias
  function noticias(site) {
    var tema = el("noticias-tema");
    var caixa = el("noticias-lista");
    var dados = { dias: [] };
    var html = '<option value="">Todos os temas</option>';
    Object.keys(site.temas).forEach(function (k) {
      html += '<option value="' + esc(k) + '">' + esc(site.temas[k]) + "</option>";
    });
    tema.innerHTML = html;

    function mostrar() {
      var t = tema.value;
      var partes = [];
      dados.dias.forEach(function (dia) {
        var itens = dia.itens.filter(function (n) { return !t || n.tema === t; });
        if (!itens.length) return;
        partes.push('<h2 class="dia">' + esc(dataBonita(dia.data)) + '</h2><ul class="lista">' +
          itens.map(function (n) { return noticiaHtml(n, false); }).join("") + "</ul>");
      });
      caixa.innerHTML = partes.length ? partes.join("") :
        '<p class="vazio">Ainda não há notícias com este tema. Escolha "Todos os temas".</p>';
    }
    tema.addEventListener("change", mostrar);
    carregar("dados/noticias.json").then(function (d) { dados = d; mostrar(); })
      .catch(function () { caixa.innerHTML = '<p class="vazio">As primeiras notícias aparecem aqui em breve.</p>'; });
  }

  carregar("dados/site.json").then(function (site) {
    if (pagina === "inicio") inicio(site);
    else if (pagina === "cursos") cursos(site);
    else if (pagina === "noticias") noticias(site);
  });
})();
