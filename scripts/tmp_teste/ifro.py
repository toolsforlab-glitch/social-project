import re, sys, html
sys.path.insert(0, "scripts")
from comum import baixar
import vigiar
v = [x for x in vigiar.VIGIAS if x["nome"].startswith("IFRO")][0]
for url in v["itens"]:
    t = baixar(url, 40).decode("utf-8", "replace")
    for bloco in t.split('<div class="tileItem">')[1:]:
        m = re.search(v["item"], bloco, re.S)
        d = re.search(r"icon-calendar\"></i>\s*(\d{2})/(\d{2})/(\d{2})", bloco)
        if m and d and d.group(3) == "26" and int(d.group(2)) >= 10:
            ti = html.unescape(m.group(2)).strip()
            ok = re.search(v["incluir"], ti, re.I) and not re.search(v["excluir"], ti, re.I)
            print("✓" if ok else "✗", d.group(0)[-8:], ti, "https://selecao.ifro.edu.br" + m.group(1))
