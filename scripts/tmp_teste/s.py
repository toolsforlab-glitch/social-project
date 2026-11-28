import os, sys, re, html, urllib.request, json
from concurrent.futures import ThreadPoolExecutor
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=60); return r.read().decode("utf-8", "replace")
def tx(b): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", b, flags=re.S))))
faq = tx(get("https://www.sc.senac.br/psg/partials/faq.html")); i = faq.find("Como me inscrevo"); print("FAQ:", faq[i:i+900])
cur = []
for p in range(1, 6):
    b = get(f"https://portal.sc.senac.br/cursos/{p}/psg/abertas/todos-tipos/todas-areas/search")
    cur += re.findall(r'href="(https://portal\.sc\.senac\.br/curso/\d+/psg/[^"]+)"', b)
cur = list(dict.fromkeys(cur)); print("cursos:", len(cur))
def ver(u):
    try:
        b = get(u)
    except Exception as e:
        return u, str(e), []
    i = b.find("Turmas Disponíveis"); seg = b[i:]
    turmas = re.split(r"(?=Turma \d{4}\.\d+\.\d+)", tx(seg))[1:]
    out = []
    for t in turmas:
        t = t[:1500]
        out.append({"cod": t[:20], "gratis": "Curso Gratuito" in t, "preco": bool(re.search(r"R\$", t)), "psg_preco": "Investimento PSG" in t,
                    "matric": "Matrícula Online" in t, "interesse": "Registrar Interesse" in t, "ini": (re.search(r"Início (\d\d/\d\d/\d{4})", t) or [0, ""])[1],
                    "txt": t[:260]})
    links = re.findall(r'href="(https://cloud\.plataforma\.senac\.br/senacmatriculaonline[^"]+)"', b)
    return u, len(links), out
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(ver, cur))
from collections import Counter
c = Counter()
for u, nl, ts in res:
    for t in ts:
        c[(t["gratis"], t["preco"], t["psg_preco"], t["matric"], t["interesse"])] += 1
print("combinações (gratis, preço, psg_preço, matrícula online, registrar interesse):", c)
for u, nl, ts in res[:200]:
    for t in ts:
        if t["gratis"]:
            print("G", u.split("/psg/")[1][:40], "|", t["txt"][:230], "| matric:", t["matric"], "| links:", nl)
json.dump(res, open("../sonda/sc.json", "w"), ensure_ascii=False)
