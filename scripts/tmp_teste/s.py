import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import senac_rs as m
from comum import baixar
from base import texto_de_html, citacao_valida
p = baixar(m.LISTA, timeout=180).decode("utf-8", "replace")
f = texto_de_html(baixar(m.FAQ, timeout=60))
print("gratuidade:", citacao_valida(m.FRASE_GRATUIDADE, f), "| ordem:", citacao_valida(m.FRASE_ORDEM, f), "| faq len", len(f))
ts = m.ler_turmas(p)
print("turmas com datas:", len(ts))
for t in ts:
    if t["prazo"] >= "2026-01-01":
        print({k: v for k, v in t.items() if k not in ("req_texto", "cron_texto")}, "| cidade:", m.cidade_da_unidade(t["unidade"]), "| idade/esc/doc/renda:", m.idade_escolaridade(t["requisitos"]), "| auditoria:", m.auditar(t))
