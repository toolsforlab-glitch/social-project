import re, subprocess, sys, time, os
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
B = "https://ps.ifgoiano.edu.br"
os.makedirs("../sonda", exist_ok=True)
for n in [708, 707, 716]:
    links = []
    for suf in ["", "?page=2", "?page=3"]:
        try:
            h = baixar(f"{B}/edital/visualizar/{n}/{suf}", timeout=40)
            h = h.decode("utf-8", "replace")
        except Exception as e:
            print(n, suf, "ERRO", e); continue
        if suf == "":
            open(f"../sonda/v{n}.txt", "w").write(texto_de_html(h))
        for m in re.findall(r'href="(/media/anexos_edital/[^"]+)"', h):
            if m not in links: links.append(m)
    print(n, "anexos:", len(links))
    for l in links:
        print("  ", l)
        if not re.search(r"edital|retifica", l, re.I) or re.search(r"anexo", l, re.I): continue
        try:
            b = baixar(B + l, timeout=60)
            p = f"../sonda/{n}_{len(os.listdir('../sonda'))}.pdf"; open(p, "wb").write(b)
            t = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True).stdout
            open(p[:-4] + ".txt", "w").write(t)
            print("     texto:", len(t))
        except Exception as e:
            print("     ERRO", e)
        time.sleep(2)
