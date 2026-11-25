// Auditoria dos requisitos mostrados no site (regra do responsável, 25/11/2026): corre depois de gerar o site e
// confere, em todos os cursos e turmas, que o bloco «Requisitos» não repete idade, escolaridade ou renda, não tem
// termos técnicos (per capita, 2,0, federação, possuir, maior ou igual, rótulos «Requisito …:») nem texto cortado.
// Usa as mesmas funções do site (site/app.js). Só avisa; não impede a publicação.
const fs = require("fs"), path = require("path");
const raiz = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(raiz, "site", "app.js"), "utf8");
const trecho = (a, b) => src.slice(src.indexOf(a), src.indexOf(b));
eval(trecho("  var ESCOLARIDADE_TXT", "  // Linguagem simples") + trecho("  var NUMEROS", "  function requisitosHtml"));
const cursos = JSON.parse(fs.readFileSync(path.join(raiz, "docs", "dados", "cursos.json"), "utf8")).cursos;
const TECNICO = /per capita|\d,0\b|federa[çc]|\bpossuir\b|maior ou igual|requisito (de|espec)|m[íi]nima\s*:|\b0\d\s*\(/i;
let n = 0; const avisos = [];
function checar(l, onde) {
  n++;
  const idade = l.filter(x => /\d+\s*anos\b/.test(x) && !/renda|escolaridade/i.test(x));
  const escola = l.filter(x => /^escolaridade/i.test(x)), renda = l.filter(x => /renda/i.test(x));
  if (idade.length > 1 || escola.length > 1 || renda.length > 1) avisos.push(`repetição em ${onde}: ${l.join(" / ")}`);
  l.forEach(x => {
    if (TECNICO.test(x)) avisos.push(`termo técnico em ${onde}: ${x}`);
    if (/\([^)]*$/.test(x)) avisos.push(`texto cortado em ${onde}: ${x}`);
  });
}
cursos.forEach(c => {
  const onde = `${c.id} ${String(c.titulo || "").slice(0, 40)}`;
  const turmas = c.turmas || [];
  if (turmas.length) turmas.forEach(t => checar(requisitosDe(c, t), onde)); else checar(requisitosDe(c, null), onde);
});
console.log(`Auditoria dos requisitos: ${n} blocos, ${avisos.length} aviso(s).`);
avisos.slice(0, 40).forEach(a => console.log("  AVISO " + a.slice(0, 300)));
