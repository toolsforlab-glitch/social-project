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
    # SENAI Bahia (cursos técnicos com bolsa): saiu em 23/11/2026, porque a entrada exige nota do ENEM (regra: cursos
    # com prova ficam fora); o vigia foi retirado.
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
    # Senac Sergipe: o portal do PSG (psg.se.senac.br/cursos) lê a lista pública /api/course/filter; em 23/11/2026 tinha
    # 0 cursos. Conta-se meta.totalItems.
    {"nome": "Senac Sergipe (Programa Senac de Gratuidade)",
     "url": "https://psg.se.senac.br/api/course/filter?page=1&limit=6",
     "contar_json": True, "caminho": ["meta", "totalItems"], "link": "https://psg.se.senac.br/cursos",
     "verificar": "Apareceram cursos no portal do PSG do Senac Sergipe: peça ao Claude para montar o leitor próprio a "
                  "partir da lista pública (psg.se.senac.br/api/course/filter)."},
    # SENAI Rio Grande do Norte: a página «Oportunidades» (vagas gratuitas regimentais) lê esta lista; em 23/11/2026
    # respondia «Nenhuma oportunidade encontrada».
    {"nome": "SENAI Rio Grande do Norte (vagas gratuitas regimentais)",
     "url": "https://www.rn.senai.br/transparencia/includes/api/api-oportunidades.php?acao=resultado&modalidade=&produto=&cidade=&area=&curso=",
     "fechado": "Nenhuma oportunidade encontrada",
     "verificar": "O SENAI RN publicou vagas gratuitas na página «Oportunidades» (www.rn.senai.br/oportunidades/): peça "
                  "ao Claude para montar o leitor próprio enquanto estão abertas."},
    # Senac Rio Grande do Norte: a página do Programa de Bolsas mostra o último edital; em 23/11/2026 só tinha o
    # resultado do edital 006/2026 (fechado). Quando o texto mudar, saiu edital novo.
    {"nome": "Senac Rio Grande do Norte (Programa de Bolsas / PSG)",
     "url": "https://lp.rn.senac.br/programa-de-bolsa",
     "fechado": "RESULTADO EDITAL Nº 006_2026",
     "verificar": "O Senac RN mudou a página do Programa de Bolsas (provavelmente edital novo): peça ao Claude para ler o "
                  "edital e montar o leitor próprio."},
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
                dado = json.loads(html)
                for k in v.get("caminho", []):
                    dado = dado[k]
                n = dado if isinstance(dado, int) else len(dado)
            except (ValueError, KeyError, TypeError):
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
