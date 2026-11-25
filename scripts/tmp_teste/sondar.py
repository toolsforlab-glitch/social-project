"""Temporário: baixa páginas e as guarda para análise (apagar depois)."""
import os, re, sys, hashlib, urllib.parse, json
sys.path.insert(0, "scripts")
from comum import baixar

PALAVRAS = re.compile(r"psg|gratu|edital|selec|inscri|curso|qualifica|turma|matricul", re.I)
os.makedirs("sonda", exist_ok=True)
urls = [u.strip() for u in open("scripts/tmp_teste/urls.txt") if u.strip() and not u.startswith("#")]
seguir = os.environ.get("SEGUIR") == "1"
vistos, resumo = set(), []

def guarda(u, prof):
    if u in vistos: return
    vistos.add(u)
    nome = re.sub(r"[^a-z0-9]+", "_", u.lower())[:90] + "_" + hashlib.sha1(u.encode()).hexdigest()[:6]
    try:
        b = baixar(u, timeout=60)
        open(f"sonda/{nome}.html", "wb").write(b)
        t = b.decode("utf-8", "replace")
        tit = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
        resumo.append({"url": u, "bytes": len(b), "titulo": (tit.group(1).strip() if tit else "")[:120], "arq": nome})
        print("OK", len(b), u, flush=True)
        if seguir and prof == 0:
            host = urllib.parse.urlparse(u).netloc
            for h in re.findall(r'href="([^"#]+)"', t):
                h = urllib.parse.urljoin(u, h)
                if urllib.parse.urlparse(h).netloc == host and PALAVRAS.search(h) and len(vistos) < 120:
                    guarda(h, 1)
    except Exception as e:
        resumo.append({"url": u, "erro": str(e)[:200]})
        print("ERRO", u, str(e)[:200], flush=True)

for u in urls:
    guarda(u, 0)
json.dump(resumo, open("sonda/resumo.json", "w"), ensure_ascii=False, indent=1)
