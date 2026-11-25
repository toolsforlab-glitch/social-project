import sys, re, html, urllib.parse
sys.path.insert(0, "scripts")
from comum import baixar
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
a = t("https://www.ifpb.edu.br/editais")
print("CATEGORIAS h2:", [limpo(x) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", a, re.S)][:40])
i = a.find("Processos Seletivos"); 
for m in re.finditer(r"(?i)(cursos? (fic|de forma[çc][ãa]o inicial)|forma[çc][ãa]o inicial|discentes|estudantes|processos seletivos)", limpo(a)):
    pass
x = limpo(a)
for kw in ["FIC", "Formação Inicial", "Mulheres Mil", "Discente", "Cursos Técnicos", "Seleção de alunos", "Seleção de estudantes"]:
    for m in list(re.finditer(re.escape(kw), x))[:3]: print(kw, "→", x[max(0,m.start()-150):m.end()+250])
for u in ["https://estudante.ifpb.edu.br/", "https://estudante.ifpb.edu.br/processos-seletivos/", "https://estudante.ifpb.edu.br/editais/",
          "https://estudante.ifpb.edu.br/cursos/?modalidade=fic", "https://www.ifpb.edu.br/campus/cabedelo/cursos/formacao-inicial-e-continuada-fic"]:
    try: b = t(u)
    except Exception as e: print("ERRO", u, e); continue
    print("#####", u, len(b))
    ls = [(limpo(x)[:140], urllib.parse.urljoin(u, h)) for h, x in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)]
    ls = [l for l in ls if re.search(r"FIC|Forma[çc][ãa]o Inicial|sele|edital|inscri|processo|Mulheres|EJA|Qualifica", l[0], re.I)]
    for l in ls[:40]: print("  ", l)
    m = re.search(r'(?s)<main.*?</main>', b); print("  TXT:", limpo(m.group(0) if m else b)[:1200])
