import re, sys, os
sys.path.insert(0, "scripts")
from comum import baixar
os.makedirs("sonda", exist_ok=True)
raw = baixar("https://www.to.senac.br/cursos/abertos", 60).decode("utf-8", "replace")
principal = sorted(set(re.findall(r'/_nuxt/[A-Za-z0-9_\-]+\.js', raw)))
vistos = set()
fila = list(principal)
while fila and len(vistos) < 120:
    j = fila.pop(0)
    if j in vistos: continue
    vistos.add(j)
    try:
        t = baixar("https://www.to.senac.br" + j, 60).decode("utf-8", "replace")
    except Exception as e:
        continue
    for n in re.findall(r'["\'`]\./([A-Za-z0-9_\-]+\.js)["\'`]', t):
        fila.append("/_nuxt/" + n)
    achados = set(re.findall(r'(?:get|post)\(\s*[`"\'](/[^`"\']+)[`"\']', t))
    if achados: print(j, sorted(achados))
print("chunks:", len(vistos))
