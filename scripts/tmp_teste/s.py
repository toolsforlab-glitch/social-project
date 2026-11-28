import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
res = []
urls = ["https://mooc.cps.sp.gov.br/", "https://mooc.cps.sp.gov.br/course/index.php", "https://mooc.cps.sp.gov.br/cursos",
        "https://mais.ifmg.edu.br/", "https://mais.ifmg.edu.br/maisifmg/", "https://mais.ifmg.edu.br/course/index.php",
        "https://www.ifmg.edu.br/maisifmg"]
for i, u in enumerate(urls):
    try:
        b = baixar(u, timeout=40)
        open(f"../sonda/{i}.html", "wb").write(b)
        t = b.decode("utf-8", "replace")
        res.append({"u": u, "ok": len(b), "title": (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1][:100]})
    except Exception as e:
        res.append({"u": u, "erro": str(e)[:200]})
json.dump(res, open("../sonda/resumo.json", "w"))
