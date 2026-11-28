import os, sys, re, html, urllib.request
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=60); return r.read().decode("utf-8", "replace"), r.geturl()
def tx(b): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", b, flags=re.S))))
b, f = get("https://portal.sc.senac.br/cursos/1/todas-unidades/psg/todas-modalidades/todos-tipos/todas-areas/search")
print("LISTA", f, len(b))
t = tx(b); i = t.find("Cursos"); print(t[:200]); 
links = sorted(set(re.findall(r'href="([^"]*curso[^"]*)"', b)))
print(len(links), links[:60])
print(re.findall(r'(?:pagina|page)[^"]{0,40}', b)[:20])
m = re.search(r"(\d+)\s+(?:cursos?|resultados?)\s+encontrad", t, re.I); print("total", m.group(0) if m else "")
i = t.find("PSG"); print(t[i-1500:i+3000])
for p in ["faq.html", "programa.html", "inscricao.html"]:
    try:
        x, _ = get("https://www.sc.senac.br/psg/partials/" + p); print("==", p, tx(x)[:2500])
    except Exception as e: print("==", p, e)
