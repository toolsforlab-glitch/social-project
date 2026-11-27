"""Temporário (27/11/2026): cria o curso do Edital 52/2026 do IFRO Ji-Paraná (Libras Básico I), decisão do responsável:
publicar com aviso sobre o ano 2027 do cronograma. Confere todas as frases no PDF antes de gravar."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida
from cursos import id_curso
from ifro_fic import pdf_do_edital
from turmas import hoje_ceara

P = "https://selecao.ifro.edu.br/extensao-jiparana/2102-edital-n-52-2026-selecao-de-estudantes-curso-de-libras-basico-i-2027-1"
TITULO = "Libras Básico I (Língua Brasileira de Sinais) – IFRO Ji-Paraná"
F = {"gratuito": "A inscrição e o curso são gratuitos.",
     "vagas": "A seleção será por ordem de manifestação de interesse e inscrição efetivada.",
     "data": "Período de Inscrição 30/11/2027 a 11/12/2027",
     "público": "O público-alvo para ambos serão alunos, servidores e comunidade externa.",
     "escolaridade": "O pré-requisito de acesso para o curso é o Ensino Fundamental II completo (9º ano).",
     "horário": "ocorrerão uma vez por semana, às sextas-feiras, das 19h às 22h30, de forma presencial",
     "início": "Início das aulas 05/02/2027",
     "inscrição": "via formulário do Google Forms, no link <https://forms.gle/Q4YsG1ibnapzmktT8>"}
pdf, texto, resultado = pdf_do_edital(P)
falhas = [k for k, f in F.items() if not citacao_valida(f, texto)]
print("PDF:", pdf, "| resultado:", resultado, "| frases que não conferem:", falhas)
if falhas or resultado:
    sys.exit(1)
hoje = hoje_ceara()
base = Base(); carregar_config(base)
ident = id_curso(P, TITULO)
if any(r.get("ID") == ident for r in base.tabela("Cursos")):
    print("já existe", ident); sys.exit(0)
ev = [f"{k}: «{F[k]}» ({pdf})" for k in ("gratuito", "data", "vagas", "público", "escolaridade", "horário", "início")]
ev.append(f"abertura: «{F['data']}» ({pdf})")
base.acrescentar("Cursos", [{
    "ID": ident, "Estado": "Publicado", "Título": TITULO,
    "Entidade": "IFRO – Instituto Federal de Rondônia (Campus Ji-Paraná, Centro de Idiomas)",
    "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-RO", "Modalidade": "presencial",
    "País": "BR", "Região": "Rondônia", "Cidade": "Ji-Paraná",
    "Descrição": ("Curso gratuito de Libras (nível básico I), com 40 horas, no IFRO de Ji-Paraná. São 20 vagas, preenchidas "
                  "por ordem de inscrição. As aulas são às sextas-feiras, das 19h às 22h30, a partir de 5 de fevereiro de 2027."),
    "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
    "Requisitos": F["escolaridade"], "Escolaridade mínima": "Ensino Fundamental completo (9º ano)",
    "Certificado": "desconhecido", "Inscrições até": "2026-12-11", "Inscrições abrem em": "2026-11-30",
    "Início": "2027-02-05", "Duração": "40 horas", "Link verificado": "SIM", "Primeiro visto": hoje,
    "Última verificação": hoje, "Origem": "edital", "Precisa de internet": "Sim",
    "Notas": (f"{hoje}: criado à mão pelo Claude (decisão do responsável: publicar com aviso). O cronograma do edital "
              "escreve 2027 nas datas de inscrição; usadas 30/11 a 11/12/2026."),
    "Como me inscrever": ("1. De 30/11 a 11/12/2026, preencha a ficha de matrícula (Anexo I do edital) e junte num só PDF: "
                          "documento com foto, CPF, comprovante de residência, certidão de nascimento ou casamento, "
                          "comprovante do 9º ano e uma foto 3x4.\n2. Envie tudo pelo formulário do Google Forms "
                          "(https://forms.gle/Q4YsG1ibnapzmktT8).\n3. Acompanhe o resultado na página do edital "
                          "(17/12 preliminar, 21/12 final). A matrícula é feita automaticamente com os documentos enviados."),
    "Nota da verificação": f"{hoje}: edital lido por código; frases conferidas no PDF.",
    **VERIFICACAO_INICIAL, "Situação das inscrições": "Por abrir", "Verificar automaticamente": "FALSE",
    "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, data, vagas, abertura",
    "Mudança a rever": "FALSE",
    "O que falta confirmar": ("O cronograma do edital diz «30/11/2027 a 11/12/2027» para as inscrições, mas as aulas começam "
                              "a 05/02/2027: deve ser erro de digitação (2026). Em caso de dúvida, confirme pelo e-mail "
                              "cfic.jipa@ifro.edu.br ou pelo telefone (69) 2183-6920."),
}])
base.guardar()
print("criado", ident)
