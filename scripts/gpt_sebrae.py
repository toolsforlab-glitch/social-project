"""Pergunta única ao GPT (22/11/2026): há alguma página OFICIAL do Sebrae que diga, com todas as letras, que os cursos
online da loja (os que a página chama só de “Curso online”, não os “Ao vivo”) se começam a qualquer momento, sem turma?

Os cursos “Curso autoinstrucional” já estão provados pela própria página (sebrae.py). Os cerca de 400 “Curso online”
são gratuitos, mas a página não diz que são sob demanda. O GPT só aponta frases e links; o código confere que o link é
de sebrae.com.br, que a frase está letra a letra na página e que a frase diz que se começa a qualquer momento / no
próprio ritmo. Nada é alterado na planilha: o resultado fica no registro da rodada para uma pessoa decidir.
"""
import json
import os
import re
import sys

from base import ACAO_SOB_DEMANDA, citacao_valida, texto_de_html
from comum import baixar_final, dominio_permitido, extrair_json
from consultar_gpt import gpt, registar_uso

DOMINIO = "sebrae.com.br"
EXEMPLO = "https://loja.sebrae.com.br/gest-o-financeira-1-372000026927"
PEDIDO = f"""Preciso de provas escritas, não de conclusões.
Na loja do Sebrae (loja.sebrae.com.br) há cursos marcados como “Curso online” (diferentes dos “Ao vivo” e dos “Curso \
autoinstrucional”). Exemplo: {EXEMPLO}

Pergunta: existe alguma página OFICIAL do Sebrae (domínio sebrae.com.br, incluindo loja.sebrae.com.br, perguntas \
frequentes, termos de uso, ajuda, regulamento dos cursos online / EAD) que diga EXPLICITAMENTE que esses cursos \
online podem ser começados a qualquer momento, sem turma ou data de início, ou feitos no ritmo do aluno? Também serve \
uma frase sobre o prazo para concluir depois da inscrição.

Não deduza a partir de não haver datas na página. Não servem notícias, blogs nem sites de terceiros.
Copie cada frase EXATA, letra a letra, sem resumir, com o link exato da página onde está, e diga a que cursos a frase \
se aplica (todos os cursos online da loja, só um curso, só cursos via WhatsApp, etc.). Até 5 frases.

Responda só com JSON entre <json></json>:
[{{"frase": "…", "url": "…", "aplica_se_a": "…"}}]
Se não encontrar nenhuma, responda <json>[]</json>."""


def main():
    chave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not chave:
        registar_uso(False, "sem chave da OpenAI (segredo OPENAI_API_KEY ou SOCIAL_PROJECT)")
        return
    texto, uso = gpt("gpt-5.5", PEDIDO, DOMINIO, chave)
    respostas = extrair_json(texto) or []
    print(f"O GPT devolveu {len(respostas)} frase(s).")
    provadas = 0
    for r in respostas if isinstance(respostas, list) else []:
        frase = re.sub(r"\s+", " ", str(r.get("frase") or "")).strip()
        url = str(r.get("url") or "").strip()
        motivo = ""
        if not frase or not url:
            motivo = "sem frase ou sem link"
        elif not dominio_permitido(url, [DOMINIO]):
            motivo = "link fora de sebrae.com.br"
        elif not ACAO_SOB_DEMANDA.search(frase) and not re.search(r"prazo|dias para conclu|turma|in[íi]cio", frase, re.I):
            motivo = "a frase não fala em começar a qualquer momento, ritmo, turma ou prazo"
        else:
            try:
                bruto, final = baixar_final(url, timeout=40)
                if not dominio_permitido(final, [DOMINIO]):
                    motivo = "o link redireciona para fora de sebrae.com.br"
                elif not citacao_valida(frase, texto_de_html(bruto)):
                    motivo = "a frase não está na página indicada"
            except Exception as e:  # noqa: BLE001
                motivo = f"não foi possível abrir o link ({str(e)[:60]})"
        provadas += not motivo
        print(json.dumps({"frase": frase, "url": url, "aplica_se_a": r.get("aplica_se_a"),
                          "resultado": "CONFERIDA POR CÓDIGO" if not motivo else f"recusada: {motivo}"},
                         ensure_ascii=False, indent=1))
    if not respostas:
        print("Resposta do GPT (sem JSON):", texto[:1500])
    registar_uso(True, "pergunta única: regra dos cursos online do Sebrae", 1, provadas, uso)


if __name__ == "__main__":
    sys.exit(main())
