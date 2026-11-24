import json, glob, re
from comum import extrair_json
cods_pdf, cods_resp = set(), []
for f in sorted(glob.glob("/tmp/diag/*.json")):
    d = json.load(open(f))
    cods_pdf |= set(re.findall(r"\b[A-Z]{2,4}\.[A-Z0-9]{2,4}\.\d{2,4}\b", d["texto"]))
    cods_resp += [t.get("codigo") for t in (extrair_json(d["resposta"]) or {}).get("turmas") or []]
print("codigos no PDF:", len(cods_pdf), "| propostos (distintos):", len(set(cods_resp)), "| em falta:", sorted(cods_pdf - set(cods_resp))[:20])
