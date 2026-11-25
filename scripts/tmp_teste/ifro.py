import re, sys, html, glob
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
for f in glob.glob("sonda/*.html"):
    t = open(f, encoding="utf-8", errors="replace").read()
    pdfs = sorted(set(re.findall(r'href="([^"]+\.pdf)"', t)))
    print("=====", f[-60:], pdfs)
    for p in pdfs[:1]:
        u = p if p.startswith("http") else "https://selecao.ifro.edu.br" + p
        try:
            x = texto_de_html(baixar(u.replace(" ", "%20"), 60))
            for k in ["gratuit", "inscriç", "sorteio", "ordem", "prova", "requisit", "idade", "escolaridade", "período", "vagas"]:
                for m in list(re.finditer(k, x, re.I))[:2]:
                    print("  ", k, "::", x[max(0, m.start()-150):m.start()+220])
        except Exception as e: print("ERRO", u, e)
