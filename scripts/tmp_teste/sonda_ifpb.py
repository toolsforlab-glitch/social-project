import sys, re, html, urllib.parse, os
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
def corpo(b):
    x = limpo(b); k = x.rfind("Últimas Notícias")
    return x[k:] if k > 0 else x
os.makedirs("sonda", exist_ok=True)
for ed in [478, 476, 473, 474, 475, 472, 477]:
    u = f"https://estudante.ifpb.edu.br/processoseletivo/processo/7/edicao/{ed}/"
    try: b = t(u)
    except Exception as e: print("ERRO", u, e); continue
    print("#####", u)
    ls = [(limpo(x)[:150], urllib.parse.urljoin(u, h)) for h, x in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)]
    ls = [l for l in ls if re.search(r"\.pdf|/editais/|arquivo|media|download|inscri", l[1] + l[0], re.I)]
    for l in ls[:20]: print("  ", l)
    print("  TXT:", corpo(b)[:2500])
    pdfs = [l[1] for l in ls if l[1].lower().endswith(".pdf") or "/media/" in l[1]]
    for p in pdfs[:2]:
        try:
            d = baixar(p, timeout=60)
            if d[:4] == b"%PDF":
                tx = texto_de_html(d); open(f"sonda/ifpb_{ed}_{pdfs.index(p)}.txt", "w").write(tx)
                print("  PDF", p, len(tx))
                for pat in [r".{0,200}sortei.{0,250}", r".{0,200}(an[áa]lise|crit[ée]rio).{0,250}", r".{0,150}entrevista.{0,150}", r".{0,150}\bprova\b.{0,150}", r".{0,120}idade.{0,150}"]:
                    for m in list(re.finditer(pat, tx, re.I))[:2]: print("    ", pat[:12], "→", m.group(0)[:450])
        except Exception as e: print("  ERRO pdf", p, e)
