// Teste do site antes de publicar (26/11/2026): abre docs/cursos.html num navegador simulado (jsdom), com os dados
// gerados, percorre todas as páginas da lista de cursos e falha se a lista não desenhar ou se houver um erro de
// JavaScript. Nasceu de um erro real: um cartão de grupo chamava uma função inexistente e a lista inteira mostrava
// «Não foi possível carregar os cursos». Uso: node scripts/testar_site.js (precisa de `npm i jsdom`).
const { JSDOM, VirtualConsole } = require("jsdom");
const fs = require("fs"), path = require("path");
const dir = path.join(__dirname, "..", "docs");
const erros = [];
const vc = new VirtualConsole();
vc.on("jsdomError", (e) => erros.push("JS: " + e.message + " " + ((e.detail && e.detail.stack) || "").split("\n").slice(0, 3).join(" | ")));
const dom = new JSDOM(fs.readFileSync(path.join(dir, "cursos.html"), "utf8"),
  { runScripts: "outside-only", url: "https://teste/social-project/cursos.html", virtualConsole: vc });
const w = dom.window;
const ler = (u) => fs.readFileSync(path.join(dir, String(u).replace(/^https:\/\/teste\/social-project\//, "").split("?")[0]), "utf8");
w.fetch = (u) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(ler(u))), text: () => Promise.resolve(ler(u)) });
w.scrollTo = () => {}; w.Element.prototype.scrollIntoView = function () {};
w.matchMedia = () => ({ matches: false, addListener() {}, addEventListener() {} });
let src = fs.readFileSync(path.join(dir, "app.js"), "utf8");
// mostra o erro que a página esconderia atrás de «Não foi possível carregar os cursos»
src = src.replace(/\.catch\(function \(\) \{(\s*)lista\.innerHTML = '<(li|p) class="vazio">Não foi possível/g,
  ".catch(function (e) { window.__erroLista = String(e && e.stack || e);$1lista.innerHTML = '<$2 class=\"vazio\">Não foi possível");
w.eval(src);
w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
const falhou = () => [...w.document.querySelectorAll(".vazio")].some((x) => /Não foi possível/.test(x.textContent));
setTimeout(async () => {
  let paginas = 1;
  if (!falhou()) {
    for (let i = 0; i < 500; i++) {
      const prox = [...w.document.querySelectorAll("button, a")].find((b) => /Próxima/.test(b.textContent));
      if (!prox || prox.disabled) break;
      prox.click(); paginas++;
      await new Promise((r) => setTimeout(r, 20));
      if (falhou()) break;
    }
  }
  if (falhou()) erros.unshift("A lista de cursos não desenhou (página " + paginas + "): " + (w.__erroLista || "sem detalhe"));
  if (erros.length) { console.log("TESTE DO SITE FALHOU:\n" + erros.slice(0, 10).join("\n")); process.exit(1); }
  console.log("Teste do site: ok (" + paginas + " páginas da lista, sem erros de JavaScript).");
  process.exit(0);
}, 3000);
