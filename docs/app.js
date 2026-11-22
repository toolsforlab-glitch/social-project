(function () {
  "use strict";

  // capitais dos territórios: aparecem primeiro nas listas de cidades
  var CAPITAIS = ["Fortaleza", "São Luís", "Rio Branco", "Teresina", "Lisboa"];
  function ordenarCidades(lista) {
    return lista.slice().sort(function (a, b) {
      var ca = CAPITAIS.indexOf(a), cb = CAPITAIS.indexOf(b);
      if (ca >= 0 || cb >= 0) return (ca < 0 ? 99 : ca) - (cb < 0 ? 99 : cb);
      return a.localeCompare(b, "pt");
    });
  }

  // Ligações para fora do site abrem noutra aba, para a pessoa não perder o lugar onde estava.
  function marcarExternos(raiz) {
    [].forEach.call((raiz || document).querySelectorAll('a[href^="http"]'), function (a) {
      if (a.host === location.host || a.getAttribute("target")) return;
      a.setAttribute("target", "_blank");
      a.setAttribute("rel", "noopener");
      if (!a.querySelector(".so-leitor")) a.insertAdjacentHTML("beforeend", '<span class="so-leitor"> (abre em outra aba)</span>');
    });
  }
  marcarExternos(document);
  new MutationObserver(function (lista) {
    lista.forEach(function (m) { [].forEach.call(m.addedNodes, function (n) { if (n.nodeType === 1) marcarExternos(n.parentNode || n); }); });
  }).observe(document.body, { childList: true, subtree: true });

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
  function hojeIso() {
    var d = new Date();
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function dataCurtaG(iso) { var p = (iso || "").slice(0, 10).split("-"); return p.length === 3 ? p[2] + "/" + p[1] : ""; }
  // Turmas lidas das páginas oficiais: some quando passa o prazo ou, sem prazo, quando a turma começa
  function turmasAtuais(c) {
    var h = hojeIso();
    return (c.turmas || []).filter(function (t) {
      if (t.prazo) return t.prazo >= h;
      return !t.inicio || t.inicio > h;
    });
  }
  // Prazos a terminar: dias que faltam até ao fim das inscrições (0 = hoje). Só com prazo comprovado.
  var DIAS_ALERTA = 3;
  function diasAte(iso) {
    if (!iso) return null;
    var p = iso.slice(0, 10).split("-"), d = new Date(+p[0], +p[1] - 1, +p[2]);
    var h = new Date(); h = new Date(h.getFullYear(), h.getMonth(), h.getDate());
    return Math.round((d - h) / 864e5);
  }
  function prazoProximo(c) {
    var turmas = turmasAtuais(c);
    var prazos = (c.turmas || []).length ? turmas.map(function (t) { return t.prazo; }).filter(Boolean)
                                          : (c.inscricoes_ate ? [c.inscricoes_ate] : []);
    prazos = prazos.filter(function (x) { var n = diasAte(x); return n !== null && n >= 0; }).sort();
    return prazos[0] || "";
  }
  function terminaEmBreve(c) { var n = diasAte(prazoProximo(c)); return n !== null && n >= 0 && n <= DIAS_ALERTA; }
  function quandoTermina(iso) {
    var n = diasAte(iso);
    return n === 0 ? "Último dia: inscrições até hoje" : n === 1 ? "Últimos dias: inscrições até amanhã"
         : "Últimos dias: inscrições até " + dataCurtaG(iso);
  }
  // «Lembrar-me»: evento de calendário (.ics) no dia do fim das inscrições, com aviso na véspera ao meio-dia.
  // Fica no telemóvel da pessoa: o site não guarda nenhum dado.
  function icsTexto(t) { return String(t || "").replace(/\\/g, "\\\\").replace(/([,;])/g, "\\$1").replace(/\r?\n/g, "\\n"); }
  function lembrarHtml(titulo, prazo, link, sitio) {
    if (!prazo || !(diasAte(prazo) >= 1)) return "";
    var d = prazo.slice(0, 10).replace(/-/g, "");
    var p = prazo.slice(0, 10).split("-"), fim = new Date(+p[0], +p[1] - 1, +p[2] + 1);
    var dfim = fim.getFullYear() + ("0" + (fim.getMonth() + 1)).slice(-2) + ("0" + fim.getDate()).slice(-2);
    var agora = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
    var resumo = "Último dia de inscrição: " + titulo;
    var ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Cursos gratuitos//PT-BR", "CALSCALE:GREGORIAN", "BEGIN:VEVENT",
      "UID:" + d + "-" + Math.abs(String(titulo + link).split("").reduce(function (a, ch) { return (a * 31 + ch.charCodeAt(0)) | 0; }, 7)) + "@cursos-gratuitos",
      "DTSTAMP:" + agora, "DTSTART;VALUE=DATE:" + d, "DTEND;VALUE=DATE:" + dfim,
      "SUMMARY:" + icsTexto(resumo),
      "DESCRIPTION:" + icsTexto((sitio ? sitio + ". " : "") + "Inscreva-se até hoje. Confirme na página oficial: " + link),
      "URL:" + link, "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT12H",
      "DESCRIPTION:" + icsTexto("Amanhã é o último dia de inscrição: " + titulo), "END:VALARM", "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    var nome = "inscricao-" + titulo.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").slice(0, 40) + ".ics";
    return '<a class="lembrar" href="data:text/calendar;charset=utf-8,' + encodeURIComponent(ics) + '" download="' + esc(nome) + '">' +
      "Adicionar o prazo à agenda do celular</a>";
  }
  // turno pelo horário de início da turma: antes das 12h manhã, até às 18h tarde, depois noite
  function turnosDe(c) {
    if (!(c.turmas || []).length) return c.turnos || [];
    return turmasAtuais(c).map(function (t) {
      var h = parseInt((t.horario || "").split(":")[0], 10);
      return isNaN(h) ? "" : h < 12 ? "Manhã" : h < 18 ? "Tarde" : "Noite";
    }).filter(Boolean);
  }
  function turmaHtml(t, comBotao, tituloCurso) {
    var l = ["<strong>" + esc(t.unidade || (t.local && t.local.nome) || "") + "</strong>" + (t.cidade ? " (" + esc(t.cidade) + ")" : "")];
    var quando = [t.inicio ? dataCurtaG(t.inicio) + (t.fim ? " a " + dataCurtaG(t.fim) : "") : "", t.horario, t.dias]
      .filter(Boolean).join(" · ");
    if (quando) l.push(esc(quando));
    var urgente = t.prazo && diasAte(t.prazo) >= 0 && diasAte(t.prazo) <= DIAS_ALERTA;
    l.push(t.prazo ? '<span class="prazo' + (urgente ? ' urgente' : '') + '">' + (urgente ? esc(quandoTermina(t.prazo)) : "Inscrições até " + esc(dataBonita(t.prazo))) + "</span>"
           : t.inscricao === "pagina" ? '<span class="prazo">Prazo de inscrição não indicado: confirme na página da turma</span>'
           : '<span class="prazo">Inscrições abertas. O prazo não está indicado: inscreva-se antes do início da turma</span>');
    if (t.info) l.push(esc(t.info));
    if (t.inscricao === "online") l.push(t.info ? "Inscrição pela internet." : "Aulas on-line ao vivo. Inscrição pela internet.");
    if (t.inscricao === "presencial") l.push("Inscrição presencial" + (t.local_texto ? " em: " + esc(t.local_texto) : " na unidade"));
    if (t.inscricao !== "pagina" && t.telefone) l.push("Dúvidas: " + esc(t.telefone));
    var quem = [t.idade_minima ? t.idade_minima + " anos ou mais" : "", t.escolaridade ? (t.inscricao === "pagina" ? "Escolaridade: " : "Requisito: ") + t.escolaridade.replace(/\.$/, "") : ""]
      .filter(Boolean).join(" · ");
    if (quem) l.push(esc(quem));
    if (t.documentos) l.push("Documentos: " + esc(t.documentos.replace(/\.$/, "")));
    // turma com local de inscrição próprio (Centec presencial): não mostrar também a morada da unidade
    var u = (t.inscricao === "presencial" && t.local_texto) ? null : t.local;
    if (u) {
      var morada = [u.morada, u.bairro, u.municipio].filter(Boolean).join(", ");
      if (morada) l.push(esc(morada));
      if (u.telefone) l.push("Telefone " + esc(u.telefone));
    }
    if (comBotao) {
      var b = destinoBotao(t.destino, true, t.inscricao);
      if (b.nota) l.push('<span class="guia-link">' + b.nota + "</span>");
      l.push('<a class="botao" href="' + esc(t.link) + '" rel="noopener">' + esc(b.rotulo) + "</a>");
    }
    if (comBotao && tituloCurso) l.push(lembrarHtml(tituloCurso, t.prazo, t.link, [t.unidade, t.cidade].filter(Boolean).join(", ")));
    return "<li>" + l.join("<br>") + "</li>";
  }

  // Botão e nota a partir do destino do link (paginas.py: curso, acesso, lista, pdf, formulario, inicio, geral).
  // Regra do projeto: quem clica tem de saber que página vai abrir e o que fazer lá.
  function destinoBotao(d, emTurma, inscricao, jaTemGuiaGovbr) {
    d = d || {};
    var conta = d.conta || "";
    var govbr = /gov\.br/i.test(conta);
    var extra = d.nota ? " " + esc(d.nota) : "";
    var umaConta = /^conta\b/i.test(conta) ? "uma " + conta : "uma conta em " + conta;
    var precisaConta = conta && d.tipo !== "acesso" ? " Para se inscrever, é preciso entrar com " + esc(umaConta) + "." +
      (govbr && !jaTemGuiaGovbr ? ' Veja como criar a conta e subir de nível em <a href="antes.html#govbr">Antes de começar</a>.' : "") : "";
    switch (d.tipo) {
      case "curso":
        return { rotulo: emTurma ? "Ver esta turma e se inscrever" : "Ver o curso e se inscrever", nota: (precisaConta + extra).trim() };
      case "acesso":
        return { rotulo: "Entrar no " + (conta || "site") + " e se inscrever",
                 nota: "O botão abre a página de acesso" + (conta ? " do " + esc(conta) : "") + ", não o curso. Entre com a sua conta." +
                       (d.nota ? extra : " Se ainda não tem conta, é preciso criar uma nessa página. Depois de entrar, clique outra vez no botão.") };
      case "lista":
        return { rotulo: "Abrir a lista de cursos", nota: "O botão abre uma lista geral, não o curso. " +
                 (d.procurar ? "Na lista, procure “" + esc(d.procurar) + "”." : "Na lista, procure o nome do curso.") + precisaConta + extra };
      case "inicio":
        return { rotulo: "Abrir o site oficial", nota: "O botão abre a página inicial do site, não o curso. " +
                 (d.procurar ? "Procure “" + esc(d.procurar) + "”." : "Procure o nome do curso.") + precisaConta + extra };
      case "pdf":
        return { rotulo: "Ver o edital (PDF)", nota: "O botão abre o documento completo, em PDF." + extra };
      case "formulario":
        return { rotulo: "Abrir o formulário de inscrição", nota: "O botão abre o formulário de inscrição deste curso." + precisaConta + extra };
      case "geral":
        return { rotulo: "Ver na página oficial", nota: "A página oficial não mostra este curso diretamente: confirme com a entidade antes de ir." };
      default:
        return { rotulo: inscricao === "online" ? "Fazer a inscrição on-line" : emTurma ? "Ver na página oficial" : "Procurar este curso na página oficial", nota: "" };
    }
  }

  // Nota do destino em texto simples (para a ficha impressa e o texto do WhatsApp)
  function notaSimples(d, emTurma) {
    if (!d || d.tipo === "curso" && !d.conta) return "";
    return destinoBotao(d, emTurma, "").nota.replace(/<[^>]+>/g, "").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&#39;/g, "'");
  }
  var GRATUIDADE_AVISO = "A página oficial não diz por escrito que este curso é gratuito: confirme antes de se inscrever";
  // Descrição: um texto reescrito pela rotina mostra-se como resumo; o texto copiado da página oficial, sem rótulo.
  function descricaoHtml(c) {
    if (!c.descricao) return "";
    return '<p class="descricao">' + (c.descricao_origem === "pagina" ? "" : '<span class="rotulo">Em resumo:</span> ') +
      esc(c.descricao) + "</p>";
  }
  function idCartao(c, i) { return "curso-" + (c.id ? String(c.id).replace(/[^\w-]/g, "") : i); }

  function preencherOnde(select, locais, valor) {
    // o site é para o país todo: os estados aparecem só pelo nome («Ceará», não «Brasil – Ceará») e por ordem
    // alfabética, depois de «Mostrar tudo» e «On-line» (pedido do responsável, 22/11/2026)
    var html = '<option value="">Mostrar tudo</option>';
    var nome = function (l) { return String(l.rotulo || "").replace(/^Brasil\s*[–-]\s*/, ""); };
    var online = locais.filter(function (l) { return l.id === "online"; });
    var estados = locais.filter(function (l) { return l.id !== "online"; })
      .sort(function (a, b) { return nome(a).localeCompare(nome(b), "pt-BR"); });
    online.concat(estados).forEach(function (l) {
      html += '<option value="' + esc(l.id) + '"' + (l.id === valor ? " selected" : "") + ">" + esc(nome(l)) + "</option>";
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

    // "Inscrições terminando": cursos do lugar escolhido cujo prazo mais próximo (turma ou curso) acaba nos
    // próximos 10 dias. Sem nenhum, diz isso (em vez de deixar o bloco vazio) e leva à lista completa.
    var caixa = el("inicio-ultimos"), todos = null;
    function desenharUltimos() {
      if (!todos) return;
      var o = onde.value;
      var ultimos = todos.filter(function (c) {
        if (o === "online" && c.modalidade !== "online") return false;
        // estado escolhido: só os cursos presenciais desse estado; os on-line têm a opção própria «On-line»
        if (o && o !== "online" && (c.modalidade === "online" || c.local !== o)) return false;
        var n = diasAte(prazoProximo(c));
        return n !== null && n >= 0 && n <= 10;
      }).sort(function (a, b) { return prazoProximo(a).localeCompare(prazoProximo(b)); }).slice(0, 5);
      if (!ultimos.length) {
        caixa.innerHTML = '<li class="vazio">' + (o === "online"
          ? "Nenhum curso on-line com inscrições terminando nos próximos 10 dias. Os cursos on-line costumam ficar abertos por mais tempo."
          : "Nenhum curso com inscrições terminando nos próximos 10 dias neste lugar.") +
          ' <a href="' + ver.getAttribute("href") + '">Ver todos os cursos</a></li>';
        return;
      }
      caixa.innerHTML = ultimos.map(function (c) {
        var sitio = c.modalidade === "online" ? "On-line" : [c.cidade, c.regiao].filter(Boolean)[0] || "";
        return '<li class="noticia"><h3><a href="cursos.html' + (o ? "?onde=" + o : "") + "#" + idCartao(c, 0) + '">' + esc(c.titulo) + "</a></h3>" +
          '<p class="meta">' + (sitio ? esc(sitio) + ". " : "") + "Inscrições até " + esc(dataBonita(prazoProximo(c))) + "</p></li>";
      }).join("");
    }
    onde.addEventListener("change", desenharUltimos);
    carregar("dados/cursos.json").then(function (d) {
      todos = d.cursos || [];
      desenharUltimos();
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
    var marcaEscolhida = params.get("marca") || "";
    var certificado = el("cursos-certificado");
    var duracao = el("cursos-duracao");
    if (certificado) certificado.checked = params.get("certificado") === "gratuito" || marcaEscolhida === "cert-gratuito";
    if (duracao && ["curto", "medio", "longo"].indexOf(params.get("duracao")) >= 0) duracao.value = params.get("duracao");
    if (marcaEscolhida === "cert-gratuito") marcaEscolhida = "";  // links antigos: agora é o filtro «Certificado»
    var marcaSumiu = "";  // marca de um link antigo que já nenhum curso tem
    var cidade = el("cursos-cidade");
    var notaBarreiras = el("cursos-nota-barreiras");
    var rotulos = {};
    site.necessidades.forEach(function (n) { rotulos[n.id] = n.rotulo; });
    var nomesLocal = {};
    site.locais.forEach(function (l) { nomesLocal[l.id] = l.rotulo; });

    // Busca por palavra: cada palavra digitada tem de aparecer como palavra inteira no texto do curso, não dentro de
    // outra («excel» não acha «excelência»). Aceita até 3 letras a mais no fim, para plurais e flexões
    // («curso» acha «cursos», «eletricist» acha «eletricista»). Com várias palavras, todas têm de aparecer.
    function bateBusca(alvo, busca) {
      var palavras = alvo.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
      return busca.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).every(function (termo) {
        return palavras.some(function (p) {
          return p === termo || (p.indexOf(termo) === 0 && p.length - termo.length <= 3 && termo.length >= 3);
        });
      });
    }
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
      if (c.idade_maxima) q.push({ p: "Você tem " + c.idade_maxima + " anos ou menos?", nao: "O curso é para pessoas com até " + c.idade_maxima + " anos." });
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
      var turmas = turmasAtuais(c);
      var temTurmas = (c.turmas || []).length > 0;
      var factos = [];
      // marcas que filtram a lista quando se clica: data-filtro="tipo:valor" (onde, facilita ou marca)
      function marca(cls, txt, filtro) { return '<span class="' + cls + '" data-filtro="' + esc(filtro) + '">' + esc(txt) + "</span>"; }
      if (c.modalidade === "online") factos.push(marca("local", "On-line", "onde:online"));
      else {
        var partes = [c.cidade, c.regiao].filter(Boolean).filter(function (v, i, a) { return a.indexOf(v) === i; });
        var sitio = partes.join(", ") || nomesLocal[c.local] || "";
        var txtLocal = (c.modalidade === "misto" ? "Presencial e on-line" : "Presencial") + (sitio ? ": " + sitio : "");
        factos.push(c.local ? marca("local", txtLocal, "onde:" + c.local) : txtLocal);
      }
      if (c.certificado === "gratuito") factos.push(marca("bom", "Certificado gratuito", "marca:cert-gratuito"));
      else if (c.certificado === "pago") factos.push('<span class="atencao">Certificado pago</span>');
      // regra do projeto: gratuidade só com frase da página que diga que não há custo; sem ela, avisa-se
      if (c.gratuidade_comprovada === false) factos.push(marca("atencao", "Gratuidade por confirmar", "marca:grat-confirmar"));
      var breve = terminaEmBreve(c);
      if (breve) factos.unshift(marca("urgente", quandoTermina(prazoProximo(c)), "facilita:fecha_breve"));
      if (temTurmas) {
        factos.push('<span class="bom">' + (turmas.length === 1 ? "1 turma com inscrições abertas" : turmas.length + " turmas com inscrições abertas") + "</span>");
      } else {
        if (c.inscricoes_ate && !breve) factos.push('<span class="atencao">Inscrições até ' + esc(dataBonita(c.inscricoes_ate)) + "</span>");
        else if (c.data_por_confirmar) factos.push('<span class="atencao">Confirme a data na página oficial</span>');
        if (c.situacao === "Por confirmar") factos.push('<span class="atencao">Inscrições por confirmar</span>');
        if (c.inicio) factos.push("Começa em " + esc(dataBonita(c.inicio)));
        (c.turnos || []).forEach(function (t) { if (TURNO[t]) factos.push(t === "Noite" ? marca("local", TURNO[t], "facilita:noite") : TURNO[t]); });
      }
      (c.etiquetas || []).forEach(function (e) { factos.push(marca("publico", e.texto, "marca:pub:" + e.texto)); });
      (c.acessibilidade || []).forEach(function (e) { factos.push(marca("acessivel", e.texto, "marca:acc:" + e.texto)); });
      if (c.ajuda && !/^n[aã]o/i.test(c.ajuda)) factos.push(marca("bom", c.ajuda, "facilita:ajuda"));
      else if (c.ajuda) factos.push('<span class="bom">' + esc(c.ajuda) + "</span>");
      if (c.duracao) factos.push(esc(c.duracao));
      var factosHtml = factos.map(function (f) {
        var mf = f.match(/^<span class="(\w+)" data-filtro="([^"]*)">(.*)<\/span>$/);
        if (mf) return '<li class="' + mf[1] + ' filtravel"><button type="button" class="filtro" data-filtro="' + mf[2] +
          '" title="Mostrar só os cursos assim">' + mf[3] + "</button></li>";
        var m = f.match(/^<span class="(\w+)">(.*)<\/span>$/);
        return m ? '<li class="' + m[1] + '">' + m[2] + "</li>" : "<li>" + (f.indexOf("<") >= 0 ? f : esc(f)) + "</li>";
      }).join("");
      var condicoes = [];
      if (c.exclusivo_para) condicoes.push(esc(c.exclusivo_para));
      (c.etiquetas || []).forEach(function (e) { condicoes.push("Sobre as vagas, a fonte diz: “" + esc(e.frase.replace(/[.\s]+$/, "")) + "”"); });
      var frasesAcess = (c.acessibilidade || []).map(function (e) { return e.frase; }).filter(function (f, i, a) { return a.indexOf(f) === i; });
      frasesAcess.forEach(function (f) { condicoes.push("Sobre acessibilidade, a fonte diz: “" + esc(f.replace(/[.\s]+$/, "")) + "”"); });
      if (c.gratuidade_comprovada === false) condicoes.push(GRATUIDADE_AVISO);
      if (c.requisitos) condicoes.push("Requisitos: " + esc(c.requisitos));
      // com turmas, os documentos são os de cada turma
      if (c.documentos && !temTurmas) condicoes.push("Documentos: " + esc(c.documentos.replace(/\.$/, "")));
      // O título nunca é uma ligação (igual em todos os cursos): para ir ao site oficial usam-se os botões,
      // que dizem para onde levam.
      return '<li class="curso" id="' + idCartao(c, i) + '"><h3>' + esc(c.titulo) + "</h3>" +
        (c.entidade ? '<p class="entidade">' + esc(c.entidade) + "</p>" : "") +
        descricaoHtml(c) +
        '<ul class="factos">' + factosHtml + "</ul>" +
        (condicoes.length ? '<p class="condicao">' + condicoes.join(". ") + "</p>" : "") +
        posso(c, i) + antesHtml(c) +
        (temTurmas ? '<div class="onde turmas"><p class="onde-titulo">Turmas com inscrições abertas</p><ul>' +
          turmas.map(function (t) { return turmaHtml(t, true, c.titulo); }).join("") + "</ul>" +
"</div>" :
        c.onde_inscrever && c.onde_inscrever.length ? '<div class="onde"><p class="onde-titulo">Onde se inscrever</p><ul>' +
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
        (!temTurmas && c.como_me_inscrever && c.como_me_inscrever.length ? '<details class="passos"><summary>Como se inscrever</summary><ol>' +
          c.como_me_inscrever.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ol></details>" : "") +
        (temTurmas ? '<a class="botao secundario" href="' + esc(c.url) + '" rel="noopener">' +
                     ((c.destino || {}).tipo === "lista" ? "Ver a lista completa de cursos" : (c.destino || {}).tipo === "pdf" ? "Ver o edital (PDF)" : "Ver outras turmas na página oficial") + "</a>"
                   : (function () {
                       var b = destinoBotao(c.destino, false, "", (c.antes || []).indexOf("govbr") >= 0);
                       return (b.nota ? '<p class="guia-link">' + b.nota + "</p>" : "") +
                         '<a class="botao secundario" href="' + esc(c.url) + '" rel="noopener">' + esc(b.rotulo) + "</a>";
                     })()) +
        (!temTurmas ? lembrarHtml(c.titulo, c.inscricoes_ate, c.url, c.modalidade === "online" ? "On-line" : c.cidade) : "") +
        '<p class="verificado">' + (c.verificado_em ? "Verificado em " + esc(dataBonita(c.verificado_em)) + ". " : "") +
        "Confirme sempre na página oficial antes de ir.</p></li>";
    }

    // horas do curso a partir do texto da duração («10 horas», «20h/aula», «Em média 6 horas»); null se não houver
    function horasDe(c) {
      var m = /(\d+(?:[.,]\d+)?)\s*(h\b|h\/|horas?)/i.exec(c.duracao || "");
      return m ? parseFloat(m[1].replace(",", ".")) : null;
    }
    function naDuracao(c, faixa) {
      var h = horasDe(c);
      if (h === null) return false;
      return faixa === "curto" ? h <= 4 : faixa === "medio" ? h > 4 && h <= 20 : h > 20;
    }
    // «no Ceará», «na Bahia», «em Pernambuco», «em Portugal»
    function noLugar(nome) {
      var no = ["Acre", "Amapá", "Amazonas", "Ceará", "Distrito Federal", "Espírito Santo", "Maranhão", "Mato Grosso",
        "Mato Grosso do Sul", "Pará", "Paraná", "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Tocantins"];
      return (no.indexOf(nome) >= 0 ? "no " : ["Bahia", "Paraíba"].indexOf(nome) >= 0 ? "na " : "em ") + nome;
    }
    function filtrar() {
      var o = onde.value;
      var t = semAcentos(texto.value.trim());
      var res = todos.filter(function (c) {
        if (escolhidas.length && !c.necessidades.some(function (n) { return escolhidas.indexOf(n) >= 0; })) return false;
        if (o === "online" && c.modalidade !== "online") return false;
        // estado escolhido: só os cursos presenciais desse estado; os on-line têm a opção própria «On-line»
        if (o && o !== "online" && (c.modalidade === "online" || c.local !== o)) return false;
        if (barreiras.indexOf("noite") >= 0 && turnosDe(c).indexOf("Noite") < 0) return false;
        if (barreiras.indexOf("sem_internet") >= 0 && c.internet !== "Não") return false;
        if (barreiras.indexOf("sem_escolaridade") >= 0 && ["Nenhuma", "Saber ler e escrever"].indexOf(c.escolaridade) < 0) return false;
        if (barreiras.indexOf("ajuda") >= 0 && (!c.ajuda || /^n[aã]o/i.test(c.ajuda))) return false;
        if (barreiras.indexOf("reservadas") >= 0 && !(c.etiquetas || []).length) return false;
        if (barreiras.indexOf("acessivel") >= 0 && !(c.acessibilidade || []).length) return false;
        if (barreiras.indexOf("fecha_breve") >= 0 && !terminaEmBreve(c)) return false;
        if (marcaEscolhida && marcasDe(c).indexOf(marcaEscolhida) < 0) return false;
        if (certificado && certificado.checked && c.certificado !== "gratuito") return false;
        if (duracao && duracao.value && !naDuracao(c, duracao.value)) return false;
        if (cidade.value && cidadesDe(c).indexOf(cidade.value) < 0) return false;
        if (t) {
          var alvo = semAcentos([c.titulo, c.descricao, c.entidade, c.cidade, c.regiao].join(" "));
          if (!bateBusca(alvo, t)) return false;
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
      if (o && o !== "online" && res.length) resumo += res.length === 1 ? " presencial" : " presenciais";
      contagem.textContent = res.length ? resumo : "";
      // filtros ativos, visíveis no topo da lista (na coluna da esquerda podem ficar fora da vista), cada um com ✕
      var ativos = [];
      escolhidas.forEach(function (id) {
        var n = (site.necessidades || []).filter(function (x) { return x.id === id; })[0];
        ativos.push(["quero:" + id, n ? n.rotulo : id]);
      });
      barreiras.forEach(function (id) {
        var bt = ulBarreiras.querySelector('[data-barreira="' + id + '"]');
        ativos.push(["facilita:" + id, bt ? bt.textContent : id]);
      });
      if (duracao && duracao.value) ativos.push(["duracao", duracao.options[duracao.selectedIndex].text]);
      if (certificado && certificado.checked) ativos.push(["certificado", "Certificado gratuito"]);
      if (cidade.value) ativos.push(["cidade", cidade.value]);
      if (texto.value.trim()) ativos.push(["texto", "“" + texto.value.trim() + "”"]);
      var caixaAtivos = el("cursos-ativos");
      if (caixaAtivos) {
        var semPresencial = false;
        caixaAtivos.hidden = !ativos.length && !semPresencial;
        caixaAtivos.innerHTML = (ativos.length ? '<span class="filtros-ativos-titulo">Filtros escolhidos:</span> ' +
          ativos.map(function (a) {
            return '<button type="button" class="filtro-ativo" data-tirar="' + esc(a[0]) + '" aria-label="Tirar o filtro ' +
              esc(a[1]) + '">' + esc(a[1]) + ' <span aria-hidden="true">✕</span></button>';
          }).join(" ") + (ativos.length > 1 ? ' <button type="button" class="filtro-limpar" data-tirar="tudo">Limpar todos</button>' : "") : "") +
          (semPresencial ? '<p class="discreto">Não há cursos presenciais ' + esc(noLugar(onde.options[onde.selectedIndex].text.replace(/^Brasil\s*[–-]\s*/, ""))) +
            (ativos.length ? " com estas escolhas" : " no momento") + ". Os cursos abaixo são on-line e servem em qualquer lugar.</p>" : "");
      }
      notaBarreiras.hidden = !barreiras.length && !(certificado && certificado.checked) && !(duracao && duracao.value);
      // «Terminam em breve»: no topo, os cursos desta escolha cujas inscrições acabam nos próximos 3 dias
      var breves = res.filter(terminaEmBreve).sort(function (a, b) { return prazoProximo(a).localeCompare(prazoProximo(b)); });
      var caixaBreve = el("cursos-breve");
      if (caixaBreve) {
        // só aparece quando há algum filtro escolhido; na entrada (Mostrar tudo, sem filtros) fica escondido
        var algumFiltro = !!o || ativos.length > 0 || !!marcaEscolhida;
        caixaBreve.hidden = !algumFiltro || !breves.length || barreiras.indexOf("fecha_breve") >= 0;
        el("cursos-breve-lista").innerHTML = breves.map(function (c) {
          var sitio = c.modalidade === "online" ? "On-line" : cidadesDe(c).filter(function (v, i, a) { return a.indexOf(v) === i; }).slice(0, 3).join(", ") || c.cidade || "";
          return '<li><a href="#' + idCartao(c, todos.indexOf(c)) + '">' + esc(c.titulo) + "</a> " +
            '<span class="discreto">' + (sitio ? esc(sitio) + ". " : "") + esc(quandoTermina(prazoProximo(c)).replace(/^Últimos? dias?: i/, "I")) + "</span></li>";
        }).join("");
      }
      lista.innerHTML = res.length ? res.map(function (c) { return cursoHtml(c, todos.indexOf(c)); }).join("") :
        (o && o !== "online"
          ? '<li class="vazio">Não há cursos presenciais ' + esc(noLugar(onde.options[onde.selectedIndex].text.replace(/^Brasil\s*[–-]\s*/, ""))) +
            (cidade.value ? " em " + esc(cidade.value) : "") + (ativos.length ? " com estas escolhas" : "") +
            ' no momento. Os cursos on-line servem em qualquer lugar. <button type="button" class="filtro botao secundario pequeno" data-filtro="onde:online">Ver os cursos on-line</button></li>'
          : '<li class="vazio">Não há cursos com essas opções no momento. Tente escolher menos opções ou "Mostrar tudo" em "Onde você está?". A lista é atualizada todo dia.</li>');

      var q = new URLSearchParams();
      if (escolhidas.length) q.set("quero", escolhidas.join(","));
      if (o) q.set("onde", o);
      if (barreiras.length) q.set("facilita", barreiras.join(","));
      if (marcaEscolhida) q.set("marca", marcaEscolhida);
      if (certificado && certificado.checked) q.set("certificado", "gratuito");
      if (duracao && duracao.value) q.set("duracao", duracao.value);
      var aviso = el("cursos-marca");
      if (aviso) {
        aviso.hidden = !marcaEscolhida && !marcaSumiu;
        aviso.innerHTML = marcaEscolhida ? "Mostrando só os cursos com: <strong>" + esc(textoMarca(marcaEscolhida)) + "</strong> " +
          '<button type="button" class="botao secundario pequeno" id="cursos-marca-limpar">Mostrar todos os cursos</button>' :
          marcaSumiu ? "Nenhum curso tem mais a marca <strong>" + esc(marcaSumiu) + "</strong>, por isso mostramos todos os cursos." : "";
      }
      if (cidade.value) q.set("cidade", cidade.value);
      history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q.toString() : ""));
    }

    function marcasDe(c) {
      return (c.certificado === "gratuito" ? ["cert-gratuito"] : [])
        .concat(c.gratuidade_comprovada === false ? ["grat-confirmar"] : [])
        .concat((c.etiquetas || []).map(function (e) { return "pub:" + e.texto; }))
        .concat((c.acessibilidade || []).map(function (e) { return "acc:" + e.texto; }));
    }
    function textoMarca(m) {
      return m === "cert-gratuito" ? "Certificado gratuito" : m === "grat-confirmar" ? "Gratuidade por confirmar" : m.replace(/^(pub|acc):/, "");
    }
    function cidadesDe(c) {
      if ((c.turmas || []).length) return turmasAtuais(c).map(function (t) { return t.cidade; }).filter(Boolean);
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
    var caixaAtivosEv = el("cursos-ativos");
    if (caixaAtivosEv) caixaAtivosEv.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-tirar]");
      if (!b) return;
      var partes = b.getAttribute("data-tirar").split(":"), tipo = partes.shift(), valor = partes.join(":");
      var tirarQuero = function (id) {
        var i = escolhidas.indexOf(id);
        if (i >= 0) escolhidas.splice(i, 1);
        var bt = el("cursos-opcoes").querySelector('[data-id="' + id + '"]');
        if (bt) bt.setAttribute("aria-pressed", "false");
      };
      var tirarFacilita = function (id) {
        var i = barreiras.indexOf(id);
        if (i >= 0) barreiras.splice(i, 1);
        var bt = ulBarreiras.querySelector('[data-barreira="' + id + '"]');
        if (bt) bt.setAttribute("aria-pressed", "false");
      };
      if (tipo === "quero") tirarQuero(valor);
      else if (tipo === "facilita") tirarFacilita(valor);
      else if (tipo === "duracao" && duracao) duracao.value = "";
      else if (tipo === "certificado" && certificado) certificado.checked = false;
      else if (tipo === "cidade") cidade.value = "";
      else if (tipo === "texto") texto.value = "";
      else if (tipo === "tudo") {
        escolhidas.slice().forEach(tirarQuero);
        barreiras.slice().forEach(tirarFacilita);
        if (duracao) duracao.value = "";
        if (certificado) certificado.checked = false;
        cidade.value = "";
        texto.value = "";
      }
      filtrar();
    });
    // clicar numa marca do curso (ex.: On-line, Certificado gratuito, Para mulheres) filtra a lista por ela
    lista.addEventListener("click", function (ev) {
      var f = ev.target.closest("button.filtro");
      if (!f) return;
      var partes = f.getAttribute("data-filtro").split(":"), tipo = partes.shift(), valor = partes.join(":");
      if (tipo === "onde") { onde.value = valor; preencherCidades(""); }
      else if (tipo === "facilita") {
        if (barreiras.indexOf(valor) < 0) barreiras.push(valor);
        [].forEach.call(ulBarreiras.querySelectorAll("button"), function (b) {
          b.setAttribute("aria-pressed", barreiras.indexOf(b.getAttribute("data-barreira")) >= 0);
        });
      } else if (tipo === "marca" && valor === "cert-gratuito" && certificado) { certificado.checked = true; }
      else if (tipo === "marca") { marcaEscolhida = valor; marcaSumiu = ""; }
      filtrar();
      contagem.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    document.addEventListener("click", function (ev) {
      if (ev.target.id !== "cursos-marca-limpar") return;
      marcaEscolhida = ""; marcaSumiu = ""; filtrar();
    });
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
    // ao entrar na busca sem filtros no link, o padrão é «Mostrar tudo» (pedido do responsável, 22/11/2026)
    preencherOnde(onde, site.locais, params.has("onde") ? params.get("onde") : "");
    onde.addEventListener("change", function () { preencherCidades(cidade.value); filtrar(); });
    texto.addEventListener("input", filtrar);
    if (certificado) certificado.addEventListener("change", filtrar);
    if (duracao) duracao.addEventListener("change", filtrar);

    // cidades do território escolhido em "Onde você está?": a capital primeiro, depois as outras por ordem alfabética
    function preencherCidades(escolhida) {
      var o = onde.value, cidades = {};
      // cursos on-line não têm cidade: o campo Cidade some e deixa de filtrar
      cidade.closest(".campo").hidden = o === "online";
      if (o === "online") escolhida = "";
      todos.forEach(function (c) {
        if (c.modalidade === "online" || (o && o !== "online" && c.local !== o)) return;
        cidadesDe(c).forEach(function (x) { cidades[x] = 1; });
      });
      cidade.innerHTML = '<option value="">Qualquer cidade</option>';
      ordenarCidades(Object.keys(cidades)).forEach(function (x) {
        var op = document.createElement("option"); op.value = x; op.textContent = x;
        if (escolhida === x) op.selected = true;
        cidade.appendChild(op);
      });
    }

    lista.innerHTML = '<li class="discreto">Carregando os cursos…</li>';
    Promise.all([carregar("dados/cursos.json"), carregar("dados/guias.json").catch(function () { return { guias: [] }; })]).then(function (r) {
      todos = r[0].cursos || [];
      // link com uma marca que nenhum curso tem mais (ex.: todas as gratuidades já confirmadas): mostrar todos e dizer porquê
      if (marcaEscolhida && !todos.some(function (c) { return marcasDe(c).indexOf(marcaEscolhida) >= 0; })) {
        marcaSumiu = textoMarca(marcaEscolhida); marcaEscolhida = "";
      }
      (r[1].guias || []).forEach(function (g) { guiasPorId[g.id] = g; });
      preencherCidades(params.get("cidade") || "");
      filtrar();
      // vindo da página inicial (#curso-…): ir ao cartão desse curso
      if (location.hash && /^#curso-/.test(location.hash)) {
        var alvo = document.getElementById(location.hash.slice(1));
        if (alvo) { alvo.scrollIntoView(); alvo.classList.add("destacado"); }
      }
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

  // ------------------------------------------------------------ Para quem encaminha
  function encaminhar(site) {
    var params = new URLSearchParams(location.search);
    var cidade = el("kit-cidade"), comOnline = el("kit-online"), lista = el("kit-lista");
    var acoes = el("kit-acoes"), copiado = el("kit-copiado");
    var todos = [], guias = {}, atualizado = "";
    var TURNO = { "Manhã": "de manhã", "Tarde": "à tarde", "Noite": "à noite" };
    var base = (site.url_site || (location.origin + location.pathname.replace(/[^/]*$/, ""))).replace(/\/?$/, "/");

    function cidadesDe(c) {
      if ((c.turmas || []).length) return turmasAtuais(c).map(function (t) { return t.cidade; }).filter(Boolean);
      return [c.cidade].concat((c.onde_inscrever || []).map(function (u) { return u.municipio; })).filter(Boolean);
    }
    function turmasDaCidade(c) {
      return turmasAtuais(c).filter(function (t) { return t.cidade === cidade.value; });
    }
    function dataCurta(iso) { var p = (iso || "").slice(0, 10).split("-"); return p.length === 3 ? p[2] + "/" + p[1] : ""; }
    function selecionados() {
      var cid = cidade.value;
      if (!cid) return [];
      return todos.filter(function (c) {
        if (c.situacao !== "Aberto" || c.em_revisao) return false;
        if (c.modalidade === "online") return comOnline.checked;
        return cidadesDe(c).indexOf(cid) >= 0;
      }).sort(function (a, b) { return (a.modalidade === "online") - (b.modalidade === "online"); });
    }
    function unidadesDaCidade(c) {
      var u = (c.onde_inscrever || []).filter(function (x) { return x.municipio === cidade.value; });
      return u.length ? u : (c.onde_inscrever || []);
    }
    // o turno está guardado por curso; se o curso tem várias unidades e vários turnos, não se sabe qual é o desta cidade
    function varia(c) { return (c.onde_inscrever || []).length > 1 && (c.turnos || []).length > 1; }
    function turnoSeguro(c) {
      return varia(c) ? "" : (c.turnos || []).map(function (t) { return TURNO[t]; }).filter(Boolean).join(" ou ");
    }
    function quemPode(c) {
      var l = [];
      if (c.idade_minima && c.idade_maxima) l.push("de " + c.idade_minima + " a " + c.idade_maxima + " anos");
      else if (c.idade_minima) l.push(c.idade_minima + " anos ou mais");
      else if (c.idade_maxima) l.push("até " + c.idade_maxima + " anos");
      if (c.escolaridade && c.escolaridade !== "Nenhuma") l.push(c.escolaridade.toLowerCase());
      if (c.renda) l.push(c.renda.charAt(0).toLowerCase() + c.renda.slice(1));
      return l.join("; ");
    }
    function fichaHtml(c, i) {
      var linhas = [];
      var tc = turmasDaCidade(c);
      if (tc.length) {
        return '<li class="ficha" data-i="' + i + '"><h2>' + esc(c.titulo) + '</h2>' +
          (c.entidade ? '<p class="entidade">' + esc(c.entidade) + "</p>" : "") +
          descricaoHtml(c) +
          '<ul class="turmas-ficha">' + tc.map(function (t) { return turmaHtml(t, false).replace("<li>", "<li>Turma: "); }).join("") + "</ul>" +
          '<p class="ficha-rodape">Inscrição: ' + tc.map(function (t) { var n = notaSimples(t.destino, true); return esc(t.link) + (n ? " (" + esc(n) + ")" : ""); }).join("<br>") + "<br>" +
          "Confirme na unidade antes de ir. Lista de " + esc(atualizado) + ".</p>" +
          '<button type="button" class="botao secundario so-ecra" data-ficha="' + i + '">Imprimir só esta ficha</button></li>';
      }
      unidadesDaCidade(c).forEach(function (u) {
        var m = [u.morada, u.bairro, u.municipio].filter(Boolean).join(", ");
        linhas.push("<li><strong>Onde:</strong> " + esc(u.nome) + (m ? ", " + esc(m) : "") + (u.horario ? ". " + esc(u.horario) : "") +
          (u.telefone ? ". Telefone " + esc(u.telefone) : "") + "</li>");
      });
      if (c.modalidade === "online") linhas.push("<li><strong>Onde:</strong> pela internet</li>");
      var quando = [c.inicio ? "começa em " + dataCurta(c.inicio) : "", turnoSeguro(c)].filter(Boolean).join(", ");
      if (quando) linhas.push("<li><strong>Quando:</strong> " + esc(quando) + "</li>");
      else if (varia(c)) linhas.push("<li><strong>Quando:</strong> o horário muda de unidade para unidade: confirme na unidade</li>");
      if (c.inscricoes_ate) linhas.push("<li><strong>Inscrições até:</strong> " + esc(dataCurta(c.inscricoes_ate)) + "</li>");
      var qp = quemPode(c); if (qp) linhas.push("<li><strong>Quem pode:</strong> " + esc(qp) + "</li>");
      if (c.exclusivo_para) linhas.push("<li><strong>Atenção:</strong> " + esc(c.exclusivo_para) + "</li>");
      if (c.gratuidade_comprovada === false) linhas.push("<li><strong>Atenção:</strong> " + GRATUIDADE_AVISO + "</li>");
      (c.etiquetas || []).forEach(function (e) { linhas.push("<li><strong>Vagas:</strong> " + esc(e.texto) + "</li>"); });
      if ((c.acessibilidade || []).length) linhas.push("<li><strong>Acessibilidade:</strong> " + esc(c.acessibilidade.map(function (e) { return e.texto; }).join(", ")) + "</li>");
      var levar = [c.documentos].concat(unidadesDaCidade(c).map(function (u) { return u.o_que_levar; })).filter(Boolean);
      if (levar.length) linhas.push("<li><strong>Levar:</strong> " + esc(levar[0].replace(/\.$/, "")) + "</li>");
      var g = (c.antes || []).map(function (id) { return guias[id]; }).filter(Boolean);
      if (g.length) linhas.push("<li><strong>Antes:</strong> " + g.map(function (x) { return esc(x.titulo); }).join(", ") + " (veja " + esc(base) + "antes.html)</li>");
      return '<li class="ficha" data-i="' + i + '"><h2>' + esc(c.titulo) + '</h2>' +
        (c.entidade ? '<p class="entidade">' + esc(c.entidade) + "</p>" : "") +
        descricaoHtml(c) + "<ul>" + linhas.join("") + "</ul>" +
        '<p class="ficha-rodape">Mais informações: ' + esc(c.url) + (notaSimples(c.destino, false) ? " (" + esc(notaSimples(c.destino, false)) + ")" : "") + "<br>" +
        (c.modalidade === "online" ? "Confirme na página do curso antes de começar." : "Confirme na unidade antes de ir.") +
        " Lista de " + esc(atualizado) + ".</p>" +
        '<button type="button" class="botao secundario so-ecra" data-ficha="' + i + '">Imprimir só esta ficha</button></li>';
    }
    function mostrar() {
      var sel = selecionados();
      acoes.hidden = !sel.length;
      if (!cidade.value) { lista.innerHTML = ""; return; }
      lista.innerHTML = sel.length ?
        '<p class="kit-titulo">Cursos gratuitos com inscrições abertas: ' + esc(cidade.value) + (comOnline.checked ? " e on-line" : "") +
        ". Lista de " + esc(atualizado) + ".</p><ul class=\"fichas\">" + sel.map(function (c) { return fichaHtml(c, todos.indexOf(c)); }).join("") + "</ul>" :
        '<p class="vazio">Neste momento não há cursos confirmados para ' + esc(cidade.value) + '. Marque "Incluir cursos on-line" ou volte daqui a alguns dias.</p>';
      var q = new URLSearchParams(); q.set("cidade", cidade.value); if (!comOnline.checked) q.set("online", "nao");
      history.replaceState(null, "", location.pathname + "?" + q.toString());
    }
    function textoWhatsapp() {
      var sel = selecionados();
      var l = ["📚 *Cursos gratuitos em " + cidade.value + "* (lista de " + atualizado + ")", ""];
      sel.forEach(function (c) {
        l.push("✅ *" + c.titulo + "*");
        var tc = turmasDaCidade(c);
        if (tc.length) {
          tc.forEach(function (t) {
            l.push([t.unidade, t.inicio ? "de " + dataCurta(t.inicio) + (t.fim ? " a " + dataCurta(t.fim) : "") : "", t.horario]
              .filter(Boolean).join(" · "));
            if (t.prazo) l.push("Inscrições até " + dataCurta(t.prazo));
            l.push(t.link);
            if (notaSimples(t.destino, true)) l.push(notaSimples(t.destino, true));
          });
          l.push("");
          return;
        }
        var u = unidadesDaCidade(c)[0];
        var det = [c.modalidade === "online" ? "On-line" : (u ? u.nome + (u.morada ? ", " + u.morada : "") : c.cidade),
                   c.inicio ? "começa em " + dataCurta(c.inicio) : "",
                   turnoSeguro(c)].filter(Boolean).join(" · ");
        l.push(det);
        if (c.documentos) l.push("Levar: " + c.documentos.replace(/\.$/, ""));
        l.push(c.url);
        if (notaSimples(c.destino, false)) l.push(notaSimples(c.destino, false));
        l.push("");
      });
      l.push("Veja todos e se pode se inscrever: " + base + "cursos.html?cidade=" + encodeURIComponent(cidade.value));
      l.push("Confirme na unidade ou na página do curso antes de ir.");
      return l.join("\n");
    }
    function copiar(t, msg) {
      (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () { copiado.textContent = msg; })
        .catch(function () { window.prompt("Copie o texto:", t); });
    }
    el("kit-imprimir").addEventListener("click", function () { window.print(); });
    el("kit-whatsapp").addEventListener("click", function () { copiar(textoWhatsapp(), "Texto copiado. Cole no WhatsApp."); });
    el("kit-link").addEventListener("click", function () { copiar(location.href, "Link copiado."); });
    lista.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-ficha]"); if (!b) return;
      var f = b.closest(".ficha"); f.classList.add("imprimir-esta"); document.body.classList.add("so-uma-ficha");
      window.print();
      setTimeout(function () { f.classList.remove("imprimir-esta"); document.body.classList.remove("so-uma-ficha"); }, 500);
    });
    cidade.addEventListener("change", mostrar);
    comOnline.addEventListener("change", mostrar);
    comOnline.checked = params.get("online") !== "nao";

    Promise.all([carregar("dados/cursos.json"), carregar("dados/guias.json").catch(function () { return { guias: [] }; })]).then(function (r) {
      todos = r[0].cursos || []; atualizado = r[0].atualizado ? dataCurta(r[0].atualizado.slice(0, 10)) + "/" + r[0].atualizado.slice(0, 4) : "";
      (r[1].guias || []).forEach(function (g) { guias[g.id] = g; });
      var cids = {};
      todos.forEach(function (c) { if (c.modalidade !== "online" && c.situacao === "Aberto" && !c.em_revisao) cidadesDe(c).forEach(function (x) { cids[x] = 1; }); });
      ordenarCidades(Object.keys(cids)).forEach(function (x) {
        var op = document.createElement("option"); op.value = x; op.textContent = x; cidade.appendChild(op);
      });
      if (params.get("cidade")) cidade.value = params.get("cidade");
      mostrar();
    }).catch(function () { lista.innerHTML = '<p class="vazio">Não foi possível carregar os cursos. Atualize a página daqui a pouco.</p>'; });
  }

  carregar("dados/site.json").then(function (site) {
    if (pagina === "antes") { antes(); return; }
    if (pagina === "encaminhar") { encaminhar(site); return; }
    if (pagina === "inicio") inicio(site);
    else if (pagina === "cursos") cursos(site);
    else if (pagina === "noticias") noticias(site);
  });
})();
