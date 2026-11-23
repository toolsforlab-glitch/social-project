"""Vigia páginas oficiais que ainda não têm leitor próprio porque, quando foram vistas, não havia nada aberto.

Para cada página, guarda-se a frase que ela mostra quando está FECHADA. Se a página abrir e a frase sumir, a rotina
abre uma pendência para o responsável (e para o Claude montar o leitor próprio a partir da página aberta).
Não muda cursos nem turmas.
"""
import json
import sys

from base import Base, carregar_config, registar_pendencia
from comum import baixar

VIGIAS = [
    {"nome": "Senac Pernambuco (Programa Senac de Gratuidade)",
     "url": "https://intranet.pe.senac.br/dr/nova/psgnet/",
     "fechado": "não existe processo de inscrição aberto",
     "verificar": "O Senac PE abriu inscrições: peça ao Claude para montar o leitor próprio a partir da página "
                  "(enquanto está aberta). A pendência de 23/11 sobre o Senac PE pode ser fechada depois disso."},
    # Senac Paraíba: o catálogo de matrículas tem o tipo de formação «Seleção PSG» (código 5); em 23/11/2026 estava
    # vazio. A resposta deste endereço traz também campos internos de pagamento do Senac PB: só se conta o número
    # de turmas, nada mais é lido nem guardado.
    {"nome": "Senac Paraíba (Seleção PSG no catálogo de matrículas)",
     "url": "https://pb.senac.br/matriculas/matricula/cursos-tecnicos/get-turmas.php?json="
            "%7B%22search%22%3A%22%22%2C%22nivel%22%3A%5B%5D%2C%22area%22%3A%22%22%2C%22cidade%22%3A%22%22%2C"
            "%22unidade%22%3A%22%22%2C%22tpFormacao%22%3A%5B%225%22%5D%2C%22turnos%22%3A%5B%5D%2C"
            "%22dataInicial%22%3A%22%22%2C%22dataFinal%22%3A%22%22%7D",
     "contar_json": True, "link": "https://pb.senac.br/matriculas/matricula/cursos-tecnicos/index.php",
     "verificar": "Apareceram turmas «Seleção PSG» (gratuitas) no catálogo do Senac PB: peça ao Claude para montar o "
                  "leitor próprio enquanto estão abertas (filtro «Tipo de formação: Seleção PSG»)."},
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
        if v.get("contar_json"):
            try:
                n = len(json.loads(html))
            except ValueError:
                print(f"{v['nome']}: a resposta não é a lista esperada; fica para amanhã.")
                continue
            if not n:
                print(f"{v['nome']}: continua sem turmas.")
                continue
            print(f"{v['nome']}: {n} turmas.")
            registar_pendencia(base, f"{v['nome']}: apareceram {n} turmas.", v["verificar"], v["link"] + "#psg",
                               origem="vigiar.py")
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
