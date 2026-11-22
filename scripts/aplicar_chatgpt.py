"""Aplica a resposta do ChatGPT (assinatura do responsável) ao texto de auditoria preparado por consultar_gpt.py.

A resposta, colada pelo responsável, fica em estado/resposta_chatgpt.txt; a que cursos corresponde cada número está em
estado/auditoria_chatgpt.json. O código prova cada frase como sempre (domínio oficial, frase letra a letra na página,
a frase diz o que se afirma) e só grava o que passa, com a marca "encontrada pelo ChatGPT, conferida por código".
"""
import os
import sys

os.environ["GPT_MODO"] = "resposta"

from consultar_gpt import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
