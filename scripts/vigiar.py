"""Vigia páginas oficiais que ainda não têm leitor próprio porque, quando foram vistas, não havia nada aberto.

Para cada página, guarda-se a frase que ela mostra quando está FECHADA. Se a página abrir e a frase sumir, a rotina
abre uma pendência para o responsável (e para o Claude montar o leitor próprio a partir da página aberta).
Não muda cursos nem turmas.
"""
import sys

from base import Base, carregar_config, registar_pendencia
from comum import baixar

VIGIAS = [
    {"nome": "Senac Pernambuco (Programa Senac de Gratuidade)",
     "url": "https://intranet.pe.senac.br/dr/nova/psgnet/",
     "fechado": "não existe processo de inscrição aberto",
     "verificar": "O Senac PE abriu inscrições: peça ao Claude para montar o leitor próprio a partir da página "
                  "(enquanto está aberta). A pendência de 23/11 sobre o Senac PE pode ser fechada depois disso."},
]


def main():
    base = Base()
    carregar_config(base)
    for v in VIGIAS:
        try:
            html = baixar(v["url"], timeout=40).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"{v['nome']}: a página não abriu ({type(e).__name__}); fica para amanhã.")
            continue
        if v["fechado"].lower() in html.lower():
            print(f"{v['nome']}: continua sem inscrições abertas.")
            continue
        print(f"{v['nome']}: a frase de «fechado» sumiu da página.")
        registar_pendencia(base, f"{v['nome']}: a página oficial mudou e já não diz «{v['fechado']}» "
                                 "(provavelmente abriu inscrições).",
                           v["verificar"], v["url"] + "#mudou", origem="vigiar.py")
    base.guardar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
