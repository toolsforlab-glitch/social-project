"""Aplica a resposta do ChatGPT à rodada «eja» (chatgpt_eja.py, modo resposta): a resposta colada pelo responsável
fica em estado/resposta_eja.txt e o código prova cada frase antes de gravar qualquer coisa."""
import os
import sys

os.environ["GPT_MODO"] = "resposta"

from chatgpt_eja import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
