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
  // Medição (Google Analytics): só envia se a pessoa aceitou os cookies (ver o bloco do aviso, mais abaixo).
  function medir(nome, dados) {
    if (!window.__gaLigado || typeof window.gtag !== "function") return;
    dados = dados || {}; dados.pagina = pagina;
    window.gtag("event", nome, dados);
  }
  // texto digitado na busca: curto e sem nada que pareça e-mail, telefone ou documento (ninguém deve ser identificável)
  function termoSeguro(s) {
    s = (s || "").toLowerCase().replace(/\s+/g, " ").trim().slice(0, 40);
    return /@|\d{4,}/.test(s) ? "" : s;
  }
  var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
               "setembro", "outubro", "novembro", "dezembro"];

  function esc(t) {
    return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  // Telefones clicáveis no celular (revisão de 23/11/2026): cada número com DDD vira um link «tel:»; o WhatsApp abre a
  // conversa (wa.me). Recebe texto sem escapar e devolve HTML seguro.
  function telefones(t, whatsapp) {
    return esc(t).replace(/(?:\(?\d{2}\)?[\s.]?)\d{4,5}[\s.-]?\d{4}\b/g, function (m) {
      var d = m.replace(/\D/g, "");
      if (d.length < 10 || d.length > 11) return m;
      return '<a class="tel" href="' + (whatsapp ? "https://wa.me/55" + d : "tel:+55" + d) + '"' + (whatsapp ? ' rel="noopener"' : "") + ">" + m + "</a>";
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
  // Período escolhido no calendário da página de cursos ({ini, fim} em AAAA-MM-DD); null = «inscrições abertas hoje».
  var periodo = null;
  // A janela de inscrição [ini, fim] cruza o período escolhido (ou, sem período, inclui hoje)?
  function abertaNoPeriodo(ini, fim) {
    var h = hojeIso();
    ini = ini || h; fim = fim || "9999-12-31";
    if (!periodo) return ini <= h && fim >= h;
    return ini <= periodo.fim && fim >= periodo.ini;
  }
  function turmasAtuais(c) {
    var h = hojeIso();
    return (c.turmas || []).filter(function (t) {
      if (t.prazo ? t.prazo < h : (t.inicio && t.inicio <= h)) return false;
      if (t.por_abrir && !t.abertura) return false;  // inscrição futura sem data de abertura: não se mostra
      return abertaNoPeriodo(t.por_abrir ? t.abertura : "", t.prazo || t.inicio || "");
    });
  }
  // cursos que só têm inscrições futuras ficam fora das listas que não têm calendário (início, encaminhar)
  // curso sem turmas: inscrição aberta no período (sem período: hoje), ou que abre nos próximos DIAS_POR_ABRIR dias
  var DIAS_POR_ABRIR = 60;
  function porAbrir(c) { return !!(c.abertura && c.abertura > hojeIso()); }
  function janelaCurso(c) {
    if (porAbrir(c)) return periodo ? abertaNoPeriodo(c.abertura, c.inscricoes_ate || "") : diasAte(c.abertura) <= DIAS_POR_ABRIR;
    return abertaNoPeriodo("", c.inscricoes_ate || "");
  }
  function semFuturos(lista) { return (lista || []).filter(function (c) { return !c.so_futuro; }); }
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
  // «Novo no site»: o curso entrou hoje ou nos 2 dias anteriores (pedido do responsável, 25/11/2026)
  var DIAS_NOVO = 2;
  function recente(c) { var n = diasAte(c.primeiro_visto); return n !== null && n <= 0 && n >= -DIAS_NOVO; }
  function terminaEmBreve(c) { var n = diasAte(prazoProximo(c)); return n !== null && n >= 0 && n <= DIAS_ALERTA; }
  function quandoTermina(iso) {
    var n = diasAte(iso);
    return n === 0 ? "Último dia: inscrições até hoje" : n === 1 ? "Últimos dias: inscrições até amanhã"
         : "Últimos dias: inscrições até " + dataCurtaG(iso);
  }
  // «Lembrar-me»: evento de calendário (.ics) no dia do fim das inscrições, com aviso na véspera ao meio-dia.
  // Fica no telemóvel da pessoa: o site não guarda nenhum dado.
  function icsTexto(t) { return String(t || "").replace(/\\/g, "\\\\").replace(/([,;])/g, "\\$1").replace(/\r?\n/g, "\\n"); }
  // curso «por abrir»: o lembrete é para o dia em que a inscrição abre
  function lembrarAberturaHtml(titulo, abre, link, sitio) {
    var d = abre.slice(0, 10).replace(/-/g, ""), p = abre.slice(0, 10).split("-");
    var fim = new Date(+p[0], +p[1] - 1, +p[2] + 1);
    var dfim = fim.getFullYear() + ("0" + (fim.getMonth() + 1)).slice(-2) + ("0" + fim.getDate()).slice(-2);
    var agora = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
    var ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Cursos gratuitos//PT-BR", "CALSCALE:GREGORIAN", "BEGIN:VEVENT",
      "UID:abre-" + d + "-" + Math.abs(String(titulo + link).split("").reduce(function (a, ch) { return (a * 31 + ch.charCodeAt(0)) | 0; }, 7)) + "@cursos-gratuitos",
      "DTSTAMP:" + agora, "DTSTART;VALUE=DATE:" + d, "DTEND;VALUE=DATE:" + dfim,
      "SUMMARY:" + icsTexto("Abre a inscrição: " + titulo),
      "DESCRIPTION:" + icsTexto((sitio ? sitio + ". " : "") + "A inscrição abre hoje. Confirme na página oficial: " + link),
      "URL:" + link, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    var nome = "abre-" + titulo.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").slice(0, 40) + ".ics";
    return '<a class="lembrar" href="data:text/calendar;charset=utf-8,' + encodeURIComponent(ics) + '" download="' + esc(nome) + '">' +
      "Adicionar à agenda o dia em que a inscrição abre</a>";
  }
  function lembrarHtml(titulo, prazo, link, sitio, abre) {
    if (!prazo || !(diasAte(prazo) >= 1)) return "";
    if (abre) return lembrarAberturaHtml(titulo, abre, link, sitio);
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
    // turno pelo horário da turma («08:00 - 12:00»). Turma de dia inteiro (ex.: 08:00 - 17:00) não conta como
    // «de manhã» nem «à tarde», porque ocupa os dois (25/11/2026).
    return turmasAtuais(c).map(turnoDaTurma).filter(Boolean);
  }
  function turnoDaTurma(t) {
    var m = /(\d{1,2})[:h](\d{2})?\s*(?:-|–|às|a)?\s*(?:(\d{1,2})[:h]\d{0,2})?/.exec(t.horario || "");
    if (!m) return "";
    var ini = +m[1], fim = m[3] !== undefined ? +m[3] : null;
    if (ini >= 17) return "Noite";
    if (fim !== null && ini < 12 && fim > 13) return "";
    return ini < 12 ? "Manhã" : "Tarde";
  }
  function semAncora(u) { return String(u || "").split("#")[0]; }
  function turmaHtml(t, comBotao, tituloCurso, curso) {
    var l = ["<strong>" + esc(t.unidade || (t.local && t.local.nome) || "") + "</strong>" + (t.cidade ? " (" + esc(t.cidade) + ")" : "")];
    // «Dias» às vezes repete o período («23/11/2026 a 18/12/2026»), que já aparece no início da linha
    var diasT = /^\s*\d{1,2}\/\d{1,2}(\/\d{2,4})?\s*(a|até|-)\s*\d{1,2}\/\d{1,2}(\/\d{2,4})?\s*$/i.test(t.dias || "") && t.inicio ? "" : t.dias;
    var quando = [t.inicio ? dataCurtaG(t.inicio) + (t.fim ? " a " + dataCurtaG(t.fim) : "") : "", t.horario, diasT]
      .filter(Boolean).join(" · ");
    if (quando) l.push(esc(quando));
    var urgente = t.prazo && diasAte(t.prazo) >= 0 && diasAte(t.prazo) <= DIAS_ALERTA;
    if (t.por_abrir && t.abertura) l.push('<span class="prazo">Inscrições de ' + esc(dataBonita(t.abertura)) + (t.prazo ? " a " + esc(dataBonita(t.prazo)) : "") + "</span>");
    else l.push(t.prazo ? '<span class="prazo' + (urgente ? ' urgente' : '') + '">' + (urgente ? esc(quandoTermina(t.prazo)) : "Inscrições até " + esc(dataBonita(t.prazo))) + "</span>"
           : t.inscricao === "pagina" ? '<span class="prazo">Prazo de inscrição não indicado: confirme na página da turma</span>'
           : '<span class="prazo">Inscrições abertas. O prazo não está indicado: inscreva-se antes do início da turma</span>');
    // Detalhes da turma: no celular cada curso ocupava ~1,5 ecrã. Na lista, ficam numa caixa «Ver detalhes da turma»
    // que abre ao tocar (decisão do responsável, 23/11/2026); nas fichas para imprimir (sem botão) ficam à vista.
    var det = [], tipos = [];
    if (t.info) det.push(esc(t.info));
    if (t.inscricao === "online") l.push(t.info ? "Inscrição pela internet." : "Aulas on-line ao vivo. Inscrição pela internet.");
    if (t.inscricao === "presencial") l.push("Inscrição presencial" + (t.local_texto ? " em: " + esc(t.local_texto) : " na unidade"));
    if (t.inscricao !== "pagina" && t.telefone) { det.push("Dúvidas: " + telefones(t.telefone)); tipos.push("telefone"); }
    var reqs = requisitosDe(curso, t);
    if (reqs.length) l.push(requisitosHtml(reqs));
    if (t.documentos) { det.push("Documentos: " + esc(t.documentos.replace(/\.$/, ""))); tipos.splice(tipos.indexOf("telefone") >= 0 ? tipos.length - 1 : tipos.length, 0, "documentos"); }
    // turma com local de inscrição próprio (Centec presencial): não mostrar também a morada da unidade
    var u = (t.inscricao === "presencial" && t.local_texto) ? null : t.local;
    if (u) {
      var morada = [u.morada, u.bairro, u.municipio].filter(Boolean).join(", ");
      if (morada) { det.push(esc(morada)); tipos.push("endereço"); }
      if (u.telefone) { det.push("Telefone " + telefones(u.telefone)); if (tipos.indexOf("telefone") < 0) tipos.push("telefone"); }
    }
    if (det.length && comBotao) {
      var ordem = ["documentos", "endereço", "telefone"].filter(function (x) { return tipos.indexOf(x) >= 0; });
      var rotulo = ordem.length ? ordem.length === 1 ? ordem[0] : ordem.slice(0, -1).join(", ") + " e " + ordem[ordem.length - 1] : "";
      l.push('<details class="turma-detalhes"><summary>Mais detalhes da turma' + (rotulo ? " <span>(" + esc(rotulo) + ")</span>" : "") +
             "</summary>" + det.join("<br>") + "</details>");
    } else {
      l = l.concat(det);
    }
    if (comBotao) {
      var b = destinoBotao(t.destino, true, t.inscricao);
      if (b.nota) l.push('<span class="guia-link">' + b.nota + "</span>");
      l.push('<a class="botao" href="' + esc(t.link) + '" rel="noopener">' + esc(b.rotulo) + "</a>");
    }
    if (comBotao && tituloCurso) l.push(lembrarHtml(tituloCurso, t.prazo, t.link, [t.unidade, t.cidade].filter(Boolean).join(", ")));
    return "<li>" + l.join("<br>").replace(/<br>(<details|<div class="requisitos")/g, "$1").replace(/(<\/details>|<\/ul><\/div>)<br>/g, "$1") + "</li>";
  }

  // Requisitos num lugar só (pedido do responsável, 25/11/2026): substitui o questionário «Posso me inscrever?» e a
  // linha «Requisitos:» soltas. Nas turmas, os requisitos da turma (idade, escolaridade) vêm primeiro e os do curso
  // (renda, público, outros) juntam-se a eles.
  var ESCOLARIDADE_TXT = {
    "Saber ler e escrever": "Saber ler e escrever", "Fundamental incompleto": "Ter estudado parte do ensino fundamental",
    "Fundamental completo": "Ter o ensino fundamental completo", "Médio incompleto": "Ter começado o ensino médio",
    "Médio completo": "Ter o ensino médio completo", "Superior": "Ter curso superior"
  };
  // Requisitos: o texto da fonte, sem reescrever (decisão do responsável, 25/11/2026: reescrever pode mudar o sentido;
  // a ferramenta pode errar). Só se tiram espaços a mais e a pontuação do fim, e a primeira letra fica maiúscula.
  function simples(x) {
    x = String(x || "").replace(/\s+/g, " ").trim().replace(/[.;,]\s*$/, "");
    return x.charAt(0).toUpperCase() + x.slice(1);
  }
  // um requisito por linha: separa por «;», por fim de frase e antes dos rótulos da fonte («Requisito de Idade:»,
  // «Escolaridade mínima:», «Idade maior ou igual…»), sem apagar nenhuma palavra
  function partesDe(texto) {
    return String(texto || "")
      .replace(/\s+(?=Requisito\s+(?:de\s+idade|espec[íi]fico)\s*:)/gi, "; ")
      .replace(/(Requisito\s+de)\s+(Idade)/gi, "$1\u0001$2")  // «Requisito de Idade:» fica junto
      .replace(/([^;\s])\s+(?=(?:Escolaridade|Idade)(?:\s+m[íi]nima)?\s*:)/g, "$1; ")
      .replace(/([^;\s])\s+(?=Idade\s+(?:m[íi]nima|maior|igual|a partir))/g, "$1; ")
      .split(/;\s*|\.\s+(?=[A-ZÀ-Ú])/).map(function (p) { return p.replace(/\u0001/g, " "); })
      .map(function (p) { return p.trim(); }).filter(Boolean);
  }

  function requisitosDe(c, t) {
    // 1.º o texto da fonte (escolaridade da turma, requisitos do curso, renda, público), uma parte por linha;
    // 2.º só o que a fonte não diz por escrito, a partir dos números lidos (idade) e dos campos do curso.
    var fonte = [];
    if (t && t.escolaridade && !/\([^)]*$/.test(t.escolaridade)) {  // cortada na fonte: vale a do texto do curso
      partesDe(t.escolaridade).map(simples).forEach(function (x, i) { fonte.push(i === 0 && !/^escolaridade/i.test(x) ? "Escolaridade: " + x : x); });
    }
    if (c) {
      partesDe(c.requisitos).map(simples).forEach(function (x) { fonte.push(x); });
      if (c.renda && !fonte.some(function (x) { return /renda|sal[áa]rio/i.test(x); })) fonte.push(simples(c.renda));
      if (c.exclusivo_para) fonte.push(simples(c.exclusivo_para));
    }
    var numIdade = function (x) { var m = /(\d+)\s*anos\b/i.exec(x); return m && !/renda|escolaridade/i.test(x) ? +m[1] : null; };
    var idadesFonte = fonte.map(numIdade).filter(function (n) { return n !== null; });
    var temEscola = fonte.some(function (x) { return /escolaridade|ensino (fundamental|m[ée]dio)|alfabetiz|superior/i.test(x); });
    var gerados = [];
    var idade = function (min, max) {
      return min && max ? "Ter de " + min + " a " + max + " anos" : min ? "Ter " + min + " anos ou mais" : max ? "Ter até " + max + " anos" : "";
    };
    var min = (t && t.idade_minima) || (c && c.idade_minima), max = (t && t.idade_maxima) || (c && c.idade_maxima);
    if ((min || max) && !(min && idadesFonte.indexOf(+min) >= 0) && !(!min && max && idadesFonte.indexOf(+max) >= 0)) gerados.push(idade(min, max));
    if (c && !temEscola && c.escolaridade && ESCOLARIDADE_TXT[c.escolaridade]) gerados.push(ESCOLARIDADE_TXT[c.escolaridade]);
    if (c && /aperfei[cç]oamento/i.test(c.documentos || "") && !fonte.some(function (x) { return /experi[êe]ncia/i.test(x); }))
      gerados.push("Ter experiência na área (é um curso de aperfeiçoamento)");
    // sem repetir: compara sem o rótulo («Escolaridade mínima:», «Requisito de Idade:»…) e sem maiúsculas
    var chave = function (x) {
      return x.toLowerCase().replace(/^(requisito\s+(de\s+idade|espec[íi]fico)|escolaridade(\s+m[íi]nima|\s+a\s+partir\s+de)?|idade(\s+m[íi]nima)?)\s*:\s*/, "")
              .replace(/[^a-z0-9à-ú]+/g, " ").trim();
    };
    var vistos = {};
    return gerados.concat(fonte).filter(function (x) { var k = chave(x); if (!k || vistos[k]) return false; vistos[k] = 1; return true; });
  }
  function requisitosHtml(itens) {
    if (!itens.length) return "";
    return '<div class="requisitos"><p class="requisitos-titulo">Requisitos</p><ul>' +
      itens.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul></div>";
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
        // turma presencial sem página própria (ex.: Centec): a inscrição é na unidade e o botão serve só para conferir
        // (pedido do responsável, 23/11/2026)
        if (emTurma && inscricao === "presencial")
          return { rotulo: "Conferir na página " + (d.nome ? "do " + d.nome : "oficial"),
                   nota: "Esta turma não tem página própria: o botão abre a lista geral" + (d.nome ? " do " + esc(d.nome) : "") + ", só para conferir. " +
                         (d.procurar ? "Lá, procure “" + esc(d.procurar) + "”." : "Lá, procure o nome do curso.") + extra };
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
  // curta = cartão da lista de cursos: a descrição mostra 2 linhas e um botão «ler mais» (revisão do celular, 23/11/2026)
  function descricaoHtml(c, curta) {
    if (!c.descricao) return "";
    return '<p class="descricao' + (curta ? ' curta' : '') + '">' + (c.descricao_origem === "pagina" ? "" : '<span class="rotulo">Em resumo:</span> ') +
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

  // «O que facilita para você?»: o curso passa nesta opção? (usada no filtro e para contar)
  function passaBarreira(c, id) {
    if (id === "noite") return turnosDe(c).indexOf("Noite") >= 0;
    if (id === "manha") return turnosDe(c).indexOf("Manhã") >= 0;
    if (id === "tarde") return turnosDe(c).indexOf("Tarde") >= 0;
    // aceita menores de 18 anos: idade mínima abaixo de 18 escrita na fonte (no curso ou numa turma aberta)
    if (id === "jovens") {
      var idades = [c.idade_minima].concat(((c.turmas || []).length ? turmasAtuais(c) : []).map(function (t) { return t.idade_minima; }))
        .map(function (x) { return parseInt(x, 10); }).filter(function (x) { return !isNaN(x); });
      return idades.some(function (x) { return x < 18; });
    }
    if (id === "sem_internet") return c.internet === "Não";
    if (id === "sem_escolaridade") return ["Nenhuma", "Saber ler e escrever"].indexOf(c.escolaridade) >= 0;
    if (id === "ajuda") return !!c.ajuda && !/^n[aã]o/i.test(c.ajuda);
    if (id === "reservadas") return !!(c.etiquetas || []).length;
    if (id === "acessivel") return !!(c.acessibilidade || []).length;
    if (id === "fecha_breve") return terminaEmBreve(c);
    if (id === "recente") return recente(c);
    return true;
  }
  // botões que não encontram nenhum curso ficam escondidos e voltam sozinhos quando houver cursos (25/11/2026).
  // Tira também a opção da escolha (vinda de um link antigo), para a lista não ficar vazia sem botão para desmarcar.
  function esconderSemCursos(ul, atributo, escolhidas, temCurso) {
    if (!ul) return;
    ul.querySelectorAll("button[" + atributo + "]").forEach(function (b) {
      var id = b.getAttribute(atributo), vazio = !temCurso(id);
      b.parentNode.hidden = vazio;
      var i = escolhidas.indexOf(id);
      if (vazio && i >= 0) { escolhidas.splice(i, 1); b.setAttribute("aria-pressed", "false"); }
    });
  }
  function necessidadeTemCurso(cursos) {
    return function (id) { return cursos.some(function (c) { return (c.necessidades || []).indexOf(id) >= 0; }); };
  }

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

  // horas do curso a partir do texto da duração («10 horas», «20h/aula», «Em média 6 horas»); null se não houver
  function horasDe(c) {
    var m = /(\d+(?:[.,]\d+)?)\s*(h\b|h\/|horas?)/i.exec(c.duracao || "");
    return m ? parseFloat(m[1].replace(",", ".")) : null;
  }
  // faixas de duração (em horas). «longo» (mais de 20 h) fica só para links antigos; as faixas longas foram
  // divididas a pedido do responsável (27/11/2026), porque há cursos de 160, 240 horas e técnicos de 800 horas ou mais.
  var FAIXAS_DURACAO = [["curto", "Até 4 horas", 0, 4], ["medio", "De 5 a 20 horas", 4, 20], ["h40", "De 21 a 40 horas", 20, 40],
    ["h80", "De 41 a 80 horas", 40, 80], ["h160", "De 81 a 160 horas", 80, 160], ["h400", "De 161 a 400 horas", 160, 400],
    ["h400mais", "Mais de 400 horas (cursos técnicos)", 400, Infinity], ["longo", "Mais de 20 horas", 20, Infinity]];
  function naDuracao(c, faixa) {
    var h = horasDe(c);
    if (h === null) return false;
    var f = FAIXAS_DURACAO.filter(function (x) { return x[0] === faixa; })[0];
    return f ? h > f[2] && h <= f[3] : true;
  }
  function marcasDe(c) {
    return (c.certificado === "gratuito" ? ["cert-gratuito"] : [])
      .concat(c.gratuidade_comprovada === false ? ["grat-confirmar"] : [])
      .concat((c.etiquetas || []).map(function (e) { return "pub:" + e.texto; }))
      .concat((c.acessibilidade || []).map(function (e) { return "acc:" + e.texto; }));
  }
  function cidadesDe(c) {
    if ((c.turmas || []).length) return turmasAtuais(c).map(function (t) { return t.cidade; }).filter(Boolean);
    var l = [c.cidade].concat((c.onde_inscrever || []).map(function (u) { return u.municipio; }));
    return l.filter(Boolean);
  }

  // Uma busca (o que a pessoa escolheu nos filtros) como objeto, a partir do endereço ?quero=…&onde=…
  function buscaDe(p) {
    var lista = function (k) { return (p.get(k) || "").split(",").filter(Boolean); };
    var marca = p.get("marca") || "";
    return { quero: lista("quero"), onde: p.get("onde") || "", facilita: lista("facilita"),
             marca: marca === "cert-gratuito" ? "" : marca, cidade: p.get("cidade") || "",
             certificado: p.get("certificado") === "gratuito" || marca === "cert-gratuito",
             duracao: p.get("duracao") || "", texto: p.get("texto") || "" };
  }
  // O curso entra nesta busca? (a mesma regra da lista de cursos e das buscas salvas)
  function passaBusca(c, f) {
    if (f.quero.length && !(c.necessidades || []).some(function (n) { return f.quero.indexOf(n) >= 0; })) return false;
    if (f.onde === "online" && c.modalidade !== "online") return false;
    // estado escolhido: só os cursos presenciais desse estado; os on-line têm a opção própria «On-line»
    if (f.onde && f.onde !== "online" && (c.modalidade === "online" || c.local !== f.onde)) return false;
    if (!f.facilita.every(function (id) { return passaBarreira(c, id); })) return false;
    if (f.marca && marcasDe(c).indexOf(f.marca) < 0) return false;
    // calendário: o curso tem de ter inscrições abertas em algum dia do período (sem período: hoje)
    if ((c.turmas || []).length) { if (!turmasAtuais(c).length) return false; }
    else if (!janelaCurso(c)) return false;
    if (f.certificado && c.certificado !== "gratuito") return false;
    if (f.duracao && !naDuracao(c, f.duracao)) return false;
    if (f.cidade && cidadesDe(c).indexOf(f.cidade) < 0) return false;
    var t = semAcentos(f.texto.trim());
    if (t && !bateBusca(semAcentos([c.titulo, c.descricao, c.entidade, c.cidade, c.regiao].join(" ")), t)) return false;
    return true;
  }

  // ------------------------------------------------------------ Buscas salvas (só neste aparelho)
  // Pedido do responsável (25/11/2026): «salvar a busca» em vez de avisos por e-mail. Nada sai do aparelho: a lista
  // fica no armazenamento do navegador (localStorage). Cada busca guarda o endereço, um nome e o dia da última
  // visita; «novos» são os cursos da busca que entraram no site depois desse dia.
  var CHAVE_BUSCAS = "buscas-salvas", MAX_BUSCAS = 10;
  function lerBuscas() {
    try { var v = JSON.parse(localStorage.getItem(CHAVE_BUSCAS) || "[]"); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  function gravarBuscas(l) { try { localStorage.setItem(CHAVE_BUSCAS, JSON.stringify(l.slice(0, MAX_BUSCAS))); return true; } catch (e) { return false; } }
  function chaveBusca(q) {  // a mesma busca, qualquer que seja a página ou a ordem dos parâmetros
    var p = new URLSearchParams(q); p.delete("pagina");
    var k = []; p.forEach(function (v, n) { if (v) k.push(n + "=" + v); });
    return k.sort().join("&");
  }
  function novosNaBusca(cursos, b) {
    var f = buscaDe(new URLSearchParams(b.q));
    return cursos.filter(function (c) { return (c.primeiro_visto || "").slice(0, 10) > (b.visto || "") && passaBusca(c, f); }).length;
  }
  function buscasSalvasHtml(cursos, atual) {
    var l = lerBuscas();
    if (!l.length) return "";
    return '<h2 id="titulo-buscas-salvas">Suas buscas salvas</h2><ul class="buscas-salvas">' + l.map(function (b, i) {
      var n = cursos ? novosNaBusca(cursos, b) : 0, aqui = atual && chaveBusca(b.q) === atual;
      return '<li><a href="cursos.html?' + esc(b.q) + '"' + (aqui ? ' aria-current="true"' : "") + ">" + esc(b.nome) + "</a>" +
        (n ? ' <span class="novos">' + (n === 1 ? "1 curso novo" : n + " cursos novos") + "</span>" : "") +
        ' <button type="button" class="ler-mais" data-remover-busca="' + i + '">remover</button></li>';
    }).join("") + '</ul><p class="discreto">Ficam só neste aparelho. Ninguém recebe seus dados.</p>';
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
    // o site é para o país todo: a página inicial abre com «Mostrar tudo», como a lista de cursos (25/11/2026)
    preencherOnde(onde, site.locais, "");
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
      todos = semFuturos(d.cursos);
      esconderSemCursos(el("inicio-opcoes"), "data-id", escolhidas, necessidadeTemCurso(todos));
      // buscas salvas neste aparelho, com os cursos novos de cada uma desde a última visita (25/11/2026)
      var caixaBuscas = el("inicio-buscas");
      var desenharBuscas = function () { var h = buscasSalvasHtml(todos, ""); caixaBuscas.innerHTML = h; caixaBuscas.hidden = !h; };
      if (caixaBuscas) {
        desenharBuscas();
        caixaBuscas.addEventListener("click", function (ev) {
          var r = ev.target.getAttribute("data-remover-busca");
          if (r !== null) { var l = lerBuscas(); l.splice(+r, 1); gravarBuscas(l); desenharBuscas(); }
        });
      }
      atualizar();
      desenharUltimos();
    }).catch(function () { caixa.parentNode.style.display = "none"; });
  }

  // «Avisar um erro neste curso»: abre o formulário de sugestões com o tipo e o nome do curso já preenchidos
  var FORM = {};
  function avisarErroHtml(c, naLinha) {
    if (!FORM.url) return "";
    var q = "?usp=pp_url&" + FORM.campo_tipo + "=" + encodeURIComponent(FORM.tipo_erro || "") + "&" + FORM.campo_curso + "=" +
      encodeURIComponent(c.titulo + (c.entidade ? " – " + c.entidade : "") + " (" + (c.url || "") + ")");
    var a = '<a href="' + esc(FORM.url + q) + '" target="_blank" rel="noopener">Avisar um erro' + (naLinha ? "" : " neste curso") + "</a>";
    return naLinha ? ' <span class="avisar">' + a + "</span>" : '<p class="avisar">' + a + "</p>";
  }

  // ------------------------------------------------------------ Números (23/11/2026)
  // Resumo dos cursos abertos hoje, com a mesma regra da página de cursos (turmas atuais; sem os só futuros).
  function numeros(site) {
    // mapa do Brasil em quadrados: [UF, linha, coluna, nome]
    var GRADE = [["RR", 0, 2, "Roraima"], ["AP", 0, 4, "Amapá"],
      ["AC", 1, 0, "Acre"], ["AM", 1, 1, "Amazonas"], ["PA", 1, 3, "Pará"], ["MA", 1, 4, "Maranhão"], ["CE", 1, 5, "Ceará"], ["RN", 1, 6, "Rio Grande do Norte"],
      ["RO", 2, 1, "Rondônia"], ["MT", 2, 2, "Mato Grosso"], ["TO", 2, 3, "Tocantins"], ["PI", 2, 4, "Piauí"], ["PE", 2, 5, "Pernambuco"], ["PB", 2, 6, "Paraíba"],
      ["MS", 3, 2, "Mato Grosso do Sul"], ["GO", 3, 3, "Goiás"], ["BA", 3, 4, "Bahia"], ["AL", 3, 5, "Alagoas"],
      ["DF", 4, 3, "Distrito Federal"], ["MG", 4, 4, "Minas Gerais"], ["SE", 4, 5, "Sergipe"],
      ["PR", 5, 2, "Paraná"], ["SP", 5, 3, "São Paulo"], ["RJ", 5, 4, "Rio de Janeiro"], ["ES", 5, 5, "Espírito Santo"],
      ["SC", 6, 2, "Santa Catarina"], ["RS", 7, 2, "Rio Grande do Sul"]];
    function horas(c) { var m = /(\d+(?:[.,]\d+)?)\s*(h\b|h\/|horas?)/i.exec(c.duracao || ""); return m ? parseFloat(m[1].replace(",", ".")) : null; }
    carregar("dados/cursos.json").then(function (d) {
      var todos = semFuturos(d.cursos).filter(function (c) {
        return (c.turmas || []).length ? turmasAtuais(c).length > 0 : janelaCurso(c);
      });
      var total = todos.length;
      var online = todos.filter(function (c) { return c.modalidade === "online"; }).length;
      var cert = todos.filter(function (c) { return c.certificado === "gratuito"; }).length;
      var pct = function (n) { return total ? Math.round(n * 100 / total) + "%" : "0%"; };
      var quando = d.atualizado ? dataBonita(d.atualizado.slice(0, 10)) + ", às " + d.atualizado.slice(11, 16) : "";
      el("numeros-data").textContent = "Lista atualizada em " + quando + ".";
      el("numeros-cartoes").innerHTML = [[total, "cursos com inscrições abertas"], [total - online, "presenciais (" + pct(total - online) + ")"],
        [online, "on-line (" + pct(online) + ")"], [cert, "com certificado gratuito (" + pct(cert) + ")"]].map(function (x) {
        return '<div class="numero-cartao"><b>' + x[0].toLocaleString("pt-BR") + "</b><span>" + esc(x[1]) + "</span></div>";
      }).join("");
      var limites = FAIXAS_DURACAO.filter(function (x) { return x[0] !== "longo"; });
      var faixas = limites.map(function (x) { return [x[1], 0]; }).concat([["Não informada", 0]]);
      todos.forEach(function (c) {
        var h = horas(c), i = limites.length;
        if (h !== null) limites.forEach(function (x, k) { if (h > x[2] && h <= x[3]) i = k; });
        faixas[i][1]++;
      });
      el("numeros-duracao").innerHTML = faixas.map(function (f) {
        var p = total ? Math.round(f[1] * 100 / total) : 0;
        // o fundo da barra é o total (100%); a parte azul é a parcela desta faixa (pedido do responsável, 25/11/2026)
        return '<div class="barra"><span>' + esc(f[0]) + '</span><span class="barra-fundo"><span class="barra-cheia" style="width:' + (total ? f[1] * 100 / total : 0).toFixed(1) + '%"></span></span>' +
          '<span class="barra-valor">' + p + "% (" + f[1] + ")</span></div>";
      }).join("");
      var porUf = {}, ativos = {};
      (site.locais || []).forEach(function (l) { if (/^BR-/.test(l.id)) ativos[l.id.slice(3)] = 1; });
      todos.forEach(function (c) { if (c.modalidade !== "online" && /^BR-/.test(c.local || "")) porUf[c.local.slice(3)] = (porUf[c.local.slice(3)] || 0) + 1; });
      var max = Math.max.apply(null, [1].concat(Object.keys(porUf).map(function (k) { return porUf[k]; })));
      var svg = el("mapa-brasil"), g = el("mapa-bolinhas");
      var nomeUf = {}; GRADE.forEach(function (x) { nomeUf[x[0]] = x[3]; });
      function textoDica(uf) {
        var n = porUf[uf] || 0;
        return (nomeUf[uf] || uf) + ": " + (!ativos[uf] ? "ainda não faz parte do site"
          : n === 1 ? "1 curso presencial" : n + " cursos presenciais");
      }
      if (svg && g) {
        var marcas = "";
        svg.querySelectorAll(".uf-forma").forEach(function (f) {
          var uf = f.getAttribute("data-uf");
          if (!ativos[uf]) return;
          f.classList.add("ativo");
          var b = f.getBBox(), n = porUf[uf] || 0;
          var r = n >= 100 ? 17 : n >= 10 ? 14 : 12;
          // posição da bolinha: centro da caixa do estado (ajustes para estados de forma irregular)
          var ajuste = { PE: [-25, 0], PI: [0, 8], MA: [0, 10], BA: [-6, 0], PB: [-4, -2], AL: [3, -3], SE: [2, 3], RN: [4, 0] }[uf] || [0, 0];
          var x = b.x + b.width / 2 + ajuste[0], y = b.y + b.height / 2 + ajuste[1];
          marcas += '<g class="bolinha' + (n ? "" : " zero") + '" data-uf="' + uf + '"><title>' + esc(textoDica(uf)) + '</title><circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="' + r + '"></circle>' +
            '<text x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" font-size="' + (r > 12 ? 12 : 11) + '">' + n + "</text></g>";
        });
        g.innerHTML = marcas;
        // ao passar o rato (ou tocar) num estado ou na bolinha, aparece o nome do estado e o número de cursos
        var caixaMapa = svg.parentNode, dica = document.createElement("div");
        dica.className = "mapa-dica"; dica.hidden = true; dica.setAttribute("role", "status");
        caixaMapa.appendChild(dica);
        svg.querySelectorAll(".uf-forma title").forEach(function (t) { t.parentNode.removeChild(t); });  // sem a dica nativa repetida
        var mostrarDica = function (ev) {
          var alvo = ev.target.closest("[data-uf]");
          svg.querySelectorAll(".uf-forma.realce").forEach(function (f) { f.classList.remove("realce"); });
          if (!alvo) { dica.hidden = true; return; }
          var uf = alvo.getAttribute("data-uf"), forma = svg.querySelector('.uf-forma[data-uf="' + uf + '"]');
          if (forma) forma.classList.add("realce");
          dica.textContent = textoDica(uf); dica.hidden = false;
          var r = caixaMapa.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
          dica.style.left = Math.max(0, Math.min(x + 12, r.width - dica.offsetWidth)) + "px";
          dica.style.top = Math.max(0, y - dica.offsetHeight - 10) + "px";
        };
        svg.addEventListener("mousemove", mostrarDica);
        svg.addEventListener("click", mostrarDica);
        svg.addEventListener("mouseleave", function () {
          dica.hidden = true;
          svg.querySelectorAll(".uf-forma.realce").forEach(function (f) { f.classList.remove("realce"); });
        });
      }
    }).catch(function () { el("numeros-cartoes").innerHTML = '<p class="vazio">Não foi possível carregar os números agora.</p>'; });
  }

  // ------------------------------------------------------------ Cursos
  function cursos(site) {
    var calendarioRedesenhar = function () {};
    var params = new URLSearchParams(location.search);
    var escolhidas = (params.get("quero") || "").split(",").filter(Boolean);
    var onde = el("cursos-onde");
    var texto = el("cursos-texto");
    if (params.get("texto")) texto.value = params.get("texto").slice(0, 60);
    var lista = el("cursos-lista");
    var contagem = el("cursos-contagem");
    var todos = [];
    // paginação: 10 cursos por página, para a lista não ficar pesada (pedido do responsável, 25/11/2026)
    var hashInicial = location.hash;  // o filtrar() reescreve o endereço sem o #curso-…: guardar o destino antes
    var POR_PAGINA = 10, pagina = Math.max(1, parseInt(params.get("pagina"), 10) || 1), manterPagina = true, ultimoRes = [];
    // a mesma navegação aparece no começo e no fim da lista (pedido do responsável, 25/11/2026)
    var navsPaginas = ["acima", "abaixo"].map(function (onde) {
      var nav = document.createElement("nav");
      nav.className = "paginacao paginacao-" + onde; nav.hidden = true;
      nav.setAttribute("aria-label", onde === "acima" ? "Páginas da lista de cursos (início)" : "Páginas da lista de cursos (fim)");
      lista.insertAdjacentElement(onde === "acima" ? "beforebegin" : "afterend", nav);
      return nav;
    });
    var caixaBuscas = document.createElement("div");
    caixaBuscas.className = "buscas-caixa"; caixaBuscas.id = "cursos-buscas";
    contagem.insertAdjacentElement("afterend", caixaBuscas);
    var buscaAoAbrir = chaveBusca(location.search), novosDesde = null;  // dia da visita anterior a esta busca salva
    function nomeDaBusca() {
      var partes = [];
      if (onde.value) partes.push(onde.options[onde.selectedIndex].text.replace(/^Brasil\s*[–-]\s*/, ""));
      escolhidas.forEach(function (id) { partes.push(rotulos[id] || id); });
      barreiras.forEach(function (id) { var bt = ulBarreiras.querySelector('[data-barreira="' + id + '"]'); partes.push(bt ? bt.textContent : id); });
      if (cidade.value) partes.push(cidade.value);
      if (duracao && duracao.value) partes.push(duracao.options[duracao.selectedIndex].text);
      if (certificado && certificado.checked) partes.push("Certificado gratuito");
      if (marcaEscolhida) partes.push(textoMarca(marcaEscolhida));
      if (texto.value.trim()) partes.push("“" + texto.value.trim().slice(0, 40) + "”");
      return partes.join(", ") || "Todos os cursos";
    }
    function desenharBuscasSalvas(q) {
      var atual = chaveBusca(q), l = lerBuscas();
      var salva = l.some(function (b) { return chaveBusca(b.q) === atual; });
      var botao = !atual ? "" : salva
        ? '<p class="busca-salva">Esta busca está salva neste aparelho.</p>'
        : '<button type="button" class="botao secundario pequeno" id="cursos-salvar-busca">Salvar esta busca</button>' +
          '<span class="discreto"> Quando voltar, você vê quantos cursos novos apareceram.</span>';
      caixaBuscas.innerHTML = botao + '<div class="buscas-lista">' + buscasSalvasHtml(todos, atual) + "</div>";
    }
    caixaBuscas.addEventListener("click", function (ev) {
      var q = location.search.replace(/^\?/, "");
      if (ev.target.id === "cursos-salvar-busca") {
        var l = lerBuscas().filter(function (b) { return chaveBusca(b.q) !== chaveBusca(q); });
        l.unshift({ q: q.replace(/(^|&)pagina=\d+/, ""), nome: nomeDaBusca(), visto: hojeIso() });
        if (!gravarBuscas(l)) { caixaBuscas.insertAdjacentHTML("beforeend", '<p class="discreto">Este navegador não deixa guardar buscas.</p>'); return; }
        medir("salvar_busca", { estado: onde.value || "todos", total_salvas: Math.min(l.length, MAX_BUSCAS) });
        desenharBuscasSalvas(q);
        return;
      }
      var r = ev.target.getAttribute("data-remover-busca");
      if (r !== null) { var l2 = lerBuscas(); l2.splice(+r, 1); gravarBuscas(l2); desenharBuscasSalvas(q); }
    });
    var guiasPorId = {};
    var barreiras = (params.get("facilita") || "").split(",").filter(Boolean);
    var marcaEscolhida = params.get("marca") || "";
    var certificado = el("cursos-certificado");
    var duracao = el("cursos-duracao");
    if (certificado) certificado.checked = params.get("certificado") === "gratuito" || marcaEscolhida === "cert-gratuito";
    if (duracao && params.get("duracao") === "longo" && !duracao.querySelector('option[value="longo"]')) {
      // link antigo com «Mais de 20 horas»: a opção volta a aparecer só para este link
      var opt = document.createElement("option"); opt.value = "longo"; opt.textContent = "Mais de 20 horas"; duracao.appendChild(opt);
    }
    if (duracao && FAIXAS_DURACAO.some(function (x) { return x[0] === params.get("duracao"); })) duracao.value = params.get("duracao");
    if (marcaEscolhida === "cert-gratuito") marcaEscolhida = "";  // links antigos: agora é o filtro «Certificado»
    var marcaSumiu = "";  // marca de um link antigo que já nenhum curso tem
    var cidade = el("cursos-cidade");
    var notaBarreiras = el("cursos-nota-barreiras");
    var rotulos = {};
    site.necessidades.forEach(function (n) { rotulos[n.id] = n.rotulo; });
    var nomesLocal = {};
    site.locais.forEach(function (l) { nomesLocal[l.id] = l.rotulo; });

    var TURNO = { "Manhã": "De manhã", "Tarde": "À tarde", "Noite": "À noite" };

    function antesHtml(c) {
      var g = (c.antes || []).map(function (id) { return guiasPorId[id]; }).filter(Boolean);
      if (!g.length) return "";
      return '<p class="antes">Antes, você vai precisar de: ' + g.map(function (x) {
        return '<a href="antes.html#' + esc(x.id) + '">' + esc(x.titulo.replace(/^Tirar o |^Fazer o |^Criar a /, "")) + "</a>";
      }).join(", ") + ".</p>";
    }

    function cursoHtml(c, i) {
      var turmas = turmasAtuais(c);
      // com um filtro de turno ligado, o cartão mostra só as turmas desse turno (25/11/2026)
      var turnosPedidos = barreiras.map(function (b) { return { manha: "Manhã", tarde: "Tarde", noite: "Noite" }[b]; }).filter(Boolean);
      if (turnosPedidos.length) {
        var doTurno = turmas.filter(function (t) { return turnosPedidos.indexOf(turnoDaTurma(t)) >= 0; });
        if (doTurno.length) turmas = doTurno;
      }
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
      // regra do projeto: gratuidade só com frase da página que diga que não há custo; sem ela, avisa-se
      if (c.gratuidade_comprovada === false) factos.push(marca("atencao", "Gratuidade por confirmar", "marca:grat-confirmar"));
      var breve = terminaEmBreve(c);
      if (novosDesde && (c.primeiro_visto || "").slice(0, 10) > novosDesde) factos.unshift('<span class="novo">Novo desde a sua última visita</span>');
      else if (recente(c)) factos.unshift(marca("novo", "Novo!", "facilita:recente"));
      if (breve) factos.unshift(marca("urgente", quandoTermina(prazoProximo(c)), "facilita:fecha_breve"));
      if (temTurmas) {
        factos.push('<span class="bom">' + (turmas.length === 1 ? "1 turma com inscrições abertas" : turmas.length + " turmas com inscrições abertas") + "</span>");
      } else {
        if (porAbrir(c)) factos.push('<span class="atencao">Inscrições abrem em ' + esc(dataBonita(c.abertura)) + (c.inscricoes_ate ? " e vão até " + esc(dataBonita(c.inscricoes_ate)) : "") + "</span>");
        else if (c.inscricoes_ate && !breve) factos.push('<span class="atencao">Inscrições até ' + esc(dataBonita(c.inscricoes_ate)) + "</span>");
        else if (c.data_por_confirmar) factos.push('<span class="atencao">Confirme a data na página oficial</span>');
        if (c.situacao === "Por confirmar") factos.push('<span class="atencao">Inscrições por confirmar</span>');
        if (c.inicio) factos.push("Aulas começam em " + esc(dataBonita(c.inicio)));
        if (c.matricula) factos.push("Se for aprovado: matrícula " + esc(c.matricula));
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
      (c.etiquetas || []).forEach(function (e) { condicoes.push("Sobre as vagas, a fonte diz: “" + esc(e.frase.replace(/[.\s]+$/, "")) + "”"); });
      var frasesAcess = (c.acessibilidade || []).map(function (e) { return e.frase; }).filter(function (f, i, a) { return a.indexOf(f) === i; });
      frasesAcess.forEach(function (f) { condicoes.push("Sobre acessibilidade, a fonte diz: “" + esc(f.replace(/[.\s]+$/, "")) + "”"); });
      if (c.gratuidade_comprovada === false) condicoes.push(GRATUIDADE_AVISO);
      // com turmas, os documentos são os de cada turma
      if (c.documentos && !temTurmas) condicoes.push("Documentos: " + esc(c.documentos.replace(/\.$/, "")));
      // O título nunca é uma ligação (igual em todos os cursos): para ir ao site oficial usam-se os botões,
      // que dizem para onde levam.
      return '<li class="curso" id="' + idCartao(c, i) + '"><h2>' + esc(c.titulo) + "</h2>" +
        (c.entidade ? '<p class="entidade">' + esc(c.entidade) + "</p>" : "") +
        descricaoHtml(c, true) +
        // como se distribuem as vagas (regra de 24/11/2026: sorteio e ordem de inscrição entram, com aviso claro)
        (c.vagas === "sorteio" ? '<p class="vagas-aviso">Vagas por sorteio: inscrever-se não garante a vaga.</p>'
         : c.vagas === "ordem" ? '<p class="vagas-aviso">Vagas por ordem de inscrição: inscreva-se cedo.</p>' : "") +
        '<ul class="factos">' + factosHtml + "</ul>" +
        (condicoes.length ? '<p class="condicao">' + condicoes.join(". ") + "</p>" : "") +
        (temTurmas ? "" : requisitosHtml(requisitosDe(c, null))) + antesHtml(c) +
        (temTurmas ? '<div class="onde turmas"><p class="onde-titulo">Turmas com inscrições abertas</p><ul>' +
          turmas.map(function (t) { return turmaHtml(t, true, c.titulo, c); }).join("") + "</ul>" +
"</div>" :
        c.onde_inscrever && c.onde_inscrever.length ? '<div class="onde"><p class="onde-titulo">Onde se inscrever</p><ul>' +
          c.onde_inscrever.map(function (u) {
            var linhas = ["<strong>" + esc(u.nome) + "</strong>"];
            var morada = [u.morada, u.bairro, u.municipio].filter(Boolean).join(", ");
            if (morada) linhas.push(esc(morada));
            if (u.horario) linhas.push("Atendimento: " + esc(u.horario));
            var contactos = [u.telefone ? "Telefone " + telefones(u.telefone) : "", u.whatsapp ? "WhatsApp " + telefones(u.whatsapp, true) : ""].filter(Boolean);
            if (contactos.length) linhas.push(contactos.join(" · "));
            if (u.o_que_levar) linhas.push("Leve: " + esc(u.o_que_levar));
            return "<li>" + linhas.join("<br>") + "</li>";
          }).join("") + "</ul></div>" : "") +
        (!temTurmas && c.como_me_inscrever && c.como_me_inscrever.length ? '<details class="passos"><summary>Como se inscrever</summary><ol>' +
          c.como_me_inscrever.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ol></details>" : "") +
        // botão do curso por baixo das turmas: só se levar a outra página que não a de uma das turmas
        // (antes repetia o mesmo edital ou a mesma lista; pedido do responsável, 23/11/2026)
        (temTurmas ? (turmas.some(function (t) { return semAncora(t.link) === semAncora(c.url); }) ? "" :
                     '<p class="link-oficial"><a href="' + esc(c.url) + '" rel="noopener">' +
                     ((c.destino || {}).tipo === "lista" ? "Ver todos os cursos na página oficial" : (c.destino || {}).tipo === "pdf" ? "Ver o edital (PDF)" : "Ver outras turmas na página oficial") + "</a></p>")
                   : (function () {
                       var b = destinoBotao(c.destino, false, "", (c.antes || []).indexOf("govbr") >= 0);
                       // curso «por abrir»: a inscrição ainda não abriu, o botão só serve para ver a página oficial
                       if (porAbrir(c)) b = { rotulo: "Ver a página oficial",
                                              nota: "A inscrição ainda não abriu. Volte a partir de " + esc(dataBonita(c.abertura)) + "." };
                       return (b.nota ? '<p class="guia-link">' + b.nota + "</p>" : "") +
                         '<a class="botao secundario" href="' + esc(c.url) + '" rel="noopener">' + esc(b.rotulo) + "</a>";
                     })()) +
        (!temTurmas ? lembrarHtml(c.titulo, c.inscricoes_ate, c.url, c.modalidade === "online" ? "On-line" : c.cidade, porAbrir(c) ? c.abertura : "") : "") +
        '<p class="verificado">' + (c.verificado_em ? "Verificado em " + esc(c.verificado_em.slice(8, 10) + "/" + c.verificado_em.slice(5, 7) + "/" + c.verificado_em.slice(0, 4)) + ". " : "") +
        "Confirme sempre na página oficial antes de ir." + avisarErroHtml(c, true) + "</p></li>";
    }

    // Cursos do mesmo edital (26/11/2026, pedido do responsável): vários cursos presenciais sem turmas, com o mesmo
    // link, a mesma entidade, o mesmo prazo e os mesmos requisitos, aparecem num só cartão com a lista de cursos e
    // cidades (antes eram cartões quase iguais, um por curso, ex.: os 9 cursos do Proeja do Ifap).
    function chaveGrupo(c) {
      if ((c.turmas || []).length || c.modalidade === "online" || !c.url) return "";
      return [semAncora(c.url), c.entidade || "", c.inscricoes_ate || "", c.abertura || "", c.vagas || "",
              String(c.gratuidade_comprovada), c.matricula || "", JSON.stringify(requisitosDe(c, null)),
              JSON.stringify(c.como_me_inscrever || [])].join("\u0001");
    }
    function agrupar(res) {
      var porChave = {}, itens = [];
      res.forEach(function (c) {
        var k = chaveGrupo(c);
        if (k && porChave[k]) { porChave[k].push(c); return; }
        var g = [c];
        if (k) porChave[k] = g;
        itens.push(g);
      });
      return itens;
    }
    function grupoHtml(cs) {
      var c = cs[0];
      var comuns = function (f) { var v = f(c); return cs.every(function (x) { return f(x) === v; }) ? v : ""; };
      var factos = [];
      function marca(cls, txt, filtro) { return '<li class="' + cls + ' filtravel"><button type="button" class="filtro" data-filtro="' +
        esc(filtro) + '" title="Mostrar só os cursos assim">' + esc(txt) + "</button></li>"; }
      if (cs.some(function (x) { return novosDesde && (x.primeiro_visto || "").slice(0, 10) > novosDesde; })) factos.push('<li class="novo">Novo desde a sua última visita</li>');
      else if (cs.some(recente)) factos.push(marca("novo", "Novo!", "facilita:recente"));
      var breve = terminaEmBreve(c);
      if (breve) factos.unshift(marca("urgente", quandoTermina(prazoProximo(c)), "facilita:fecha_breve"));
      factos.push(marca("local", "Presencial: " + ([comuns(function (x) { return x.cidade || ""; }), c.regiao].filter(Boolean).join(", ") || String(nomesLocal[c.local] || "").replace(/^Brasil\s*[–-]\s*/, "")), "onde:" + c.local));
      if (c.gratuidade_comprovada === false) factos.push(marca("atencao", "Gratuidade por confirmar", "marca:grat-confirmar"));
      if (porAbrir(c)) factos.push('<li class="atencao">Inscrições abrem em ' + esc(dataBonita(c.abertura)) + (c.inscricoes_ate ? " e vão até " + esc(dataBonita(c.inscricoes_ate)) : "") + "</li>");
      else if (c.inscricoes_ate && !breve) factos.push('<li class="atencao">Inscrições até ' + esc(dataBonita(c.inscricoes_ate)) + "</li>");
      if (c.situacao === "Por confirmar") factos.push('<li class="atencao">Inscrições por confirmar</li>');
      if (c.matricula) factos.push("<li>Se for aprovado: matrícula " + esc(c.matricula) + "</li>");
      var turnoComum = comuns(function (x) { return (x.turnos || []).join(","); });
      turnoComum.split(",").filter(Boolean).forEach(function (t) { if (TURNO[t]) factos.push(t === "Noite" ? marca("local", TURNO[t], "facilita:noite") : "<li>" + esc(TURNO[t]) + "</li>"); });
      var condicoes = [];
      (c.etiquetas || []).forEach(function (e) { condicoes.push("Sobre as vagas, a fonte diz: “" + esc(e.frase.replace(/[.\s]+$/, "")) + "”"); });
      if (c.gratuidade_comprovada === false) condicoes.push(GRATUIDADE_AVISO);
      var lista = cs.map(function (x) {
        var det = [x.cidade, turnoComum ? "" : (x.turnos || []).map(function (t) { return TURNO[t] || t; }).join(", "), x.duracao,
                   x.inicio ? "aulas começam em " + dataCurtaG(x.inicio) : ""].filter(Boolean);
        return '<li id="' + idCartao(x, todos.indexOf(x)) + '"><strong>' + esc(x.titulo) + "</strong>" +
          (det.length ? '<br><span class="discreto">' + esc(det.join(" · ")) + "</span>" : "") +
          (x.descricao ? '<details class="grupo-descricao"><summary>Sobre este curso</summary>' + descricaoHtml(x, false) + "</details>" : "") + "</li>";
      }).join("");
      var b = destinoBotao(c.destino, false, "", (c.antes || []).indexOf("govbr") >= 0);
      if (porAbrir(c)) b = { rotulo: "Ver a página oficial", nota: "A inscrição ainda não abriu. Volte a partir de " + esc(dataBonita(c.abertura)) + "." };
      var verif = cs.map(function (x) { return x.verificado_em || ""; }).filter(Boolean).sort()[0] || "";
      var cidadeComum = comuns(function (x) { return x.cidade || ""; });
      return '<li class="curso grupo"><h2>' + cs.length + " cursos" + (cidadeComum ? " em " + esc(cidadeComum) : "") + " com a mesma inscrição</h2>" +
        (c.entidade ? '<p class="entidade">' + esc(c.entidade) + "</p>" : "") +
        (c.vagas === "sorteio" ? '<p class="vagas-aviso">Vagas por sorteio: inscrever-se não garante a vaga.</p>'
         : c.vagas === "ordem" ? '<p class="vagas-aviso">Vagas por ordem de inscrição: inscreva-se cedo.</p>' : "") +
        '<ul class="factos">' + factos.join("") + "</ul>" +
        (condicoes.length ? '<p class="condicao">' + condicoes.join(". ") + "</p>" : "") +
        '<div class="onde grupo-cursos"><p class="onde-titulo">Cursos e cidades</p><ul>' + lista + "</ul></div>" +
        requisitosHtml(requisitosDe(c, null)) + antesHtml(c) +
        (c.como_me_inscrever && c.como_me_inscrever.length ? '<details class="passos"><summary>Como se inscrever</summary><ol>' +
          c.como_me_inscrever.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ol></details>" : "") +
        (b.nota ? '<p class="guia-link">' + b.nota + "</p>" : "") +
        '<a class="botao secundario" href="' + esc(c.url) + '" rel="noopener">' + esc(b.rotulo) + "</a>" +
        lembrarHtml(cs.length + " cursos (" + (c.entidade || "") + ")", c.inscricoes_ate, c.url, comuns(function (x) { return x.cidade || ""; }), porAbrir(c) ? c.abertura : "") +
        '<p class="verificado">' + (verif ? "Verificado em " + esc(verif.slice(8, 10) + "/" + verif.slice(5, 7) + "/" + verif.slice(0, 4)) + ". " : "") +
        "Confirme sempre na página oficial antes de ir." + avisarErroHtml(c, true) + "</p></li>";
    }

    // «no Ceará», «na Bahia», «em Pernambuco», «em Portugal»
    function noLugar(nome) {
      var no = ["Acre", "Amapá", "Amazonas", "Ceará", "Distrito Federal", "Espírito Santo", "Maranhão", "Mato Grosso",
        "Mato Grosso do Sul", "Pará", "Paraná", "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Tocantins"];
      return (no.indexOf(nome) >= 0 ? "no " : ["Bahia", "Paraíba"].indexOf(nome) >= 0 ? "na " : "em ") + nome;
    }
    function filtrar() {
      var o = onde.value;
      var buscaAtual = { quero: escolhidas, onde: o, facilita: barreiras, marca: marcaEscolhida, cidade: cidade.value,
                         certificado: !!(certificado && certificado.checked), duracao: duracao ? duracao.value : "",
                         texto: texto.value };
      var res = todos.filter(function (c) { return passaBusca(c, buscaAtual); });
      // ordem: presenciais primeiro; dentro de cada grupo, o prazo de inscrição mais próximo primeiro; os cursos sem
      // prazo (ex.: on-line sob demanda) no fim, do mais recente na planilha para o mais antigo (22/11/2026)
      res.sort(function (a, b) {
        var pa = a.modalidade === "online" ? 1 : 0, pb = b.modalidade === "online" ? 1 : 0;
        if (pa !== pb) return pa - pb;
        var xa = prazoProximo(a), xb = prazoProximo(b);
        if (xa && xb && xa !== xb) return xa.localeCompare(xb);
        if (!!xa !== !!xb) return xa ? -1 : 1;
        return (b.primeiro_visto || "").localeCompare(a.primeiro_visto || "");
      });
      var presenciais = res.filter(function (c) { return c.modalidade !== "online"; }).length;
      var resumo = res.length === 1 ? "1 curso" : res.length + " cursos";
      if (o && o !== "online" && res.length) resumo += res.length === 1 ? " presencial" : " presenciais";
      contagem.textContent = res.length ? resumo : "";
      medirBusca(texto.value, res.length);
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
      if (periodo) ativos.push(["periodo", periodo.ini === periodo.fim ? "Inscrições em " + dataBonita(periodo.ini)
                                                                       : "Inscrições de " + dataBonita(periodo.ini) + " a " + dataBonita(periodo.fim)]);
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
      // qualquer mudança de filtro volta à página 1; só os botões da paginação (e os links #curso-…) mantêm a página
      ultimoRes = res;
      var itens = agrupar(res);
      var totalPaginas = Math.max(1, Math.ceil(itens.length / POR_PAGINA));
      if (!manterPagina) pagina = 1;
      manterPagina = false;
      if (pagina > totalPaginas) pagina = totalPaginas;
      var daPagina = itens.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA);
      desenharPaginas(itens.length, totalPaginas);
      lista.innerHTML = res.length ? daPagina.map(function (g) { return g.length > 1 ? grupoHtml(g) : cursoHtml(g[0], todos.indexOf(g[0])); }).join("") :
        (o && o !== "online"
          ? '<li class="vazio">Não há cursos presenciais ' + esc(noLugar(onde.options[onde.selectedIndex].text.replace(/^Brasil\s*[–-]\s*/, ""))) +
            (cidade.value ? " em " + esc(cidade.value) : "") + (ativos.length ? " com estas escolhas" : "") +
            ' no momento. Os cursos on-line servem em qualquer lugar. <button type="button" class="filtro botao secundario pequeno" data-filtro="onde:online">Ver os cursos on-line</button></li>'
          : '<li class="vazio">Não há cursos com essas opções no momento. Tente escolher menos opções ou "Mostrar tudo" em "Onde você está?". A lista é atualizada todo dia.</li>');

      // «ler mais» só nas descrições que não cabem nas 2 linhas
      lista.querySelectorAll(".descricao.curta").forEach(function (p) {
        if (p.scrollHeight <= p.clientHeight + 2) { p.classList.remove("curta"); return; }
        var b = document.createElement("button");
        b.type = "button"; b.className = "ler-mais"; b.textContent = "ler mais"; b.setAttribute("aria-expanded", "false");
        b.addEventListener("click", function () {
          var aberta = p.classList.toggle("curta") === false;
          b.textContent = aberta ? "ler menos" : "ler mais"; b.setAttribute("aria-expanded", aberta ? "true" : "false");
        });
        p.insertAdjacentElement("afterend", b);
      });
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
      if (texto.value.trim()) q.set("texto", texto.value.trim().slice(0, 60));
      if (pagina > 1) q.set("pagina", pagina);
      desenharBuscasSalvas(q.toString());
      history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q.toString() : ""));
    }

    function desenharPaginas(n, total) {
      if (total <= 1) { navsPaginas.forEach(function (nav) { nav.hidden = true; nav.innerHTML = ""; }); return; }
      var ini = (pagina - 1) * POR_PAGINA + 1, fim = Math.min(n, pagina * POR_PAGINA);
      var botao = function (i, rotulo, aria) {
        return '<li><button type="button" class="botao secundario pequeno" data-pagina="' + i + '"' +
          (aria ? ' aria-label="' + aria + '"' : "") + ">" + rotulo + "</button></li>";
      };
      var html = '<p class="paginacao-texto">Mostrando ' + ini + "–" + fim + " de " + n + (n === ultimoRes.length ? " cursos" : " cartões") + " (página " + pagina +
        " de " + total + ")</p><ul>" + (pagina > 1 ? botao(pagina - 1, "‹ Anterior", "Página anterior") : "");
      var anterior = 0;
      for (var i = 1; i <= total; i++) {
        if (i !== 1 && i !== total && Math.abs(i - pagina) > 1) continue;
        if (i - anterior > 1) html += '<li class="reticencias" aria-hidden="true">…</li>';
        html += i === pagina ? '<li><span class="pagina-atual" aria-current="page">' + i + "</span></li>" : botao(i, String(i), "Página " + i);
        anterior = i;
      }
      html += (pagina < total ? botao(pagina + 1, "Próxima ›", "Próxima página") : "") + "</ul>";
      navsPaginas.forEach(function (nav) { nav.hidden = false; nav.innerHTML = html; });
    }
    navsPaginas.forEach(function (nav) { nav.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-pagina]");
      if (!b) return;
      pagina = parseInt(b.getAttribute("data-pagina"), 10) || 1;
      manterPagina = true;
      filtrar();
      medir("mudar_pagina", { numero_pagina: pagina });  // "pagina" é o nome da página do site (medir)
      contagem.scrollIntoView({ behavior: "smooth", block: "start" });
    }); });
    // links para um cartão (#curso-…, da página inicial ou de «Terminam em breve»): abrir a página onde ele está
    function irParaCurso(id) {
      var i = -1;
      agrupar(ultimoRes).some(function (g, j) {
        if (g.some(function (c) { return idCartao(c, todos.indexOf(c)) === id; })) { i = j; return true; } return false; });
      if (i < 0) return false;
      var p = Math.floor(i / POR_PAGINA) + 1;
      if (p !== pagina) { pagina = p; manterPagina = true; filtrar(); }
      var alvo = document.getElementById(id);
      if (alvo) { alvo.scrollIntoView(); alvo.classList.add("destacado"); }
      return true;
    }
    document.addEventListener("click", function (ev) {
      var a = ev.target.closest('a[href^="#curso-"]');
      if (a && irParaCurso(a.getAttribute("href").slice(1))) ev.preventDefault();
    });

    function textoMarca(m) {
      return m === "cert-gratuito" ? "Certificado gratuito" : m === "grat-confirmar" ? "Gratuidade por confirmar" : m.replace(/^(pub|acc):/, "");
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
    // Medição: o que as pessoas procuram (e não encontram) e que filtros usam
    var ultimaBusca = "", relogioBusca = null;
    function medirBusca(valor, n) {
      clearTimeout(relogioBusca);
      relogioBusca = setTimeout(function () {
        var termo = termoSeguro(valor);
        if (termo.length < 2 || termo === ultimaBusca) return;
        ultimaBusca = termo;
        var dados = { termo: termo, resultados: n, estado: onde.value || "todos" };
        medir("busca", dados);
        if (!n) medir("busca_sem_resultado", { termo: termo, estado: onde.value || "todos" });
      }, 1500);
    }
    function nomeOpcao(sel) { var o = sel.options[sel.selectedIndex]; return o ? o.textContent.trim() : sel.value; }
    onde.addEventListener("change", function () { medir("filtro", { filtro: "estado", valor: nomeOpcao(onde) }); });
    cidade.addEventListener("change", function () { if (cidade.value) medir("filtro", { filtro: "cidade", valor: cidade.value, estado: nomeOpcao(onde) }); });
    if (duracao) duracao.addEventListener("change", function () { if (duracao.value) medir("filtro", { filtro: "duracao", valor: duracao.value }); });
    if (certificado) certificado.addEventListener("change", function () { if (certificado.checked) medir("filtro", { filtro: "certificado", valor: "gratuito" }); });
    ulBarreiras.addEventListener("click", function (ev) {
      var b = ev.target.closest("button.opcao");
      if (b && b.getAttribute("aria-pressed") === "true") medir("filtro", { filtro: "facilita", valor: b.getAttribute("data-barreira") });
    });
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
      else if (tipo === "periodo") { periodo = null; calendarioRedesenhar(); }
      else if (tipo === "texto") texto.value = "";
      else if (tipo === "tudo") {
        escolhidas.slice().forEach(tirarQuero);
        barreiras.slice().forEach(tirarFacilita);
        if (duracao) duracao.value = "";
        if (certificado) certificado.checked = false;
        cidade.value = "";
        texto.value = "";
        periodo = null; calendarioRedesenhar();
      }
      filtrar();
    });
    // clicar numa marca do curso (ex.: On-line, Certificado gratuito, Para mulheres) filtra a lista por ela
    lista.addEventListener("click", function (ev) {
      var f = ev.target.closest("button.filtro");
      if (!f) return;
      var partes = f.getAttribute("data-filtro").split(":"), tipo = partes.shift(), valor = partes.join(":");
      // botão «Ver os cursos on-line» de um estado sem cursos presenciais (medir antes de mudar o filtro)
      if (f.classList.contains("botao") && valor === "online") medir("ver_online_sem_presencial", { estado: nomeOpcao(onde) });
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
    // celular: quem chega já com uma escolha (da página inicial) vê logo a contagem e os cursos; os filtros ficam
    // na caixa «Mudar a busca». Em telas largas, a caixa fica sempre aberta.
    // ao imprimir a lista, os detalhes das turmas saem abertos
    window.addEventListener("beforeprint", function () {
      document.querySelectorAll(".turma-detalhes").forEach(function (d) { d.open = true; });
    });
    var caixaFiltros = el("cursos-filtros-caixa");
    if (caixaFiltros && window.matchMedia) {
      var largo = window.matchMedia("(min-width: 64rem)");
      var chegouComEscolha = ["quero", "onde", "facilita", "marca", "certificado", "duracao"].some(function (k) { return params.has(k); });
      caixaFiltros.open = largo.matches || !chegouComEscolha;
      var ajustar = function () { if (largo.matches) caixaFiltros.open = true; };
      if (largo.addEventListener) largo.addEventListener("change", ajustar); else if (largo.addListener) largo.addListener(ajustar);
    }
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
      todos = semFuturos(r[0].cursos);
      // link com uma marca que nenhum curso tem mais (ex.: todas as gratuidades já confirmadas): mostrar todos e dizer porquê
      if (marcaEscolhida && !todos.some(function (c) { return marcasDe(c).indexOf(marcaEscolhida) >= 0; })) {
        marcaSumiu = textoMarca(marcaEscolhida); marcaEscolhida = "";
      }
      (r[1].guias || []).forEach(function (g) { guiasPorId[g.id] = g; });
      var salvas = lerBuscas();
      salvas.forEach(function (b) {
        if (buscaAoAbrir && chaveBusca(b.q) === buscaAoAbrir) { novosDesde = b.visto || ""; b.visto = hojeIso(); }
      });
      if (novosDesde !== null) gravarBuscas(salvas);
      esconderSemCursos(el("cursos-opcoes"), "data-id", escolhidas, necessidadeTemCurso(todos));
      esconderSemCursos(ulBarreiras, "data-barreira", barreiras, function (id) {
        return todos.some(function (c) { return passaBarreira(c, id); });
      });
      preencherCidades(params.get("cidade") || "");
      filtrar();
      // vindo da página inicial (#curso-…): ir ao cartão desse curso
      if (hashInicial && /^#curso-/.test(hashInicial)) irParaCurso(hashInicial.slice(1));
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
    var estado = el("kit-estado"), cidade = el("kit-cidade"), comOnline = el("kit-online"), lista = el("kit-lista");
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
      if (c.renda) { var rs = simples(c.renda); l.push(rs.charAt(0).toLowerCase() + rs.slice(1)); }
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
      var quando = [c.inicio ? "aulas começam em " + dataCurta(c.inicio) : "", turnoSeguro(c)].filter(Boolean).join(", ");
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
      var q = new URLSearchParams(); if (estado.value) q.set("estado", estado.value); q.set("cidade", cidade.value); if (!comOnline.checked) q.set("online", "nao");
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
                   c.inicio ? "aulas começam em " + dataCurta(c.inicio) : "",
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
    // Google Analytics: um evento por clique nos botões, com o município e o estado (como na busca principal; 25/11/2026)
    var ufDaCidade = {}, nomeLocal = {};
    (site.locais || []).forEach(function (l) { nomeLocal[l.id] = String(l.rotulo || "").replace(/^Brasil\s*[–-]\s*/, ""); });
    function estadoDe(cid) {
      if (estado.value) return nomeLocal[estado.value] || estado.value;
      return Object.keys(ufDaCidade[cid] || {}).map(function (id) { return nomeLocal[id] || id; }).join(" / ");
    }
    // municípios só do estado escolhido (pedido do responsável, 25/11/2026)
    var todasCidades = [];
    function preencherCidades(valor) {
      var doEstado = estado.value ? todasCidades.filter(function (x) { return (ufDaCidade[x] || {})[estado.value]; }) : [];
      cidade.innerHTML = '<option value="">' + (estado.value ? "Escolha o município" : "Escolha primeiro o estado") + "</option>" +
        doEstado.map(function (x) { return '<option value="' + esc(x) + '"' + (x === valor ? " selected" : "") + ">" + esc(x) + "</option>"; }).join("");
      cidade.disabled = !estado.value;
    }
    estado.addEventListener("change", function () {
      preencherCidades(""); mostrar();
      if (estado.value) history.replaceState(null, "", location.pathname + "?estado=" + encodeURIComponent(estado.value));
      else history.replaceState(null, "", location.pathname);
    });
    function medirBotao(botao, extra) {
      var d = { botao: botao, municipio: cidade.value || "(nenhum)", estado: estadoDe(cidade.value) || "(nenhum)",
                com_online: comOnline.checked ? "sim" : "nao" };
      Object.keys(extra || {}).forEach(function (k) { d[k] = extra[k]; });
      medir("encaminhar_botao", d);
    }
    el("kit-imprimir").addEventListener("click", function () { medirBotao("imprimir_lista"); window.print(); });
    el("kit-whatsapp").addEventListener("click", function () { medirBotao("copiar_texto_whatsapp"); copiar(textoWhatsapp(), "Texto copiado. Cole no WhatsApp."); });
    el("kit-link").addEventListener("click", function () { medirBotao("copiar_link_lista"); copiar(location.href, "Link copiado."); });
    lista.addEventListener("click", function (ev) {
      var b = ev.target.closest("button[data-ficha]"); if (!b) return;
      var f = b.closest(".ficha"), hf = f.querySelector("h2, h3");
      medirBotao("imprimir_ficha", { curso: hf ? hf.textContent.trim().slice(0, 100) : "" }); f.classList.add("imprimir-esta"); document.body.classList.add("so-uma-ficha");
      window.print();
      setTimeout(function () { f.classList.remove("imprimir-esta"); document.body.classList.remove("so-uma-ficha"); }, 500);
    });
    cidade.addEventListener("change", mostrar);
    comOnline.addEventListener("change", mostrar);
    cidade.addEventListener("change", function () { if (cidade.value) medir("montar_lista", { cidade: cidade.value, municipio: cidade.value, estado: estadoDe(cidade.value) }); });
    comOnline.checked = params.get("online") !== "nao";

    Promise.all([carregar("dados/cursos.json"), carregar("dados/guias.json").catch(function () { return { guias: [] }; })]).then(function (r) {
      todos = semFuturos(r[0].cursos); atualizado = r[0].atualizado ? dataCurta(r[0].atualizado.slice(0, 10)) + "/" + r[0].atualizado.slice(0, 4) : "";
      (r[1].guias || []).forEach(function (g) { guias[g.id] = g; });
      var cids = {};
      todos.forEach(function (c) {
        if (c.modalidade !== "online" && c.situacao === "Aberto" && !c.em_revisao) cidadesDe(c).forEach(function (x) {
          cids[x] = 1; if (c.local) (ufDaCidade[x] = ufDaCidade[x] || {})[c.local] = 1;
        });
      });
      todasCidades = ordenarCidades(Object.keys(cids));
      var comCidades = {};
      todasCidades.forEach(function (x) { Object.keys(ufDaCidade[x] || {}).forEach(function (id) { comCidades[id] = 1; }); });
      Object.keys(comCidades).sort(function (a, b) { return (nomeLocal[a] || a).localeCompare(nomeLocal[b] || b, "pt-BR"); }).forEach(function (id) {
        var op = document.createElement("option"); op.value = id; op.textContent = nomeLocal[id] || id; estado.appendChild(op);
      });
      // links antigos só com ?cidade=: o estado vem dos cursos daquele município
      var pe = params.get("estado"), pc = params.get("cidade");
      if (!pe && pc && ufDaCidade[pc]) pe = Object.keys(ufDaCidade[pc])[0];
      if (pe && comCidades[pe]) estado.value = pe;
      preencherCidades(pc || "");
      mostrar();
    }).catch(function () { lista.innerHTML = '<p class="vazio">Não foi possível carregar os cursos. Atualize a página daqui a pouco.</p>'; });
  }

  // Google Analytics só com consentimento (LGPD; decisão do responsável, 22/11/2026).
  // Sem ID configurado (config.json → google_analytics) não aparece aviso nem se carrega nada.
  // Antes de a pessoa aceitar, nenhum script do Google é carregado e nenhum cookie é gravado.
  (function () {
    var id = document.body.getAttribute("data-ga") || "";
    var aviso = document.getElementById("aviso-cookies");
    var mudar = document.querySelectorAll('[data-cookies="mudar"]');
    if (!/^G-[A-Z0-9]+$/.test(id) || !aviso) { mudar.forEach(function (b) { b.hidden = true; }); return; }
    var CHAVE = "cookies-analytics";
    function ler() { try { return localStorage.getItem(CHAVE); } catch (e) { return null; } }
    function gravar(v) { try { localStorage.setItem(CHAVE, v); } catch (e) {} }
    var ligado = false;
    function ligar() {
      window["ga-disable-" + id] = false; window.__gaLigado = true;
      if (ligado) return; ligado = true;
      window.dataLayer = window.dataLayer || [];
      window.gtag = function () { window.dataLayer.push(arguments); };
      window.gtag("js", new Date());
      window.gtag("config", id);
      var s = document.createElement("script"); s.async = true;
      s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
      document.head.appendChild(s);
    }
    function desligar() {
      window["ga-disable-" + id] = true; window.__gaLigado = false;
      document.cookie.split(";").forEach(function (c) {
        var n = c.split("=")[0].trim();
        if (/^_ga/.test(n)) {
          document.cookie = n + "=; Max-Age=0; path=/";
          document.cookie = n + "=; Max-Age=0; path=/; domain=" + location.hostname;
          document.cookie = n + "=; Max-Age=0; path=/; domain=." + location.hostname;
        }
      });
    }
    function mostrarAviso(sim) {
      aviso.hidden = !sim;
      document.body.style.paddingBottom = sim ? aviso.offsetHeight + "px" : "";
    }
    document.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-cookies]");
      if (b) {
        var v = b.getAttribute("data-cookies");
        if (v === "mudar") { mostrarAviso(true); aviso.querySelector("button").focus(); return; }
        gravar(v); mostrarAviso(false);
        if (v === "sim") ligar(); else desligar();
        return;
      }
      // Quem aceitou: cliques que interessam (inscrição, lembretes, gov.br, fichas, canais)
      if (!window.__gaLigado) return;
      var curso = ev.target.closest(".curso, .ficha"), h = curso && curso.querySelector("h2, h3");
      var nomeCurso = h ? h.textContent.trim().slice(0, 100) : "";
      var a = ev.target.closest("a"), bt = ev.target.closest("button");
      if (a && a.classList.contains("lembrar")) { medir("lembrete_prazo", { curso: nomeCurso }); return; }
      if (a && /(^|\/)antes\.html#govbr$/.test(a.getAttribute("href") || "")) { medir("ver_passo_govbr", { curso: nomeCurso }); return; }
      if (a && /whatsapp\.com/i.test(a.href)) { medir("abrir_canal_whatsapp", {}); return; }
      if (a && a.closest(".aviso") && /envie o curso/i.test(a.textContent)) { medir("abrir_formulario_parceiros", {}); return; }
      if (a && a.closest(".guia")) { var g = a.closest(".guia"); medir("abrir_fonte_guia", { guia: g.id }); return; }
      if (a && a.classList.contains("botao") && curso) {
        var dest = ""; try { dest = new URL(a.href, location.href).hostname; } catch (e) {}
        medir("abrir_inscricao", { curso: nomeCurso, destino: dest }); return;
      }
      // os botões da página «Para quem encaminha» (imprimir, WhatsApp, link, ficha) são medidos em encaminhar(),
      // no evento «encaminhar_botao», com o município e o estado
    });
    var escolha = ler();
    if (escolha === "sim") ligar();
    else if (escolha !== "nao") mostrarAviso(true);
  })();

  // botão «Copiar a chave» (Pix, página Sobre)
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("[data-copiar]");
    if (!b) return;
    var v = b.getAttribute("data-copiar");
    var feito = function () { var t0 = b.textContent; b.textContent = "Chave copiada"; setTimeout(function () { b.textContent = t0; }, 2500); };
    if (navigator.clipboard) navigator.clipboard.writeText(v).then(feito, function () { window.prompt("Copie a chave Pix:", v); });
    else window.prompt("Copie a chave Pix:", v);
    medir("copiar_pix", {});
  });
  carregar("dados/site.json").then(function (site) {
    FORM = site.formulario || {};
    if (pagina === "numeros") { numeros(site); return; }
    if (pagina === "antes") { antes(); return; }
    if (pagina === "encaminhar") { encaminhar(site); return; }
    if (pagina === "inicio") inicio(site);
    else if (pagina === "cursos") cursos(site);
    else if (pagina === "noticias") noticias(site);
  });
})();
