import json, glob, re
from base import citacao_valida
from turmas import chave
f = glob.glob("/tmp/diag/*.json")[0]
d = json.load(open(f))
texto, resp = d["texto"], d["resposta"]
i = texto.find("DOCUMENTO OFICIAL LIGADO")

from comum import extrair_json
res = extrair_json(resp)
falhas = 0
for t in res.get("turmas") or []:
    fr = str(t.get("frase") or "")
    ok = citacao_valida(fr, texto)
    nome = chave(t.get("curso", "")) in chave(fr)
    if not (ok and nome):
        falhas += 1
        if falhas <= 8:
            print("FALHA cv=%s nome=%s | curso=%r | frase=%r" % (ok, nome, t.get("curso"), fr[:300]))
print("falhas", falhas, "de", len(res.get("turmas") or []))
