import sys, re, html, urllib.parse
sys.path.insert(0, "scripts")
from comum import baixar
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
def corpo(b):
    x = limpo(b); i = x.find("Ir para o conteúdo"); j = x.find("Campi Areia"); k = x.find("Sousa Sumé", j)
    return x[k:] if k > 0 else x
for u in ["https://estudante.ifpb.edu.br/processoseletivo/processo/7/", "https://estudante.ifpb.edu.br/editais/?page=2", "https://estudante.ifpb.edu.br/editais/?page=3"]:
    try: b = t(u)
    except Exception as e: print("ERRO", u, e); continue
    print("#####", u)
    ls = [(limpo(x)[:150], urllib.parse.urljoin(u, h)) for h, x in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)]
    for l in [l for l in ls if "/editais/" in l[1] or "processo" in l[1]][:40]: print("  ", l)
    print("  TXT:", corpo(b)[:1800])
