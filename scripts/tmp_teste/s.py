import os, sys, re, html, urllib.request
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=60); return r.read().decode("utf-8", "replace"), r.geturl()
def tx(b): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", b, flags=re.S))))
b, f = get("https://portal.sc.senac.br/cursos/1/psg/abertas/todos-tipos/todas-areas/search")
t = tx(b); m = re.search(r"Mostrando .{0,60}registros", t); print("ABERTAS", m.group(0) if m else "?")
cur = sorted(set(re.findall(r'href="(https://portal\.sc\.senac\.br/curso/\d+/psg/[^"]+)"', b)))
print(len(cur), cur[:30])
for u in cur[:3]:
    c, _ = get(u); ct = tx(c)
    i = ct.find("Turma"); print("=====", u, len(ct)); print(ct[ct.find("Senac Santa Catarina --> -->")+0:][:200])
    j = ct.find("Programa Senac de Gratuidade (PSG) Educação"); 
    print(ct[1500:j if j > 0 else 9000][:7000])
    print("LINKS", sorted(set(re.findall(r'href="([^"]*(?:inscri|matric|turma)[^"]*)"', c, re.I)))[:20])
