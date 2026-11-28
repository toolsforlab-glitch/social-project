"""Temporário (28/11/2026): Firjan SENAI (SENAI-RJ), edital de cursos de qualificação profissional gratuitos (11.260 vagas),
como curso geral (M8). Frases do edital em PDF conferidas por código (sonda de 28/11, pdftotext); frase da página conferida aqui."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara
hoje = hoje_ceara()
P = "https://www.firjansenai.com.br/sobre/conheca-a-firjan-senai/editais-gratuitos"
ED = "https://www.firjansenai.com.br/sites/default/files/2026-11/OFERTAS%201%20EDITAL%20QP_Gratuidade_REV.0_atual.%2011.11.2026.pdf.pdf"
FP = "As inscrições para os cursos gratuitos da Firjan SENAI estão abertas!"
FE = {"gratuito": "vagas gratuitas, no âmbito da gratuidade regimental do SENAI-RJ",
      "data": "Inscrições e Matrículas 23/11/2026 até 23/04/2027",
      "vagas": "a ordem de inscrição e a entrega da documentação para a matrícula",
      "renda": "Possuir renda familiar mensal per capita bruta de até 1,5 salário-mínimo federal"}
ok = citacao_valida(FP, texto_de_html(baixar(P, timeout=40)))
print("frase da página:", ok)
if ok:
    base = Base(); carregar_config(base)
    T = "Cursos de qualificação profissional gratuitos da Firjan SENAI (Rio de Janeiro, 11.260 vagas)"
    ident = id_curso(P, T)
    if ident not in {r.get("ID") for r in base.tabela("Cursos")}:
        ev = [f"gratuito (página): «{FP}» ({P}; conferida por código)"] + \
             [f"{k}: «{v}» ({ED}; edital em PDF, conferida por código a {hoje})" for k, v in FE.items()]
        base.acrescentar("Cursos", [{"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Firjan SENAI (SENAI-RJ, Gratuidade Regimental)",
            "Link": P, "Página do curso": ED, "Destino do link": "edital", "Local": "BR-RJ", "Modalidade": "misto", "País": "BR",
            "Região": "Rio de Janeiro",
            "Cidade": ("Rio de Janeiro (Maracanã, Tijuca, Jacarepaguá, Benfica e outras), São Gonçalo, Niterói, Nova Iguaçu, Duque de Caxias, "
                       "Volta Redonda, Barra Mansa, Resende, Campos, Petrópolis, Itaguaí, Três Rios, Itaperuna, Nova Friburgo e outras"),
            "Descrição": ("Cursos de qualificação profissional gratuitos da Firjan SENAI em escolas de todo o estado do Rio de Janeiro, para "
                          "pessoas de baixa renda (até 1,5 salário mínimo por pessoa na família). Há cursos presenciais, semipresenciais e "
                          "on-line ao vivo. As vagas vão por ordem de inscrição, com início das turmas entre janeiro e abril de 2027."),
            "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": "Renda familiar de até 1,5 salário mínimo por pessoa; a idade e a escolaridade dependem de cada curso (estão no edital)",
            "Renda máxima": "1,5 salário mínimo por pessoa", "Certificado": "desconhecido", "Inscrições até": "2027-04-23", "Início": "",
            "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial",
            "Precisa de internet": "Sim",
            "Notas": f"{hoje}: criado à mão pelo Claude (curso geral do edital, regra M8; auditoria 7 do ChatGPT; frases conferidas por código).",
            "Como me inscrever": ("1. Abra o edital na página «Editais gratuitos» da Firjan SENAI e escolha o curso, a escola e o turno.\n"
                                  "2. Cursos presenciais e semipresenciais: inscrição e matrícula presenciais na escola SENAI escolhida, com os "
                                  "documentos do edital e a autodeclaração de baixa renda.\n"
                                  "3. Cursos on-line ao vivo: inscrição no site da Firjan, enviando os documentos pela plataforma.\n"
                                  "4. As vagas vão por ordem de inscrição; a inscrição de cada turma fecha quando enche."),
            "Nota da verificação": f"{hoje}: página e edital em PDF lidos por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, data, vagas, renda", "Mudança a rever": "FALSE",
            "O que falta confirmar": "As turmas uma a uma (escola, datas e vagas) estão só no edital em PDF."}])
        base.guardar(); print("+", ident)
