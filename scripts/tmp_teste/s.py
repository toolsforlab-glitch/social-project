import sys, re
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
B="https://portal.fiero.org.br/files/arquivos/SENAI/SENAI%20GRATUIDADE%202027.1/EDITAIS/"
alvos = [("pagina","https://portal.fiero.org.br/senai/paginas/aprendizagem-b%EF%BF%BDsica-e-tcnica/101"),
 ("ed42",B+"Edital%20dos%20Cursos%20de%20Aprendizagem%20Industrial%20B%C3%A1sica%20n%C2%BA%2042.2027.1.pdf"),
 ("ed43",B+"Edital%20dos%20Cursos%20de%20Aprendizagem%20Industrial%20T%C3%A9cnica%20n%C2%BA%2043.2027.1.pdf")]
for n,u in alvos:
    t=texto_de_html(baixar(u,timeout=60))
    print("#####",n,len(t))
    for m in re.finditer(r"[^.;]{0,220}(?:\d{2}/\d{2}/\d{4}|\d{2} a \d{2}/\d{2}/\d{4})[^.;]{0,160}", t):
        s=m.group(0).strip()
        if re.search(r"inscri|cronograma|matr[íi]cula|resultado|in[íi]cio", s, re.I): print("  >", s[:380])
    if n!="pagina":
        i=t.find("8. ") ; j=t.find("VAGAS")
        for kw in ["Porto Velho","Ariquemes","Ji-Paraná","Vilhena","Cacoal","Jaru","Rolim"]:
            print("   cidade", kw, t.count(kw))
        k=t.find("QUADRO"); print("   QUADRO:", t[k:k+900] if k>=0 else "-")
