"""Temporário (27/11/2026): cria o curso geral do SENAI DF – Gratuidade Regimental, Edital 01/2027.
O site do SENAI DF (sistemafibra.org.br) não responde ao GitHub: o edital (PDF) e as páginas foram lidos no Chrome,
com a VPN do Brasil, e as frases conferidas pelo Claude no texto extraído (regra T10)."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config
from cursos import id_curso
from turmas import hoje_ceara

hoje = hoje_ceara()
PAG = "https://www.sistemafibra.org.br/senai/educacao/educacao-profissional/cursos"
LISTA = "https://sistemafibra.org.br/senai/cursos_gratuidade/indexCursos.php"
ED = "https://www.sistemafibra.org.br/senai/editais/gratuidade/edital-01-2027-cursos-de-aperfeicoamento-e-qualificacao-de-gratuidade-regimental/download"
T = "SENAI DF – cursos gratuitos de qualificação e aperfeiçoamento (Gratuidade Regimental, Edital 01/2027)"
ev = [
 f"gratuito: «torna públicas as etapas do processo seletivo para o preenchimento de 6.465 (seis mil quatrocentos e sessenta e cinco) vagas gratuitas» ({ED})",
 f"gratuito: «O Senai-DF oferece, gratuitamente, cursos de formação profissional nas escolas em Brasília (Setor de Indústria Gráficas), Brazlândia, Gama, Taguatinga e Sobradinho.» ({PAG})",
 f"público: «As vagas serão destinadas a pessoas de baixa renda» ({ED})",
 f"data: «As inscrições serão realizadas no período de 17/11/2026 a 15/03/2027, exclusivamente de forma online» ({ED})",
 f"vagas: «seguindo ordem cronológica de manifestação de interesse» ({ED})",
 f"vagas: «na unidade indicada na convocação, por ordem de chegada» ({ED})",
 f"renda: «renda familiar mensal per capita bruta de no máximo 1,5 salários-mínimos federal» ({ED})",
]
base = Base(); carregar_config(base)
ident = id_curso(PAG, T)
if ident in {r.get("ID") for r in base.tabela("Cursos")}:
    print("já existe", ident)
else:
    base.acrescentar("Cursos", [{"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "SENAI Distrito Federal (Gratuidade Regimental)",
        "Link": LISTA, "Página do curso": LISTA, "Destino do link": "lista", "Local": "BR-DF", "Modalidade": "presencial",
        "País": "BR", "Região": "Distrito Federal", "Cidade": "Gama, Brasília (SIG), Taguatinga e Sobradinho",
        "Descrição": ("Cerca de 80 cursos gratuitos para pessoas de baixa renda nas escolas do SENAI no Gama, no SIG, em "
                      "Taguatinga e em Sobradinho, com turmas de janeiro a março de 2027: eletricista, padeiro, confeiteiro, "
                      "soldador, refrigeração, construção, informática, programação, design, costura e outros. Há turmas "
                      "presenciais, semipresenciais e a distância. São 6.465 vagas."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao, emprego", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": ("Renda familiar de até 1,5 salário mínimo por pessoa (autodeclaração)\n"
                       "Idade e escolaridade mínimas variam por curso (Anexo III do edital)"),
        "Renda máxima": "1,5 salário mínimo por pessoa", "Certificado": "desconhecido", "Inscrições até": "2027-03-15",
        "Início": "", "Duração": "de 8 a 460 horas, conforme o curso", "Link verificado": "SIM", "Primeiro visto": hoje,
        "Última verificação": hoje, "Origem": "edital", "Precisa de internet": "Sim",
        "Notas": f"{hoje}: criado à mão pelo Claude (Edital 01/2027 do SENAI DF; site lido no Chrome, regra T10).",
        "Como me inscrever": ("1. Até 15/03/2027, faça o cadastro de interesse online na página de inscrições do SENAI DF "
                              "(escolha a escola e o curso; tenha os documentos já digitalizados).\n2. Espere a convocação "
                              "por e-mail, telefone ou WhatsApp.\n3. Vá à escola indicada na convocação com identidade, CPF, "
                              "comprovante de residência, comprovante de escolaridade e a autodeclaração de baixa renda "
                              "(Anexo IV do edital): a matrícula é por ordem de chegada, enquanto houver vaga."),
        "Nota da verificação": f"{hoje}: edital e páginas lidos no navegador; frases conferidas no texto extraído.",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, data, vagas, renda", "Mudança a rever": "FALSE",
        "O que falta confirmar": ("A inscrição é um cadastro de interesse: o edital não diz por que ordem são feitas as "
                                  "primeiras convocações; a matrícula é por ordem de chegada. Empregados do Sistema Fibra não "
                                  "podem concorrer.")}])
    base.guardar()
    print("+", ident)
