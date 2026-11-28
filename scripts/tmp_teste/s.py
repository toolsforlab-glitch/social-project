import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
import urllib.request
os.makedirs("../sonda", exist_ok=True)
res = []
B = "https://mais.ifmg.edu.br/maisifmg"
urls = [B + "/enrol/index.php?id=62", B + "/course/view.php?id=62", B + "/course/info.php?id=62", B + "/local/staticpage/view.php?page=registro",
        B + "/enrol/index.php?id=125", B + "/enrol/index.php?id=612", B + "/enrol/index.php?id=232",
        "http://mooc.cps.sp.gov.br/", "https://mooc.cps.sp.gov.br/login/index.php", "https://mooc.cps.sp.gov.br/index.php",
        "https://www.cps.sp.gov.br/mooc/", "https://mooc.cps.sp.gov.br/moodle/"]
for i, u in enumerate(urls):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read(); fim = r.geturl()
        open(f"../sonda/{i}.html", "wb").write(b)
        t = b.decode("utf-8", "replace")
        res.append({"u": u, "fim": fim, "ok": len(b), "title": (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1][:100]})
    except Exception as e:
        res.append({"u": u, "erro": str(e)[:200]})
json.dump(res, open("../sonda/resumo.json", "w"))
