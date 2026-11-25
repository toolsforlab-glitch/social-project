// Auditoria dos requisitos mostrados no site (regra do responsável, 25/11/2026): corre depois de gerar o site e
// confere, em todos os cursos e turmas, que o bloco «Requisitos» não repete idade, escolaridade ou renda, não tem
// texto cortado e que cada linha tirada da fonte existe letra a letra no texto da fonte (nada foi reescrito; decisão
// do responsável, 25/11/2026). As únicas linhas escritas pelo site são as geradas a partir de números ou campos
// («Ter 18 anos ou mais», escolaridade do campo do curso, experiência nos cursos de aperfeiçoamento).
// Usa as mesmas funções do site (site/app.js). Só avisa; não impede a publicação.
const fs = require("fs"), path = require("path");
const raiz = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(raiz, "site", "app.js"), "utf8");
const trecho = (a, b) => src.slice(src.indexOf(a), src.indexOf(b));
eval(trecho("  var ESCOLARIDADE_TXT", "  // Requisitos: o texto da fonte") + trecho("  // Requisitos: o texto da fonte", "  function requisitosHtml"));
const cursos = JSON.parse(fs.readFileSync(path.join(raiz, "docs", "dados", "cursos.json"), "utf8")).cursos;
const norm = x => String(x || "").toLowerCase().replace(/\s+/g, " ").trim();
const GERADO = x => /^Ter (de )?\d+ (a \d+ )?anos/.test(x) || /^Ter até \d+ anos/.test(x) ||
  Object.values(ESCOLARIDADE_TXT).indexOf(x) >= 0 || /^Ter experiência na área \(é um curso de aperfeiçoamento\)$/.test(x);
let n = 0; const avisos = [];
function checar(l, onde, c, t) {
  const fonte = norm([t && t.escolaridade, c.requisitos, c.renda, c.exclusivo_para].join(" "));
  n++;
  const idade = l.filter(x => /\d+\s*anos\b/.test(x) && !/renda|escolaridade|experi/i.test(x));
  const escola = l.filter(x => /^escolaridade/i.test(x)), renda = l.filter(x => /renda/i.test(x));
  if (idade.length > 1 || escola.length > 1 || renda.length > 1) avisos.push(`repetição em ${onde}: ${l.join(" / ")}`);
  l.forEach(x => {
    const sem = norm(x.replace(/^Escolaridade: /, ""));
    if (!GERADO(x) && fonte.indexOf(sem) < 0) avisos.push(`texto diferente da fonte em ${onde}: ${x}`);
    if (/\([^)]*$/.test(x)) avisos.push(`texto cortado em ${onde}: ${x}`);
  });
}
cursos.forEach(c => {
  const onde = `${c.id} ${String(c.titulo || "").slice(0, 40)}`;
  const turmas = c.turmas || [];
  if (turmas.length) turmas.forEach(t => checar(requisitosDe(c, t), onde, c, t)); else checar(requisitosDe(c, null), onde, c, null);
});
console.log(`Auditoria dos requisitos: ${n} blocos, ${avisos.length} aviso(s).`);
avisos.slice(0, 40).forEach(a => console.log("  AVISO " + a.slice(0, 300)));
