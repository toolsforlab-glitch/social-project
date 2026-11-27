import sys, urllib.request, urllib.parse, re
sys.path.insert(0, ".")
from comum import baixar, AGENTE
B = "https://www.sp.senai.br"
try:
    h = baixar(f"{B}/cursos/cursos-livres/0?modalidade=3&gratuito=1", timeout=40).decode("utf-8", "replace")
    print("lista ok", len(h), re.findall(r"\d+ a \d+ de \d+", h)[:1], len(re.findall(r"openModalTurmas\(", h)))
    print("pagina 2:", len(baixar(f"{B}/cursos/cursos-livres/1?modalidade=3&gratuito=1", timeout=40)))
    dados = urllib.parse.urlencode({"nomeCurso": "acelerando-a-transicao-para-a-economia-circular", "cursoId": "107971", "escolaId": "150",
                                     "estrategia": "A Distância", "bolsa": "1", "gratuito": "1", "turno": "0", "pos": "0"}).encode()
    req = urllib.request.Request(f"{B}/cursosturmas/", data=dados, headers={"User-Agent": AGENTE, "X-Requested-With": "XMLHttpRequest",
                                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    t = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    print("turmas:", re.sub(r"<[^>]+>", " ", t)[:300])
    print("faq:", "cursos gratuitos online" in baixar(f"{B}/perguntas-frequentes", timeout=40).decode("utf-8", "replace"))
except Exception as e:
    print("ERRO", type(e).__name__, e)
