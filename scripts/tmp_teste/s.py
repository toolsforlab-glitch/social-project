import sys, re
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
def frases(t, rx, n=12):
    out=[]
    for f in re.split(r"(?<=[.;!?])\s+", t):
        if re.search(rx, f, re.I): out.append(f.strip()[:400])
    return out[:n]
alvos = [
 ("RO-pagina", "https://portal.fiero.org.br/senai/paginas/aprendizagem-b%EF%BF%BDsica-e-tcnica/101", r"gratuit|inscri|ordem|idade|anos|comunidade|edital"),
 ("RO-edital43", "https://portal.fiero.org.br/files/arquivos/SENAI/SENAI%20GRATUIDADE%202027.1/EDITAIS/Edital%20dos%20Cursos%20de%20Aprendizagem%20Industrial%20T%C3%A9cnica%20n%C2%BA%2043.2027.1.pdf", r"gratuit|inscri[çc][õo]es|ordem|idade|anos|comunidade|prova|sele[çc][ãa]o|período|munic"),
 ("AM-388", "https://portalsenac.am.senac.br/portal_senac/web/uploads/psg/publicacoes/n-388-2026-senac-manaus-centro-cth-inscricoes-abertas-42320fca8957.pdf", r"inscri|per[íi]odo|gratuit|prova|avalia|idade|experi"),
]
for nome,u,rx in alvos:
    try:
        b=baixar(u,timeout=60); t=texto_de_html(b)
        print("#####",nome,len(b)); [print("  >",f) for f in frases(t,rx,25)]
        if nome=="RO-pagina":
            print("LINKS:", sorted(set(re.findall(r'href="([^"]*(?:EDITAIS|edital|Edital)[^"]*)"', b.decode('utf-8','replace'))))[:40])
    except Exception as e: print("ERRO",nome,type(e).__name__,str(e)[:150])
