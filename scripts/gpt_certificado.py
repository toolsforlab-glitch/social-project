"""Pergunta ao GPT (22/11/2026), uma por entidade: há uma página OFICIAL que diga, com todas as letras, que o
certificado dos cursos online desta entidade é gratuito (ou pago)?

Só para entidades com muitos cursos sem certificado provado (Sebrae, Fundação Bradesco). O GPT só aponta frases e
links; o código confere que o link é do domínio oficial, que a frase está letra a letra na página e que é o
CERTIFICADO que é gratuito ou pago (certificado_da_frase; «curso gratuito e com certificado» não chega). Nada é
alterado na planilha: o resultado fica no registro da rodada para decidir como aplicar.
"""
import json
import os
import re
import sys

from base import certificado_da_frase, citacao_valida, texto_de_html
from comum import baixar_final, dominio_permitido, extrair_json
from consultar_gpt import gpt, registar_uso

ENTIDADES = [
    {"nome": "Sebrae (cursos online da Loja Sebrae)", "dominio": "sebrae.com.br",
     "exemplo": "https://loja.sebrae.com.br/gest-o-financeira-1-372000026927",
     "contexto": "Os Termos de Uso da Loja (item 7.3) dizem que, depois de concluir o curso online e responder a "
                 "pesquisa de satisfação, o certificado fica disponível na área do cliente, mas não dizem se é gratuito."},
    {"nome": "Fundação Bradesco (Escola Virtual, ev.org.br)", "dominio": "ev.org.br",
     "exemplo": "https://www.ev.org.br/cursos/excel-basico",
     "contexto": "Todos os cursos são gratuitos; falta saber se o certificado também é, dito com todas as letras."},
]
PEDIDO = """Preciso de provas escritas, não de conclusões.
Entidade: {nome}. Exemplo de curso: {exemplo}
{contexto}

Pergunta: existe alguma página OFICIAL desta entidade (domínio {dominio}: página do curso, perguntas frequentes, \
ajuda, termos de uso, regulamento) que diga EXPLICITAMENTE se o CERTIFICADO dos cursos online é gratuito (sem custo) \
ou pago? A frase tem de falar do certificado (não basta dizer que o curso é gratuito).

Não deduza. Não servem notícias, blogs nem sites de terceiros. Copie cada frase EXATA, letra a letra, sem resumir, \
com o link exato da página, diga o valor ("gratuito", "pago" ou "sem certificado") e a que cursos a frase se aplica \
(todos os cursos online da entidade, só alguns, só um). Até 4 frases.

Responda só com JSON entre <json></json>:
[{{"valor": "gratuito|pago|sem certificado", "frase": "…", "url": "…", "aplica_se_a": "…"}}]
Se não encontrar nenhuma, responda <json>[]</json>."""


def main():
    chave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not chave:
        registar_uso(False, "sem chave da OpenAI (segredo OPENAI_API_KEY ou SOCIAL_PROJECT)")
        return
    tokens = {"input_tokens": 0, "output_tokens": 0}
    provadas = 0
    for e in ENTIDADES:
        print(f"\n=== {e['nome']} ===")
        try:
            texto, uso = gpt("gpt-5.5", PEDIDO.format(**e), e["dominio"], chave)
        except Exception as erro:  # noqa: BLE001
            print(f"  ! GPT: {erro}")
            continue
        for k in tokens:
            tokens[k] += int(uso.get(k) or 0)
        respostas = extrair_json(texto)
        if not isinstance(respostas, list) or not respostas:
            print("  O GPT não encontrou frase.", texto[:600] if not isinstance(respostas, list) else "")
            continue
        for r in respostas:
            frase = re.sub(r"\s+", " ", str(r.get("frase") or "")).strip()
            url = str(r.get("url") or "").strip()
            valor = certificado_da_frase(r.get("valor"), frase)
            motivo = ""
            if not frase or not url:
                motivo = "sem frase ou sem link"
            elif not dominio_permitido(url, [e["dominio"]]):
                motivo = "link fora do domínio oficial"
            elif not valor:
                motivo = "a frase não diz que o CERTIFICADO é gratuito, pago ou que não há certificado"
            else:
                try:
                    bruto, final = baixar_final(url, timeout=40)
                    if not dominio_permitido(final, [e["dominio"]]):
                        motivo = "o link redireciona para fora do domínio oficial"
                    elif not citacao_valida(frase, texto_de_html(bruto)):
                        motivo = "a frase não está na página indicada"
                except Exception as erro:  # noqa: BLE001
                    motivo = f"não foi possível abrir o link ({str(erro)[:60]})"
            provadas += not motivo
            print(json.dumps({"valor": r.get("valor"), "frase": frase, "url": url, "aplica_se_a": r.get("aplica_se_a"),
                              "resultado": f"CONFERIDA POR CÓDIGO ({valor})" if not motivo else f"recusada: {motivo}"},
                             ensure_ascii=False, indent=1))
    registar_uso(True, "pergunta única: certificado dos cursos online (Sebrae, Fundação Bradesco)", len(ENTIDADES),
                 provadas, tokens)


if __name__ == "__main__":
    sys.exit(main())
