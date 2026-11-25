"""Aplica a resposta do ChatGPT à rodada «certificado» (chatgpt_certificado.py, modo resposta): a resposta colada pelo responsável
fica em estado/resposta_certificado.txt e o código prova cada frase antes de gravar qualquer coisa."""
import os
import sys

os.environ["GPT_MODO"] = "resposta"

from chatgpt_certificado import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
