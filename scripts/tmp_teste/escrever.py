"""Temporário (27/11/2026): Senac SP, cartão geral das bolsas integrais do PSG (decisão do responsável, 27/11).
O site recusa o GitHub (403): frases vistas no navegador pelo Claude a 27/11/2026."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config
from cursos import id_curso
from turmas import hoje_ceara
hoje = hoje_ceara()
P = "https://www.sp.senac.br/bolsas-de-estudo"
BUSCA = "https://www.sp.senac.br/bolsas-de-estudo/cursos-com-bolsa"
V = f"vista no navegador a {hoje}; o site recusa o GitHub"
F = {"gratuito": "Sem taxas de matrícula e gratuitos para quem tem renda familiar mensal de até 2 salários mínimos federais",
     "vagas": "São preenchidas por ordem de inscrição, sem provas e taxas",
     "data": "As inscrições abrem 20 dias antes do início do curso, sempre às 12 horas, e as vagas são limitadas.",
     "renda": "Ter renda familiar de até 2 salários mínimos federais por pessoa"}
base = Base(); carregar_config(base)
T = "Cursos gratuitos com bolsa integral do Senac São Paulo (Programa Senac de Gratuidade)"
ident = id_curso(P, T)
if ident not in {r.get("ID") for r in base.tabela("Cursos")}:
    ev = [f"{k}: «{v}» ({P}; {V})" for k, v in F.items()]
    ev.append(f"turmas: leitura da API do próprio site no Chrome a {hoje}: 293 turmas com inscrição de bolsa aberta (5.267 vagas) em 38 cidades e 1.755 a abrir nos próximos 60 dias ({BUSCA})")
    base.acrescentar("Cursos", [{"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Senac São Paulo (Programa Senac de Gratuidade)",
        "Link": BUSCA, "Página do curso": P, "Destino do link": "lista", "Local": "BR-SP", "Modalidade": "presencial", "País": "BR",
        "Região": "São Paulo", "Cidade": "Capital e interior (38 cidades com turmas abertas a 27/11/2026)",
        "Descrição": ("Cursos livres, técnicos e de idiomas do Senac São Paulo, de graça para quem tem renda familiar de até 2 salários "
                      "mínimos por pessoa, com o material incluído. Cada turma abre as inscrições de bolsa 20 dias antes de começar, "
                      "ao meio-dia, e as vagas vão por ordem de inscrição, sem prova."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Renda familiar de até 2 salários mínimos por pessoa; a escolaridade e a idade dependem de cada curso",
        "Renda máxima": "2 salários mínimos por pessoa", "Certificado": "desconhecido", "Inscrições até": "", "Início": "", "Duração": "",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
        "Notas": f"{hoje}: criado à mão pelo Claude (decisão do responsável: cartão geral; as turmas uma a uma ficam para a tarefa do navegador). O site recusa o GitHub.",
        "Como me inscrever": ("1. Crie ou atualize o seu cadastro no site do Senac São Paulo, em nome de quem vai estudar.\n"
                              "2. Na busca de cursos com bolsa, escolha a unidade, o tipo de curso e o período.\n"
                              "3. Na página do curso, veja a data em que abrem as bolsas da turma e, nesse dia, a partir do meio-dia, "
                              "clique em «Inscrever para bolsa de estudo». As vagas vão por ordem de inscrição.\n"
                              "4. Acompanhe o resultado pelo e-mail."),
        "Nota da verificação": f"{hoje}: página oficial e busca de bolsas lidas no navegador pelo Claude (o site recusa o GitHub).",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, vagas, renda", "Mudança a rever": "FALSE",
        "O que falta confirmar": "As turmas uma a uma (datas, cidades, vagas) ainda não estão no site: só no Chrome, pela API do próprio Senac SP."}])
    base.guardar(); print("+", ident)
