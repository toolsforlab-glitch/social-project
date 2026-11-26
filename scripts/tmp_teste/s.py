import sys, re
sys.path.insert(0, ".")
import noticias_oficiais as n
for f in n.FONTES[-3:]:
    try:
        a = n.noticias_da_api(f, "2026-11-26") if f.get("api") else n.noticias_da_pagina(f)
    except Exception as e:
        print("ERRO", f["nome"], e); continue
    inc = re.compile(f["incluir"], re.I) if f.get("incluir") else n.INCLUIR
    print("##", f["nome"], len(a))
    for l, t in list(a.items())[:40]: print("  ", "INCLUI" if inc.search(t) and not n.EXCLUIR.search(t) else "-", t[:100], l[-60:])
