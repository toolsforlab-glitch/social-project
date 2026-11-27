import re, sys
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
def t(u):
    return re.sub(r"\s+", " ", texto_de_html(baixar(u, timeout=20)))
try:
    a = t("https://www.agenciabrasilia.df.gov.br/w/projeto-jornada-da-mulher-trabalhadora-reabre-inscricoes-para-cursos-de-qualificacao")
    i = a.find("Projeto Jornada da Mulher Trabalhadora reabre"); print("## AGÊNCIA BRASÍLIA\n", a[i:i+4500])
except Exception as e: print("AB FALHA", e)
try:
    g = t("https://portaleduca.educacao.go.gov.br/matricula/matricula-2027-1")
    for p in [r"EJA . Ensino Fundamental", r"Para quem é", r"Cronograma", r"matricula\.go\.gov\.br", r"Educação de Jovens e Adultos"]:
        for m in list(re.finditer(p, g))[:2]: print(f"## GO [{p}] …{g[max(0,m.start()-200):m.end()+400]}")
except Exception as e: print("GO FALHA", e)
for u in ["https://www.ifb.edu.br/estude-no-ifb/noticias/49036-ifb-esta-com-vagas-abertas-para-cursos-2027-1",
          "https://www.ifb.edu.br/brasilia/49096-inscricoes-abertas-para-o-curso-eja-marketing-2027",
          "https://www.ifb.edu.br/samambaia/49122-curso-tecnico-em-edificacoes-eja-ept-2027",
          "https://www.ifb.edu.br/recantodasemas/49052-processo-seletivo-para-ingresso-no-curso-tecnico-em-producao-de-audio-e-video-eja-ept"]:
    try:
        x = t(u)
        for p in [r"todos gratuitos", r"inscri[çc][õo]es", r"idade m[íi]nima", r"conclus[ãa]o do Ensino Fundamental", r"noturno|turno|hor[áa]rio"]:
            for m in list(re.finditer(p, x, re.I))[:2]: print(f"## {u[-60:]} [{p}] …{x[max(0,m.start()-200):m.end()+250]}")
    except Exception as e: print("IFB FALHA", u, e)
