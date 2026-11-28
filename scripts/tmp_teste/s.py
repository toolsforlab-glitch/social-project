import os, sys, json, re, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs("../sonda", exist_ok=True)
res = []
urls = ["https://www.pr.senac.br/", "https://www.pr.senac.br/cursos/contratos/2027_01/Edital_PSG_2027-1.pdf",
        "https://www.pr.senac.br/gratuidade/", "https://www.pr.senac.br/psg/",
        "https://www.sc.senac.br/psg/", "https://portal.sc.senac.br/psg/", "https://www.sc.senac.br/",
        "https://www.senacrs.com.br/", "https://www.senacrs.com.br/gratuidade", "https://www.senacrs.com.br/psg",
        "https://www.senairs.org.br/", "https://www.senaipr.org.br/", "https://sc.senai.br/"]
for i, u in enumerate(urls):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read(); fim = r.geturl()
        open(f"../sonda/{i}.html", "wb").write(b)
        t = b.decode("utf-8", "replace")
        res.append({"u": u, "fim": fim, "ok": len(b), "title": (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1][:80]})
    except Exception as e:
        res.append({"u": u, "erro": str(e)[:150]})
json.dump(res, open("../sonda/resumo.json", "w"))
