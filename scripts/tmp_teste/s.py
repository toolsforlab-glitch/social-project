import re, html, urllib.request
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
b = get("https://portal.sc.senac.br/cursos/1/psg/abertas/todos-tipos/todas-areas/search")
for m in re.finditer(r"abertas", b):
    print(re.sub(r"\s+", " ", b[max(0, m.start()-400):m.start()+300])); print("--")
c = get("https://portal.sc.senac.br/curso/134819/psg/modelista")
i = c.find("Registrar Interesse"); print(re.sub(r"\s+", " ", c[i-3000:i+1500]))
i = c.find("Curso Gratuito"); print("GRAT", re.sub(r"\s+", " ", c[i-500:i+800]))
