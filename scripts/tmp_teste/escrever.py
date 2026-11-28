"""Temporário (28/11/2026): passagem por São Paulo — EJA da rede municipal de SP, Fundação Paulistana (pré-inscrição
contínua) e Caminho da Capacitação (Fundo Social de SP, 34.º ciclo). Frases vistas no navegador pelo Claude a 27/11
(Brasília); conferidas aqui por código quando a página abre a partir do GitHub."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara
hoje = hoje_ceara()
base = Base(); carregar_config(base)
ids = {r.get("ID") for r in base.tabela("Cursos")}


def conferir(url, frases):
    try:
        t = texto_de_html(baixar(url, timeout=40).decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        print("não abriu:", url, repr(e)[:120]); return f"vista no navegador a {hoje}; a página não abriu a partir do GitHub"
    falta = [k for k, v in frases.items() if not citacao_valida(v, t)]
    print(url, "falta:", falta)
    return f"conferida por código a {hoje}" if not falta else f"vista no navegador a {hoje} (por código faltou: {', '.join(falta)})"


novos = []
# 1) EJA municipal de São Paulo
EJA = "https://prefeitura.sp.gov.br/w/educa%C3%A7%C3%A3o-de-jovens-e-adultos-matr%C3%ADculas-abertas-o-ano-todo"
F1 = {"data": "A Prefeitura de São Paulo mantém abertas durante todo o ano as matrículas para a Educação de Jovens e Adultos (EJA)",
      "gratuito": "modalidade gratuita destinada a pessoas com 15 anos ou mais que não tiveram acesso ou não concluíram o Ensino Fundamental (1º ao 9º ano)",
      "como": "Pela internet, o interessado pode fazer a inscrição por meio do sistema EOL Cidadão. Também é possível procurar diretamente uma escola municipal que ofereça EJA ou um CIEJA.",
      "documentos": "comprovante de escolaridade (histórico escolar ou declaração de transferência)"}
T1 = "Matrícula na EJA da rede municipal de São Paulo (ensino fundamental)"
i1 = id_curso(EJA, T1)
if i1 not in ids:
    v = conferir(EJA, F1)
    novos.append({"ID": i1, "Estado": "Publicado", "Título": T1, "Entidade": "Prefeitura de São Paulo – Secretaria Municipal de Educação",
        "Link": EJA, "Página do curso": EJA, "Destino do link": "curso", "Local": "BR-SP", "Modalidade": "presencial", "País": "BR",
        "Região": "São Paulo", "Cidade": "São Paulo",
        "Descrição": ("Para quem tem 15 anos ou mais e não terminou o ensino fundamental (1.º ao 9.º ano): a escola municipal de São Paulo "
                      "aceita matrículas na EJA durante todo o ano, de graça. Há EJA à noite nas escolas municipais, turmas de manhã, "
                      "tarde e noite nos CIEJA, a EJA Modular e o MOVA-SP para quem vai aprender a ler e escrever."),
        "Origem da descrição": "Resumo", "Necessidades": "escola", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Ter 15 anos ou mais e não ter concluído o ensino fundamental", "Idade mínima": 15,
        "Certificado": "desconhecido", "Inscrições até": "", "Início": "", "Duração": "",
        "Documentos pedidos": "RG, comprovante de endereço e comprovante de escolaridade (original e cópia); quem não tem comprovante pode pedir uma avaliação de classificação",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Não",
        "Notas": f"{hoje}: criado à mão pelo Claude (passagem por São Paulo). Notícia oficial de 16/07/2026: matrícula durante todo o ano.",
        "Como me inscrever": ("1. Peça a matrícula pela internet no sistema EOL Cidadão, ou vá direto a uma escola municipal que tenha EJA ou a um CIEJA.\n"
                              "2. Leve RG, comprovante de endereço e comprovante de escolaridade (original e cópia).\n"
                              "3. Para saber qual é a escola mais perto, ligue 156 ou use o SP156."),
        "Nota da verificação": f"{hoje}: notícia oficial da Prefeitura ({v}).", **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(f"{k}: «{x}» ({EJA}; {v})" for k, x in F1.items())[:1800],
        "Campos comprovados": "data, gratuito, idade", "Mudança a rever": "FALSE",
        "O que falta confirmar": "O ensino médio para adultos é da rede estadual (não entra neste cartão)."})

# 2) Fundação Paulistana: pré-inscrição contínua
FP = "https://prefeitura.sp.gov.br/web/fundacao_paulistana/w/funda%C3%A7%C3%A3o-paulistana-oferece-oportunidade-de-qualifica%C3%A7%C3%A3o-profissional-com-certifica%C3%A7%C3%A3o"
F2 = {"gratuito": "Os cursos são 100% gratuitos, possuem certificação e são ministrados em locais acessíveis em todas as regiões da cidade",
      "data": "oferecemos uma variedade de cursos de qualificação com inscrições permanentes",
      "requisitos": "Podem se inscrever cidadãos que residam no município de São Paulo e tenham a partir de 16 anos.",
      "como": "APENAS A PRÉ-INSCRIÇÃO NÃO GARANTE A PARTICIPAÇÃO NO CURSO"}
T2 = "Cursos de qualificação gratuitos da Fundação Paulistana (Prefeitura de São Paulo), com pré-inscrição contínua"
i2 = id_curso(FP, T2)
if i2 not in ids:
    v = conferir(FP, F2)
    novos.append({"ID": i2, "Estado": "Publicado", "Título": T2, "Entidade": "Fundação Paulistana de Educação, Tecnologia e Cultura (Prefeitura de São Paulo)",
        "Link": FP, "Página do curso": FP, "Destino do link": "lista", "Local": "BR-SP", "Modalidade": "presencial", "País": "BR",
        "Região": "São Paulo", "Cidade": "São Paulo (regiões Leste, Norte, Sul, Oeste e Centro)",
        "Descrição": ("Cursos de qualificação gratuitos e com certificado da Prefeitura de São Paulo, em todas as regiões da cidade: "
                      "cuidador de idosos, assistente administrativo, confeitaria, tortas e salgados, manicure, maquiagem, costura, "
                      "manutenção de computadores e celulares, logística, porteiro, programação (Java, .NET, PHP, React) e outros. "
                      "A pré-inscrição está sempre aberta; quando a turma abre, a pessoa recebe um e-mail para fazer a matrícula."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Morar na cidade de São Paulo; ter 16 anos ou mais", "Idade mínima": 16,
        "Certificado": "gratuito", "Inscrições até": "", "Início": "", "Duração": "",
        "Turmas abertas (cartão geral)": 24, "Turmas contadas em": hoje, "O que se contou": "cursos (com pré-inscrição)",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
        "Notas": f"{hoje}: criado à mão pelo Claude (passagem por São Paulo). 24 cursos diferentes na lista por região.",
        "Como me inscrever": ("1. Na página da Fundação Paulistana, escolha a região da cidade e clique em «CLIQUE AQUI E FAÇA SUA PRÉ-INSCRIÇÃO» do curso.\n"
                              "2. Preencha a pré-inscrição. Ela não garante a vaga.\n"
                              "3. Quando a turma abrir, chega um e-mail com um link: preencha os dados o quanto antes, porque as vagas são limitadas."),
        "Nota da verificação": f"{hoje}: página oficial da Fundação Paulistana ({v}).", **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(f"{k}: «{x}» ({FP}; {v})" for k, x in F2.items())[:1800],
        "Campos comprovados": "gratuito, certificado, data, requisitos, idade", "Mudança a rever": "FALSE",
        "O que falta confirmar": "A página não diz como as vagas são preenchidas nem quando abrem as turmas de cada curso."})

# 3) Caminho da Capacitação, 34.º ciclo (Grande SP, a partir de 07/12/2026)
CC = "https://www.caminhodacapacitacao.sp.gov.br/"
F3 = {"gratuito": "Por meio de cursos gratuitos, o programa transforma carretas totalmente equipadas em verdadeiras salas de aula sobre rodas",
      "data": "34º Ciclo - 07/12/2026",
      "público": "O programa atende prioritariamente pessoas em situação de vulnerabilidade social, como desempregados, beneficiários de programas sociais e mulheres responsáveis pelo sustento da família.",
      "idade": "Os cursos estão disponíveis para jovens a partir de 14 anos, conforme a modalidade.",
      "certificado": "Cada formação garante aprendizado de excelência e certificado oficial de conclusão."}
T3 = "Caminho da Capacitação (Fundo Social de São Paulo): cursos gratuitos em carretas na Grande São Paulo, 34.º ciclo a partir de 7/12"
i3 = id_curso(CC, T3)
if i3 not in ids:
    v = conferir(CC, F3)
    novos.append({"ID": i3, "Estado": "Publicado", "Título": T3, "Entidade": "Fundo Social de São Paulo (Governo do Estado), programa Caminho da Capacitação",
        "Link": "https://www.cursofussp.sp.gov.br/", "Página do curso": CC, "Destino do link": "lista", "Local": "BR-SP", "Modalidade": "presencial", "País": "BR",
        "Região": "São Paulo", "Cidade": "Grande São Paulo",
        "Descrição": ("Cursos curtos e gratuitos, com aulas teóricas e práticas em carretas equipadas, nas áreas de gastronomia, beleza, moda, "
                      "tecnologia e indústria, com certificado. O 34.º ciclo, na Grande São Paulo, começa a 7 de dezembro de 2026. "
                      "Dá prioridade a pessoas em situação de vulnerabilidade (desempregados, quem recebe programas sociais, mulheres que sustentam a família)."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "A partir de 14 anos, conforme o curso; prioridade para pessoas em situação de vulnerabilidade social", "Idade mínima": 14,
        "Certificado": "desconhecido", "Inscrições até": "2026-12-06", "Início": "2026-12-07", "Duração": "",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
        "Notas": f"{hoje}: criado à mão pelo Claude (passagem por São Paulo). Prazo = véspera do início do 34.º ciclo (a página não diz até quando há inscrição).",
        "Como me inscrever": ("1. Entre no site de inscrições do Fundo Social de São Paulo com o CPF e a data de nascimento.\n"
                              "2. Veja os cursos do 34.º ciclo disponíveis no seu município e inscreva-se.\n"
                              "3. A equipe do Fundo Social liga para confirmar a matrícula: deixe um telefone em que atenda."),
        "Nota da verificação": f"{hoje}: página oficial do programa ({v}).", **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(f"{k}: «{x}» ({CC}; {v})" for k, x in F3.items())[:1800],
        "Campos comprovados": "gratuito, data, público, idade", "Mudança a rever": "FALSE",
        "O que falta confirmar": ("Os municípios e os cursos do 34.º ciclo só aparecem depois de entrar com o CPF no site de inscrições. "
                                  "As vagas dão prioridade a pessoas em situação de vulnerabilidade.")})
if novos:
    base.acrescentar("Cursos", novos); base.guardar()
for n in novos: print("+", n["ID"], n["Título"])
