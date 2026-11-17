"""Ordem entre as rotinas e disparo de reserva (corre no início de cada rotina, antes de tudo o resto).

As rotinas (notícias, semanal, site) escrevem na mesma folha e no mesmo repositório, por isso não devem correr ao
mesmo tempo. O GitHub só guarda UMA rotina à espera por fila e cancela a anterior quando chega outra; por isso as
rotinas já não partilham fila e é este script que as põe por ordem:

  python3 vez.py esperar
      espera que acabem as rotinas do projeto que começaram ANTES desta (nunca as que começaram depois, para não
      ficarem à espera umas das outras). Ao fim de 45 minutos segue mesmo assim.

  python3 vez.py ja-correu [schedule,workflow_dispatch]
      disparo de reserva: o GitHub chega a atrasar horas os horários marcados, por isso cada rotina tem um segundo
      horário. Num disparo marcado, se esta rotina já correu com sucesso hoje (UTC) por um dos eventos indicados,
      escreve salta=sim em GITHUB_OUTPUT e a rotina não faz nada. Disparos à mão correm sempre.
"""
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROTINAS = ("noticias.yml", "semanal.yml", "site.yml")
ESPERA_MAXIMA = 45 * 60
INTERVALO = 30


def api(caminho):
    pedido = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/{caminho}",
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return json.load(r)


def corridas(rotina, **filtros):
    q = urllib.parse.urlencode(filtros)
    return api(f"actions/workflows/{rotina}/runs?per_page=30&{q}").get("workflow_runs", [])


def esperar():
    minha = int(os.environ["GITHUB_RUN_ID"])
    inicio = time.time()
    while True:
        antes = []
        try:
            for rotina in ROTINAS:
                # sem filtro de estado na pergunta: o filtro do GitHub atrasa e não vê rotinas que acabaram de começar
                antes += [f"{rotina} #{c['id']}" for c in corridas(rotina)
                          if c["id"] < minha and c.get("status") not in ("completed", None)]
        except Exception as e:  # noqa: BLE001
            print(f"Não foi possível ver as outras rotinas ({type(e).__name__}); segue.")
            return
        if not antes:
            print("Nenhuma rotina anterior a correr: segue.")
            return
        if time.time() - inicio > ESPERA_MAXIMA:
            print(f"Ainda a correr ao fim de {ESPERA_MAXIMA // 60} minutos: {', '.join(antes)}. Segue mesmo assim.")
            return
        print(f"À espera de: {', '.join(sorted(set(antes)))}")
        time.sleep(INTERVALO)


def ja_correu(eventos):
    saida = os.environ.get("GITHUB_OUTPUT")
    if os.environ.get("GITHUB_EVENT_NAME") != "schedule":
        print("Disparo à mão ou por alteração: corre sempre.")
        return
    rotina = os.environ["GITHUB_WORKFLOW_REF"].split("@")[0].rsplit("/", 1)[-1]
    hoje = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    minha = int(os.environ["GITHUB_RUN_ID"])
    try:
        feitas = [c for c in corridas(rotina, status="success", created=f">={hoje}")
                  if c["id"] != minha and c.get("event") in eventos and c.get("created_at", "")[:10] == hoje]
    except Exception as e:  # noqa: BLE001
        print(f"Não foi possível ver as corridas de hoje ({type(e).__name__}); corre por segurança.")
        return
    if feitas:
        print(f"{rotina} já correu hoje com sucesso (#{feitas[0]['id']}, {feitas[0]['event']}): este disparo de reserva não faz nada.")
        if saida:
            with open(saida, "a") as f:
                f.write("salta=sim\n")
    else:
        print(f"{rotina} ainda não correu hoje com sucesso: corre agora.")


if __name__ == "__main__":
    if sys.argv[1:2] == ["esperar"]:
        esperar()
    elif sys.argv[1:2] == ["ja-correu"]:
        ja_correu(set((sys.argv[2] if len(sys.argv) > 2 else "schedule,workflow_dispatch").split(",")))
    else:
        sys.exit(__doc__)
