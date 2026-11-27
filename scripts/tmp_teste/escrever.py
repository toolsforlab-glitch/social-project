"""Temporário (27/11/2026): Programa Vencer 2026 (3ª edição), Governo de Rondônia (SEAS). Confere as frases na página e no
edital antes de gravar."""
import io, re, sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from pypdf import PdfReader
from turmas import hoje_ceara

P = "https://rondoniasocial.ro.gov.br/vencer/"
E = "https://rondonia.ro.gov.br/wp-content/uploads/2026/07/SEI_74690921_Edital_6.pdf"
TITULO = "Programa Vencer 2026 (3ª edição) – cursos de qualificação do SENAI e do Senac em Rondônia"
pagina = texto_de_html(baixar(P, timeout=40))
edital = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(baixar(E, timeout=60))).pages)
FP = {"data": "Início (Reabertura) 19/10/2026 Fim (Reabertura) 30/11/2026 Inscrições Abertas!",
      "cidades": "Porto Velho Ariquemes Cujubim Nova União Ji-Paraná Alvorada D'Oeste Guajara Mirim Jaru Cacoal Candeias do Jamari Vilhena Ouro Preto D'Oeste Nova Brasilândia D'Oeste Rolim de Moura São Miguel do Guaporé Costa Marques"}
FE = {"gratuito": "A SEAS ofertará os cursos gratuitamente, nos termos estabelecidos no presente Edital.",
      "vagas": "observada a ordem cronológica e de prioridade",
      "cadunico": "estar cadastrado(a) no Cadastro Único do Governo Federal - CadÚnico, com status ativo e não cancelado, tendo sua última atualização cadastral ocorrida há, no máximo, 24 (vinte e quatro) meses",
      "idade": "ter 16 (dezesseis) anos de idade ou mais no momento do cadastro para cursos de qualificação profissional",
      "residir": "residir no estado de Rondônia",
      "escolaridade": "Ser alfabetizado, possuir capacidade de leitura e compreensão do material didático",
      "auxílio": "O valor total do auxílio financeiro temporário será concedido no montante de R$ 2.400,00 (dois mil e quatrocentos reais)",
      "prioridade": "fica assegurada a priorização de até 40% (quarenta por cento) das vagas ofertadas às pessoas em situação de hipossuficiência e de até 40% (quarenta por cento) aos grupos vulneráveis",
      "presencial": "Os cursos de qualificação e capacitação profissional serão ofertados exclusivamente na modalidade presencial."}
falhas = [k for k, f in FP.items() if not citacao_valida(f, pagina)] + [k for k, f in FE.items() if not citacao_valida(f, edital)]
print("frases que não conferem:", falhas)
if falhas:
    sys.exit(1)
hoje = hoje_ceara()
base = Base(); carregar_config(base)
ident = id_curso(P, TITULO)
if any(r.get("ID") == ident for r in base.tabela("Cursos")):
    print("já existe", ident); sys.exit(0)
ev = [f"data: «{FP['data']}» ({P})", f"gratuito: «{FE['gratuito']}» ({E})", f"vagas: «{FE['vagas']}» ({E})",
      f"público: «{FE['cadunico']}» ({E})", f"idade: «{FE['idade']}» ({E})", f"escolaridade: «{FE['escolaridade']}» ({E})",
      f"ajuda: «{FE['auxílio']}» ({E})", f"prioridade: «{FE['prioridade']}» ({E})", f"modalidade: «{FE['presencial']}» ({E})"]
base.acrescentar("Cursos", [{
    "ID": ident, "Estado": "Publicado", "Título": TITULO,
    "Entidade": "Governo de Rondônia – SEAS (Programa Vencer), com o SENAI e o Senac",
    "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-RO", "Modalidade": "presencial",
    "País": "BR", "Região": "Rondônia", "Cidade": "",
    "Descrição": ("Cursos presenciais e gratuitos de qualificação profissional para quem está no CadÚnico, dados pelo SENAI "
                  "e pelo Senac em 16 cidades de Rondônia (entre elas Porto Velho, Ariquemes, Ji-Paraná, Cacoal e Vilhena). "
                  "Áreas: automotiva, construção civil, vestuário, energia, refrigeração, moda, beleza, gestão, gastronomia, "
                  "eventos e alimentos. Quem se matricula recebe um auxílio de R$ 2.400 em 12 parcelas e, ao concluir, um kit "
                  "profissional."),
    "Origem da descrição": "Resumo", "Necessidades": "profissao, emprego, renda", "Perfis": "todos",
    "Condição de acesso": "Estar no CadÚnico (cadastro atualizado nos últimos 24 meses) e morar em Rondônia",
    "Requisitos": "\n".join([FE["cadunico"], FE["idade"], FE["residir"], FE["escolaridade"]]),
    "Escolaridade mínima": "", "Idade mínima": "16", "Prioridade CadÚnico": "Sim",
    "Ajuda de custo ou transporte": FE["auxílio"] + ", em 12 parcelas de R$ 200,00.",
    "Certificado": "desconhecido", "Inscrições até": "2026-11-30", "Início": "", "Duração": "160 a 240 horas",
    "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "edital", "Precisa de internet": "Sim",
    "Notas": f"{hoje}: criado à mão pelo Claude a partir da página do Programa Vencer e do Edital nº 6/2026/SEAS-CODS (pista da auditoria do ChatGPT, conferida por código).",
    "Como me inscrever": ("1. Até 30/11/2026, entre na plataforma do Programa Vencer (rondoniasocial.ro.gov.br/vencer) com a sua "
                          "conta gov.br e faça o cadastro: NIS, CPF, identidade, comprovante de residência, folha do CadÚnico "
                          "(V7), dados bancários e dois telefones.\n2. Escolha a sua cidade e faça a pré-inscrição no curso.\n"
                          "3. As vagas são preenchidas por ordem de inscrição, com prioridade para quem tem menos renda e para "
                          "grupos vulneráveis. Depois, faça a matrícula no SENAI ou no Senac. Dúvidas: WhatsApp (69) 9 9966-3286."),
    "Nota da verificação": f"{hoje}: página e edital lidos por código; frases conferidas.",
    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "TRUE",
    "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, data, vagas, idade", "Mudança a rever": "FALSE",
    "O que falta confirmar": ("A lista de cursos e turmas de cada cidade só aparece depois de entrar com a conta gov.br; "
                              "a página pública não mostra quantas vagas ainda há."),
}])
base.guardar()
print("criado", ident)
