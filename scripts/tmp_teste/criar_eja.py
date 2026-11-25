"""Temporário (25/11/2026): cursos de EJA das redes estaduais (PE, AL, CE, RN) a partir das frases oficiais da
rodada 3 do ChatGPT, conferidas de novo por código antes de gravar. Gratuidade: decisão do responsável de 25/11/2026
(EJA da rede pública estadual é gratuita) registada em «Revisto por pessoa». Apagar depois de correr."""
import json, os, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import VERIFICACAO_INICIAL, DESCRICAO_RESUMO, MARCA_CHATGPT, Base, hoje_iso
from chatgpt_eja import provar
from cursos import id_curso
from comum import ler_json

prov = ler_json("estado/chatgpt_eja_resultado.json", {})["estados"]
paginas = {}

def frase(uf, campo):
    p = prov[uf][campo]
    f, url, motivo = provar(p, uf, campo, paginas)
    assert not motivo, f"{uf} {campo}: {motivo}"
    return f, url

def abre(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status == 200
    except Exception as e:  # noqa: BLE001
        print("  não abre:", url, str(e)[:60]); return False

REVISTO = "Decisão do responsável (25/11/2026): EJA da rede pública estadual é gratuita"
hoje = hoje_iso()
cursos = []

def curso(uf, regiao, titulo, entidade, link, pagina, modalidade, descricao, como, evid, comp, requisitos="",
          documentos="", ate=""):
    cursos.append({
        "ID": id_curso(pagina, titulo), "Estado": "Publicado", "Título": titulo, "Entidade": entidade,
        "Link": link, "Página do curso": pagina, "Local": f"BR-{uf}", "Modalidade": modalidade, "País": "BR",
        "Região": regiao, "Cidade": "", "Descrição": descricao, "Origem da descrição": DESCRICAO_RESUMO,
        "Necessidades": "escola", "Perfis": "todos", "Condição de acesso": "", "Requisitos": requisitos,
        "Certificado": "desconhecido", "Inscrições até": ate, "Início": "", "Duração": "", "Link verificado": "SIM",
        "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "chatgpt", "Notas": "",
        "Como me inscrever": como,
        "Nota da verificação": f"{hoje}: criado a partir da rodada 3 do ChatGPT (EJA), frases conferidas por código na página oficial.",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(evid), "Campos comprovados": ", ".join(comp), "Revisto por pessoa": REVISTO,
        "Documentos pedidos": documentos, "Precisa de internet": "Não",
    })

# Pernambuco: cadastro de 25/11 a 25/12/2026 (Matrícula Rápida)
p, up = frase("PE", "periodo"); c, _ = frase("PE", "como"); d, _ = frase("PE", "requisitos")
curso("PE", "Pernambuco", "Matrícula 2027 na EJA da rede estadual de Pernambuco", "Secretaria de Educação de Pernambuco",
      up, up, "presencial",
      "Para jovens e adultos que querem terminar o ensino fundamental ou o ensino médio na escola pública estadual. "
      "O cadastro para 2027 é feito pela internet, no site Matrícula Rápida, de 25 de novembro a 25 de dezembro de 2026. "
      "Depois, a matrícula é confirmada na escola escolhida.",
      "Faça o cadastro no site www.matricularapida.pe.gov.br, até 25 de dezembro de 2026. Depois, leve os documentos à escola escolhida para confirmar a matrícula.",
      [f"data: «{p}» ({up}; {MARCA_CHATGPT})", f"como: «{c}» ({up}; {MARCA_CHATGPT})", f"documentos: «{d}» ({up}; {MARCA_CHATGPT})"],
      ["situação", "data", "documentos"], documentos=d, ate="2026-12-25")
# Alagoas: matrícula na EJA a qualquer tempo, on-line
p, up = frase("AL", "periodo"); c, _ = frase("AL", "como")
link = "https://www.matriculaonline.al.gov.br/" if abre("https://www.matriculaonline.al.gov.br/") else up
curso("AL", "Alagoas", "Matrícula na EJA da rede estadual de Alagoas", "Secretaria de Estado da Educação de Alagoas (Seduc)",
      link, up, "presencial",
      "Para jovens e adultos que querem terminar o ensino fundamental ou o ensino médio na escola pública estadual. "
      "A matrícula na EJA pode ser feita a qualquer momento do ano letivo, pela internet, no site Matrícula Online de Alagoas.",
      "Faça a matrícula pela internet, no site www.matriculaonline.al.gov.br.",
      [f"situação: «{p}» ({up}; {MARCA_CHATGPT})", f"como: «{c}» ({up}; {MARCA_CHATGPT})"], ["situação"])
# Ceará: CEJA, matrícula em qualquer período do ano
p, up = frase("CE", "periodo"); r, ur = frase("CE", "requisitos")
curso("CE", "Ceará", "Matrícula na EJA semipresencial dos CEJA (rede estadual do Ceará)", "Secretaria da Educação do Ceará (Seduc)",
      up, up, "misto",
      "Para jovens e adultos que querem terminar o ensino fundamental ou o ensino médio. Nos CEJA (Centros de Educação de "
      "Jovens e Adultos) da rede estadual, com parte das atividades a distância. A matrícula de alunos novos pode ser feita "
      "em qualquer período do ano.",
      "Procure um CEJA da rede estadual do Ceará (lista na página da Secretaria da Educação) para fazer a matrícula.",
      [f"situação: «{p}» ({up}; {MARCA_CHATGPT})", f"requisitos: «{r}» ({ur}; {MARCA_CHATGPT})"], ["situação"], requisitos=r)
# Rio Grande do Norte: matrícula durante todo o ano letivo (SIGEduc)
p, up = frase("RN", "periodo"); c, uc = frase("RN", "como"); r, ur = frase("RN", "requisitos")
sig = "https://sigeduc.rn.gov.br/sigeduc/public/matricula/home.jsf"
curso("RN", "Rio Grande do Norte", "Matrícula na EJA da rede estadual do Rio Grande do Norte",
      "Secretaria de Estado da Educação do Rio Grande do Norte (SEEC)", sig if abre(sig) else up, up, "presencial",
      "Para jovens e adultos que querem terminar o ensino fundamental ou o ensino médio na escola pública estadual. "
      "A matrícula na EJA pode ser feita durante todo o ano letivo, pelo sistema SIGEduc da Secretaria de Educação.",
      "A matrícula é feita no SIGEduc, o sistema de matrículas da Secretaria de Educação do Rio Grande do Norte.",
      [f"situação: «{p}» ({up}; {MARCA_CHATGPT})", f"como: «{c}» ({uc}; {MARCA_CHATGPT})", f"requisitos: «{r}» ({ur}; {MARCA_CHATGPT})"],
      ["situação"], requisitos=r)

base = Base()
existentes = {x.get("ID") for x in base.tabela("Cursos")}
novos = [c for c in cursos if c["ID"] not in existentes]
base.acrescentar("Cursos", novos)
for c in cursos:
    print(("+ " if c in novos else "= já existia ") + c["Título"], "|", c["Link"])
