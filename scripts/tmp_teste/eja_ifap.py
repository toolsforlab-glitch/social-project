"""Temporário (25/11/2026): cria os 9 cursos do PS Proeja 2027.1 do Ifap a partir do edital oficial. Apagar depois."""
import os, re, subprocess, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from base import VERIFICACAO_INICIAL, DESCRICAO_RESUMO, Base, carregar_config, citacao_valida, hoje_iso
from cursos import id_curso

EDITAL = "https://www.ifap.edu.br/documents/1317/Edital_PROEJA_2027.pdf"
INSCRICAO = "https://processoseletivo.ifap.edu.br/ps/"
req = urllib.request.Request(EDITAL, headers={"User-Agent": "Mozilla/5.0"})
open("/tmp/ifap.pdf", "wb").write(urllib.request.urlopen(req, timeout=60).read())
texto = subprocess.run(["pdftotext", "-layout", "/tmp/ifap.pdf", "-"], capture_output=True, text=True).stdout
FRASES = {
    "data": "Período de Inscrições 31/10 a 30/11/2026",
    "idade": "Ter idade igual ou superior a 18 anos ATÉ A DATA DA MATRÍCULA",
    "escolaridade": "Ter concluído o Ensino Fundamental, sem dependências, ATÉ A DATA DA MATRÍCULA",
    "requisito": "Não possuir o Ensino Médio",
    "selecao": "O processo seletivo consiste na análise da faixa etária e do tempo de conclusão do ensino funda-",
    "taxa": "Não haverá taxa de inscrição",
    "presencial": "Os cursos são realizados na modalidade presencial",
}
for k, f in FRASES.items():
    assert citacao_valida(f, texto), f"frase não encontrada no edital: {k}"
OFERTAS = [  # (cidade, curso, linha do quadro de vagas)
    ("Laranjal do Jari", "Técnico em Logística", "4 Semestres"),
    ("Macapá", "Técnico em Administração", "5 Semestres"),
    ("Macapá", "Técnico em Meio Ambiente", "6 Semestres"),
    ("Macapá", "Técnico em Informática", "6 Semestres"),
    ("Oiapoque", "Técnico em Guia de Turismo", "6 Semestres"),
    ("Pedra Branca do Amapari", "Técnico em Guia de Turismo", "6 Semestres"),
    ("Porto Grande", "Técnico em Administração", "6 Semestres"),
    ("Porto Grande", "Técnico em Agropecuária", "6 Semestres"),
    ("Santana", "Técnico em serviços Públicos", "6 Semestres"),
]
base = Base()
cfg = carregar_config(base)
assert "ifap.edu.br" in cfg["cursos"].get("dominios_gratuitos", set()), "ifap.edu.br não está marcado «Tudo gratuito»"
existentes = {r.get("ID") for r in base.tabela("Cursos")}
hoje = hoje_iso()
novos = []
for cidade, curso, dur in OFERTAS:
    linha = f"{curso} Noite {dur}"
    assert citacao_valida(linha, texto), f"oferta não encontrada no quadro de vagas: {linha}"
    nome = curso.replace("serviços", "Serviços") + " integrado ao ensino médio (EJA – Proeja)"
    iid = id_curso(EDITAL, f"{nome} {cidade}")
    if iid in existentes:
        print("já existe:", nome, cidade); continue
    semestres = dur.split()[0]
    novos.append({
        "ID": iid, "Estado": "Novo", "Título": nome, "Entidade": "Instituto Federal do Amapá (Ifap)",
        "Link": EDITAL, "Página do curso": EDITAL, "Local": "BR-AP", "Modalidade": "presencial", "País": "BR",
        "Região": "Amapá", "Cidade": cidade,
        "Descrição": (f"Curso técnico junto com o ensino médio, para jovens e adultos que terminaram o ensino fundamental "
                      f"e não têm o ensino médio (Proeja). Aulas à noite, durante {semestres} semestres, no campus do Ifap "
                      f"em {cidade}. Não há prova: a classificação é pela idade e pelo tempo desde o fim do ensino "
                      f"fundamental (mais idade e mais tempo fora da escola dão mais pontos). Começa no 1.º semestre de 2027."),
        "Origem da descrição": DESCRICAO_RESUMO,
        "Necessidades": "escola, profissao, emprego", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Ter 18 anos ou mais até a matrícula; ter concluído o ensino fundamental; não ter o ensino médio.",
        "Certificado": "desconhecido", "Inscrições até": "2026-11-30", "Início": "", "Duração": f"{semestres} semestres",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "edital", "Notas": "",
        "Como me inscrever": ("Inscrição só pela internet, de 31/10 a 30/11/2026, em processoseletivo.ifap.edu.br/ps "
                              "(PS PROEJA 2027.1), entrando com a conta gov.br. Não há taxa. Resultado: 15/12/2026; "
                              "matrícula: 4 a 8/1/2027."),
        "Nota da verificação": f"{hoje}: curso criado a partir do Edital nº 18/2026 – Proen/Ifap (PS Proeja 2027.1); frases conferidas por código no PDF oficial.",
        **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join([
            "gratuito: «entidade marcada como “Tudo gratuito” em Sites de confiança, por uma pessoa»",
            f"data: «{FRASES['data']}» ({EDITAL})",
            f"idade: «{FRASES['idade']}»", f"escolaridade: «{FRASES['escolaridade']}»",
            f"turno: «{linha}»", f"taxa: «{FRASES['taxa']}»", f"seleção: «{FRASES['selecao']}»"]),
        "Campos comprovados": "gratuito, situação, data, idade, escolaridade, turno, internet",
        "Idade mínima": "18", "Escolaridade mínima": "Fundamental completo", "Turno": "Noite",
        "Precisa de internet": "Não", "Antes de começar": "govbr",
    })
base.acrescentar("Cursos", novos)
print(f"{len(novos)} cursos do Ifap criados.")
for n in novos:
    print("  +", n["Título"], "|", n["Cidade"])
