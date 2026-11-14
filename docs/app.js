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
    preencherOnde(onde, site.locais, site.territorio_piloto || "");
    onde.addEventListener("change", atualizar);
    atualizar();

    var caixa = el("inicio-ultimos");
    carregar("dados/cursos.json").then(function (d) {
      var hoje = new Date().toISOString().slice(0, 10);
      var limite = new Date(Date.now() + 10 * 864e5).toISOString().slice(0, 10);
      var ultimos = (d.cursos || []).filter(function (c) {
        return c.inscricoes_ate && c.inscricoes_ate >= hoje && c.inscricoes_ate <= limite;
      }).sort(function (a, b) { return a.inscricoes_ate.localeCompare(b.inscricoes_ate); }).slice(0, 5);
      if (!ultimos.length) { caixa.parentNode.style.display = "none"; return; }
      caixa.innerHTML = ultimos.map(function (c) {
        var sitio = c.modalidade === "online" ? "On-line" : [c.cidade, c.regiao].filter(Boolean)[0] || "";
        return '<li class="noticia"><h3><a href="' + esc(c.url) + '" rel="noopener">' + esc(c.titulo) + "</a></h3>" +
          '<p class="meta">' + (sitio ? esc(sitio) + ". " : "") + "Inscrições até " + esc(dataBonita(c.inscricoes_ate)) + "</p></li>";
      }).join("");
    }).catch(function () { caixa.parentNode.style.display = "none"; });
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
    var guiasPorId = {};
    var barreiras = (params.get("facilita") || "").split(",").filter(Boolean);
    var cidade = el("cursos-cidade");
    var notaBarreiras = el("cursos-nota-barreiras");
    var rotulos = {};
    site.necessidades.forEach(function (n) { rotulos[n.id] = n.rotulo; });
    var nomesLocal = {};
    site.locais.forEach(function (l) { nomesLocal[l.id] = l.rotulo; });

    function semAcentos(t) {
      return String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }

    var TURNO = { "Manhã": "De manhã", "Tarde": "À tarde", "Noite": "À noite" };
    var ESCOLARIDADE = {
      "Saber ler e escrever": "Você sabe ler e escrever?",
      "Fundamental incompleto": "Você já estudou pelo menos uma parte do ensino fundamental?",
      "Fundamental completo": "Você terminou o ensino fundamental?",
      "Médio incompleto": "Você já começou o ensino médio?",
      "Médio completo": "Você terminou o ensino médio?",
      "Superior": "Você tem curso superior?"
    };

    function perguntas(c) {
      var q = [];
      if (c.idade_minima) q.push({ p: "Você tem " + c.idade_minima + " anos ou mais?", nao: "O curso pede idade mínima de " + c.idade_minima + " anos." });
      if (c.escolaridade && ESCOLARIDADE[c.escolaridade]) q.push({ p: ESCOLARIDADE[c.escolaridade], nao: "O curso pede: " + c.escolaridade.toLowerCase() + "." });
      if (c.renda) {
        if (/dois sal[aá]rios/i.test(c.renda)) q.push({
          p: "Somando o que todos da sua casa ganham por mês e dividindo pelo número de pessoas, dá até dois salários mínimos?",
          nao: "O curso é para famílias com renda de até dois salários mínimos por pessoa." });
        else q.push({ p: "O curso pede: " + c.renda + ". A sua situação se encaixa?", nao: "O curso pede: " + c.renda + "." });
      }
      if (/aperfei[cç]oamento/i.test(c.documentos || "")) q.push({
        p: "Você já tem experiência na área (certificado, carteira de trabalho, declaração da empresa ou declaração sua)?",
        nao: "É um curso de aperfeiçoamento: pede experiência na área." });
      return q;
    }

    function posso(c, i) {
      var q = perguntas(c);
      if (!q.length) return "";
      return '<details class="posso" data-curso="' + i + '"><summary>Posso me inscrever?</summary>' +
        '<p class="discreto">Responda para saber. Nada do que você responde é guardado.</p><ol>' +
        q.map(function (x, j) {
          return '<li><p>' + esc(x.p) + '</p><div class="simnao" role="group">' +
            '<button type="button" class="opcao" data-q="' + j + '" data-r="sim" aria-pressed="false">Sim</button>' +
            '<button type="button" class="opcao" data-q="' + j + '" data-r="nao" aria-pressed="false">Não</button></div></li>';
        }).join("") + '</ol><p class="resultado" aria-live="polite"></p></details>';
    }

    function antesHtml(c) {
      var g = (c.antes || []).map(function (id) { return guiasPorId[id]; }).filter(Boolean);
      if (!g.length) return "";
      return '<p class="antes">Antes, você vai precisar de: ' + g.map(function (x) {
        return '<a href="antes.html#' + esc(x.id) + '">' + esc(x.titulo.replace(/^Tirar o |^Fazer o |^Criar a /, "")) + "</a>";
      }).join(", ") + ".</p>";
    }

    function cursoHtml(c, i) {
      var factos = [];
      if (c.modalidade === "online") factos.push("On-line");
      else {
        var partes = [c.cidade, c.regiao].filter(Boolean).filter(function (v, i, a) { return a.indexOf(v) === i; });
        var sitio = partes.join(", ") || nomesLocal[c.local] || "";
        factos.push((c.modalidade === "misto" ? "Presencial e on-line" : "Presencial") + (sitio ? ": " + sitio : ""));
      }
      if (c.certificado === "gratuito") factos.push('<span class="bom">Certificado gratuito</span>');
      else if (c.certificado === "pago") factos.push('<span class="atencao">Certificado pago</span>');
      if (c.inscricoes_ate) factos.push('<span class="atencao">Inscrições até ' + esc(dataBonita(c.inscricoes_ate)) + "</span>");
      else if (c.data_por_confirmar) factos.push('<span class="atencao">Confirme a data na página oficial</span>');
      if (c.situacao === "Por confirmar") factos.push('<span class="atencao">Inscrições por confirmar</span>');
      if (c.inicio) factos.push("Começa em " + esc(dataBonita(c.inicio)));
      (c.turnos || []).forEach(function (t) { if (TURNO[t]) factos.push(TURNO[t]); });
      if (c.ajuda) factos.push('<span class="bom">' + esc(c.ajuda) + "</span>");
      if (c.duracao) factos.push(esc(c.duracao));
      var factosHtml = factos.map(function (f) {
        var m = f.match(/^<span class="(\w+)">(.*)<\/span>$/);
        return m ? '<li class="' + m[1] + '">' + m[2] + "</li>" : "<li>" + (f.indexOf("<") >= 0 ? f : esc(f)) + "</li>";
      }).join("");
      var condicoes = [];
      if (c.exclusivo_para) condicoes.push(esc(c.exclusivo_para));
      if (c.requisitos) condicoes.push("Requisitos: " + esc(c.requisitos));
      if (c.documentos) condicoes.push("Documentos: " + esc(c.documentos.replace(/\.$/, "")));
      return '<li class="curso"><h3><a href="' + esc(c.url) + '" rel="noopener">' + esc(c.titulo) + "</a></h3>" +
        (c.entidade ? '<p class="entidade">' + esc(c.entidade) + "</p>" : "") +
        (c.descricao ? "<p>" + esc(c.descricao) + "</p>" : "") +
        '<ul class="factos">' + factosHtml + "</ul>" +
        (condicoes.length ? '<p class="condicao">' + condicoes.join(". ") + "</p>" : "") +
        posso(c, i) + antesHtml(c) +
        (c.onde_inscrever && c.onde_inscrever.length ? '<div class="onde"><p class="onde-titulo">Onde se inscrever</p><ul>' +
          c.onde_inscrever.map(function (u) {
            var linhas = ["<strong>" + esc(u.nome) + "</strong>"];
            var morada = [u.morada, u.bairro, u.municipio].filter(Boolean).join(", ");
            if (morada) linhas.push(esc(morada));
            if (u.horario) linhas.push("Atendimento: " + esc(u.horario));
            var contactos = [u.telefone ? "Telefone " + esc(u.telefone) : "", u.whatsapp ? "WhatsApp " + esc(u.whatsapp) : ""].filter(Boolean);
            if (contactos.length) linhas.push(contactos.join(" · "));
            if (u.o_que_levar) linhas.push("Leve: " + esc(u.o_que_levar));
            return "<li>" + linhas.join("<br>") + "</li>";
          }).join("") + "</ul></div>" : "") +
        (c.como_me_inscrever && c.como_me_inscrever.length ? '<details class="passos"><summary>Como se inscrever</summary><ol>' +
          c.como_me_inscrever.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ol></details>" : "") +
        '<a class="botao secundario" href="' + esc(c.url) + '" rel="noopener">Ver curso e se inscrever</a>' +
        '<p class="verificado">' + (c.verificado_em ? "Verificado em " + esc(dataBonita(c.verificado_em)) + ". " : "") +
        "Confirme sempre na página oficial antes de ir.</p></li>";
    }

    function filtrar() {
      var o = onde.value;
      var t = semAcentos(texto.value.trim());
      var res = todos.filter(function (c) {
        if (escolhidas.length && !c.necessidades.some(function (n) { return escolhidas.indexOf(n) >= 0; })) return false;
        if (o === "online" && c.modalidade !== "online") return false;
        if (o && o !== "online" && c.modalidade !== "online" && c.local !== o) return false;
        if (barreiras.indexOf("noite") >= 0 && (c.turnos || []).indexOf("Noite") < 0) return false;
        if (barreiras.indexOf("sem_internet") >= 0 && c.internet !== "Não") return false;
        if (barreiras.indexOf("sem_escolaridade") >= 0 && ["Nenhuma", "Saber ler e escrever"].indexOf(c.escolaridade) < 0) return false;
        if (barreiras.indexOf("ajuda") >= 0 && (!c.ajuda || /^n[aã]o/i.test(c.ajuda))) return false;
        if (cidade.value && c.modalidade !== "online" && cidadesDe(c).indexOf(cidade.value) < 0) return false;
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
      if (o && o !== "online" && res.length) resumo += " (" + presenciais + (presenciais === 1 ? " presencial, " : " presenciais, ") + (res.length - presenciais) + " on-line)";
      contagem.textContent = res.length ? resumo : "";
      notaBarreiras.hidden = !barreiras.length;
      lista.innerHTML = res.length ? res.map(function (c) { return cursoHtml(c, todos.indexOf(c)); }).join("") :
        '<li class="vazio">Não há cursos com essas opções no momento. Tente escolher menos opções ou "Mostrar tudo" em "Onde você está?". A lista é atualizada toda semana.</li>';

      var q = new URLSearchParams();
      if (escolhidas.length) q.set("quero", escolhidas.join(","));
      if (o) q.set("onde", o);
      if (barreiras.length) q.set("facilita", barreiras.join(","));
      if (cidade.value) q.set("cidade", cidade.value);
      history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q.toString() : ""));
    }

    function cidadesDe(c) {
      var l = [c.cidade].concat((c.onde_inscrever || []).map(function (u) { return u.municipio; }));
      return l.filter(Boolean);
    }
    var ulBarreiras = el("cursos-barreiras");
    [].forEach.call(ulBarreiras.querySelectorAll("button"), function (b) {
      b.setAttribute("aria-pressed", barreiras.indexOf(b.getAttribute("data-barreira")) >= 0);
    });
    ulBarreiras.addEventListener("click", function (ev) {
      var b = ev.target.closest("button.opcao");
      if (!b) return;
      var id = b.getAttribute("data-barreira"), i = barreiras.indexOf(id);
      if (i >= 0) barreiras.splice(i, 1); else barreiras.push(id);
      b.setAttribute("aria-pressed", i < 0);
      filtrar();
    });
    cidade.addEventListener("change", filtrar);
    lista.addEventListener("click", function (ev) {
      var b = ev.target.closest(".posso button.opcao");
      if (!b) return;
      var caixa = b.closest(".posso");
      [].forEach.call(b.parentNode.querySelectorAll("button"), function (x) { x.setAttribute("aria-pressed", x === b); });
      var c = todos[parseInt(caixa.getAttribute("data-curso"), 10)];
      var q = perguntas(c), respostas = [];
      q.forEach(function (x, j) {
        var on = caixa.querySelector('button[data-q="' + j + '"][aria-pressed="true"]');
        respostas.push(on ? on.getAttribute("data-r") : null);
      });
      var res = caixa.querySelector(".resultado");
      var naos = q.filter(function (x, j) { return respostas[j] === "nao"; });
      if (naos.length) {
        res.className = "resultado atencao";
        res.textContent = naos.map(function (x) { return x.nao; }).join(" ") + " Veja outros cursos na lista, ou pergunte na unidade se há exceções.";
      } else if (respostas.indexOf(null) < 0) {
        res.className = "resultado bom";
        res.textContent = "Pelo que você respondeu, você pode se inscrever. Confirme na página oficial antes de ir.";
      } else {
        res.className = "resultado"; res.textContent = "";
      }
    });

    botoesOpcoes(el("cursos-opcoes"), site.necessidades, escolhidas, filtrar);
    preencherOnde(onde, site.locais, params.has("onde") ? params.get("onde") : (site.territorio_piloto || ""));
    onde.addEventListener("change", filtrar);
    texto.addEventListener("input", filtrar);

    lista.innerHTML = '<li class="discreto">Carregando os cursos…</li>';
    Promise.all([carregar("dados/cursos.json"), carregar("dados/guias.json").catch(function () { return { guias: [] }; })]).then(function (r) {
      todos = r[0].cursos || [];
      (r[1].guias || []).forEach(function (g) { guiasPorId[g.id] = g; });
      var cidades = {};
      todos.forEach(function (c) { if (c.modalidade !== "online") cidadesDe(c).forEach(function (x) { cidades[x] = 1; }); });
      Object.keys(cidades).sort(function (a, b) { return a.localeCompare(b, "pt"); }).forEach(function (x) {
        var op = document.createElement("option"); op.value = x; op.textContent = x;
        if (params.get("cidade") === x) op.selected = true;
        cidade.appendChild(op);
      });
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
        '<p class="vazio">Ainda não há notícias com esse tema. Escolha "Todos os temas".</p>';
    }
    tema.addEventListener("change", mostrar);
    carregar("dados/noticias.json").then(function (d) { dados = d; mostrar(); })
      .catch(function () { caixa.innerHTML = '<p class="vazio">As primeiras notícias aparecem aqui em breve.</p>'; });
  }

  // ------------------------------------------------------------ Antes de começar
  function antes() {
    var caixa = el("guias-lista"), indice = el("guias-indice");
    carregar("dados/guias.json").then(function (d) {
      var g = d.guias || [];
      if (!g.length) { caixa.innerHTML = '<p class="vazio">Os guias aparecem aqui em breve.</p>'; return; }
      indice.innerHTML = g.map(function (x) { return '<li><a href="#' + esc(x.id) + '">' + esc(x.titulo) + "</a></li>"; }).join("");
      caixa.innerHTML = g.map(function (x) {
        var info = [];
        if (x.custo) info.push("<li><strong>Quanto custa:</strong> " + esc(x.custo) + "</li>");
        if (x.tempo) info.push("<li><strong>Quanto tempo leva:</strong> " + esc(x.tempo) + "</li>");
        if (x.onde) info.push("<li><strong>Onde fazer:</strong> " + esc(x.onde) + "</li>");
        return '<section class="guia" id="' + esc(x.id) + '"><h2>' + esc(x.titulo) + "</h2>" +
          (x.para_que ? "<p>" + esc(x.para_que) + "</p>" : "") +
          "<ol>" + x.passos.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ol>" +
          (info.length ? '<ul class="guia-info">' + info.join("") + "</ul>" : "") +
          '<p class="verificado">' + (x.verificado_em ? "Conferido em " + esc(dataBonita(x.verificado_em)) + " na " : "Fonte: ") +
          '<a href="' + esc(x.fonte) + '" rel="noopener">página oficial</a>.</p></section>';
      }).join("");
      if (location.hash) { var alvo = document.querySelector(location.hash); if (alvo) alvo.scrollIntoView(); }
    }).catch(function () { caixa.innerHTML = '<p class="vazio">Os guias aparecem aqui em breve.</p>'; });
  }

  carregar("dados/site.json").then(function (site) {
    if (pagina === "antes") { antes(); return; }
    if (pagina === "inicio") inicio(site);
    else if (pagina === "cursos") cursos(site);
    else if (pagina === "noticias") noticias(site);
  });
})();
