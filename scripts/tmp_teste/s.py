import re, sys, io, json
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
from pypdf import PdfReader
def ler(u, pdf=False):
    b = baixar(u, timeout=20)
    if b[:4] == b"%PDF":
        return re.sub(r"\s+", " ", "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages))
    return re.sub(r"\s+", " ", texto_de_html(b))
def ver(u, pats, n=260):
    try:
        t = ler(u)
    except Exception as e:
        print(f"\n## {u} FALHA {type(e).__name__} {str(e)[:60]}"); return
    print(f"\n## {u} ({len(t)} chars)")
    for p in pats:
        for m in list(re.finditer(p, t, re.I))[:2]:
            print(f"  [{p[:20]}] …{t[max(0,m.start()-n):m.end()+n]}")
ver("https://portaleduca.educacao.go.gov.br/matricula/matricula-2027-1", [r"09/11/2026", r"EJA", r"conforme as vagas"])
ver("https://sme.goiania.go.gov.br/site/index.php/institucional/ultimas-noticias/3320-prefeitura-de-goiania-divulga-cronograma-de-matriculas-para-o-ano-letivo-de-2027", [r"EJA", r"04/01/2027"])
for u in ["https://www.ifb.edu.br/attachments/article/49096/Edital%2044.2026%20-%20EJA%20EPT%20T%C3%A9cnico%20em%20Marketing.pdf",
          "https://www.ifb.edu.br/attachments/article/49052/EDITAL_45_EJA.pdf"]:
    ver(u, [r"submiss[ãa]o documental", r"classifica[çc][ãa]o", r"sorteio", r"ordem de", r"gratuit", r"inscri[çc][õo]es ser[ãa]o", r"per[íi]odo de inscri"], 300)
try:
    j = json.loads(baixar("https://psg.se.senac.br/api/course/filter?page=1&limit=50", timeout=20))
    print("\n## Senac SE API meta:", j.get("meta"), "| itens:", len(j.get("data") or j.get("items") or []))
    its = j.get("data") or j.get("items") or []
    for x in its[:8]: print("   ", json.dumps(x, ensure_ascii=False)[:400])
except Exception as e:
    print("Senac SE API FALHA", type(e).__name__, e)
ver("https://goias.gov.br/governo-abre-selecao-com-810-vagas-em-cursos-tecnicos-gratuitos-para-2027/", [r"inscri[çc]", r"sele[çc][ãa]o", r"prova|sorteio|an[áa]lise"])
ver("https://www.agenciabrasilia.df.gov.br/w/projeto-jornada-da-mulher-trabalhadora-reabre-inscricoes-para-cursos-de-qualificacao", [r"inscri[çc]", r"gratuit", r"cursos?"])
