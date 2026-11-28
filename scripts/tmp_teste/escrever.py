"""Temporário (28/11/2026): Senac RJ — cartão geral do PSG e cartão dos técnicos gratuitos do PROPAG (subsequente).
Os dois sites recusam o GitHub («Solicitação rejeitada»): frases vistas no navegador pelo Claude a 28/11/2026."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config
from cursos import id_curso
from turmas import hoje_ceara
hoje = hoje_ceara()
V = f"vista no navegador a {hoje}; o site recusa o GitHub"
base = Base(); carregar_config(base)
ids = {r.get("ID") for r in base.tabela("Cursos")}
novos = []

# 1) PSG
P = "https://psg.rj.senac.br/Ext/index.html"
L = "https://psg.rj.senac.br/Ext/Vagas.aspx"
F = {"gratuito": "tem o objetivo de conceder qualificação profissional gratuita e de qualidade",
     "renda": "São vários cursos destinados a pessoas de baixa renda (até 02 salários mínimos por pessoa na família)",
     "vagas": "A classificação dos candidatos para ingresso nas turmas se dá por ordem de inscrição do candidato no curso selecionado.",
     "como": "A candidatura para os cursos disponíveis da modalidade Cursos Profissionalizantes poderá ser realizada somente após a criação de Login e Senha neste site."}
T = "Cursos gratuitos do Programa Senac de Gratuidade no Senac Rio de Janeiro"
ident = id_curso(L, T)
if ident not in ids:
    ev = [f"{k}: «{v}» ({L}; {V})" for k, v in F.items()]
    ev.append(f"turmas: leitura do calendário de cada turma no Chrome a {hoje}: 49 cursos, 55 turmas com inscrição aberta (851 vagas PSG) em 11 cidades; os períodos de inscrição vão até 23/01/2027 ({L})")
    novos.append({"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Senac Rio de Janeiro (Programa Senac de Gratuidade)",
        "Link": L, "Página do curso": P, "Destino do link": "lista", "Local": "BR-RJ", "Modalidade": "presencial", "País": "BR",
        "Região": "Rio de Janeiro",
        "Cidade": "Rio de Janeiro (Centro, Bonsucesso, Botafogo, Campo Grande, Copacabana, Irajá, Madureira), Duque de Caxias, Nova Iguaçu, Niterói, Petrópolis, Nova Friburgo, Angra dos Reis, Barra do Piraí, Barra Mansa, Cabo Frio e Itaperuna",
        "Descrição": ("Cursos de qualificação profissional do Senac RJ (administração, logística, beleza, barbeiro, costura, bolos e salgados, "
                      "informática com IA, primeiros socorros, cuidador de idoso, entre outros), de graça para quem tem renda familiar de até "
                      "2 salários mínimos por pessoa. Cada turma tem o seu período de inscrição, e as vagas vão por ordem de inscrição, sem prova."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Renda familiar de até 2 salários mínimos por pessoa; os outros requisitos dependem de cada curso",
        "Renda máxima": "2 salários mínimos por pessoa", "Certificado": "desconhecido", "Inscrições até": "", "Início": "", "Duração": "",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
        "Documentos pedidos": "Documento oficial de identificação e CPF (original e cópia)",
        "Notas": f"{hoje}: criado à mão pelo Claude (cartão geral, como o do Senac SP; as turmas uma a uma ficam para a tarefa do navegador). O site recusa o GitHub.",
        "Como me inscrever": ("1. Na página de cursos do Programa Senac de Gratuidade do Senac RJ, clique em «CADASTRE-SE», digite o CPF em «Não sou cadastrado» e crie o cadastro.\n"
                              "2. Na lista de cursos, escolha a unidade, o curso e o turno e clique em «Inscrição» para ver as datas da turma.\n"
                              "3. Faça a candidatura dentro do período de inscrição da turma. As vagas vão por ordem de inscrição.\n"
                              "4. Veja o resultado na data indicada e siga as datas de matrícula do regulamento, levando documento de identificação e CPF (original e cópia)."),
        "Nota da verificação": f"{hoje}: página oficial e calendário das turmas lidos no navegador pelo Claude (o site recusa o GitHub).",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, vagas, renda", "Mudança a rever": "FALSE",
        "O que falta confirmar": "As turmas uma a uma (datas, cidades, vagas) ainda não estão no site: só no Chrome, no calendário de cada curso."})

# 2) PROPAG (técnico subsequente)
P2 = "https://www.rj.senac.br/curso-tecnico-gratuito"
L2 = "https://www.rj.senac.br/curso-tecnico-gratuito/turmas"
F2 = {"gratuito": "Os cursos são totalmente gratuitos e não têm mensalidade, nas duas modalidades.",
      "vagas": "Não há prova nem sorteio.",
      "data": "Subsequente: as matrículas estão abertas desde 21/10/2026, enquanto houver vagas.",
      "requisitos": "Subsequente: quem já concluiu o Ensino Médio, em escola pública ou particular.",
      "ajuda": "O aluno pode receber a Bolsa Permanência de R$ 400 e o Prêmio de Conclusão de Curso de R$ 1.000, de acordo com as diretrizes do programa EDUTEC.",
      "modalidade": "Todos os cursos são presenciais."}
T2 = "Cursos técnicos gratuitos do Senac RJ com o Governo do Estado (PROPAG), para quem já terminou o ensino médio"
ident2 = id_curso(L2, T2)
if ident2 not in ids:
    ev = [f"{k}: «{v}» ({P2}; {V})" for k, v in F2.items()]
    ev.append(f"turmas: lista de turmas da própria página lida no Chrome a {hoje}: 34 turmas subsequentes, todas com início a 30/11/2026, em 11 unidades ({L2}); prazo = véspera do início (inscrição «enquanto houver vagas»)")
    novos.append({"ID": ident2, "Estado": "Publicado", "Título": T2, "Entidade": "Senac Rio de Janeiro, com o Governo do Estado do Rio de Janeiro (PROPAG)",
        "Link": L2, "Página do curso": P2, "Destino do link": "lista", "Local": "BR-RJ", "Modalidade": "presencial", "País": "BR",
        "Região": "Rio de Janeiro",
        "Cidade": "Rio de Janeiro (Centro, Bonsucesso, Botafogo, Copacabana, Madureira, Marechal Floriano, Santa Luzia), Nova Friburgo, Petrópolis, Itaperuna e Santo Antônio de Pádua",
        "Descrição": ("Cursos técnicos do Senac RJ, de graça, numa parceria com o Governo do Estado: Administração, Desenvolvimento de Sistemas, "
                      "Logística, Multimídia, Estética, Massoterapia, Podologia, Óptica, Prótese Dentária e Guia de Turismo. "
                      "O aluno pode receber uma bolsa permanência de R$ 400 e um prêmio de R$ 1.000 ao concluir. Não há prova nem sorteio: "
                      "a vaga é de quem se matricula primeiro. As turmas começam a 30/11/2026."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Ter concluído o ensino médio (escola pública ou particular)",
        "Escolaridade mínima": "Médio completo", "Certificado": "desconhecido", "Inscrições até": "2026-11-29", "Início": "2026-11-30", "Duração": "",
        "Ajuda de custo ou transporte": "Bolsa Permanência de R$ 400 e Prêmio de Conclusão de R$ 1.000 (diretrizes do programa EDUTEC)",
        "Documentos pedidos": "Documento de identidade e CPF (original e cópia simples) e comprovante de conclusão do ensino médio",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Não",
        "Notas": f"{hoje}: criado à mão pelo Claude. A modalidade concomitante (alunos do ensino médio) fechou a 30/10/2026 e ficou de fora. O site recusa o GitHub.",
        "Como me inscrever": ("1. Na página dos cursos técnicos gratuitos do Senac RJ, veja as turmas abertas e escolha o curso, a unidade e o turno.\n"
                              "2. Faça a inscrição pelo formulário da página (opção «Já concluí o Ensino Médio») ou vá direto à unidade do curso.\n"
                              "3. Conclua a matrícula presencialmente na unidade, com identidade, CPF e comprovante de conclusão do ensino médio. "
                              "A vaga só fica garantida com a matrícula, enquanto houver vagas."),
        "Nota da verificação": f"{hoje}: página oficial e lista de turmas lidas no navegador pelo Claude (o site recusa o GitHub).",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, vagas, inscrições até, requisitos", "Mudança a rever": "FALSE",
        "O que falta confirmar": "A página diz «enquanto houver vagas» e não diz se aceita matrículas depois de as aulas começarem (30/11)."})
if novos:
    base.acrescentar("Cursos", novos); base.guardar()
for n in novos: print("+", n["ID"], n["Título"])
