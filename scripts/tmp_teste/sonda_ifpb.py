import sys, re, html, urllib.parse
sys.path.insert(0, "scripts")
from comum import baixar
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
for u in ["https://www.ifpb.edu.br/editais", "https://www.ifpb.edu.br/editais?b_start:int=0&tipo=FIC",
          "https://www.ifpb.edu.br/@@search?SearchableText=FIC&portal_type=Folder&sort_on=created&sort_order=reverse",
          "https://www.ifpb.edu.br/@@search?SearchableText=%22forma%C3%A7%C3%A3o%20inicial%20e%20continuada%22&sort_on=created&sort_order=reverse",
          "https://estudante.ifpb.edu.br/cursos/?tipo=fic", "https://www.ifpb.edu.br/ensino/cursos-fic"]:
    try:
        a = t(u)
    except Exception as e:
        print("ERRO", u, e); continue
    print("#####", u, len(a))
    links = []
    for h, x in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', a, re.S):
        x = limpo(x)
        if re.search(r"FIC|Forma[çc][ãa]o Inicial|curso|sele[çc][ãa]o|edital", x, re.I) and len(x) > 15:
            links.append((x[:150], urllib.parse.urljoin(u, h)))
    for l in links[:40]: print("  ", l)
    m = re.search(r'(?s)<main.*?</main>|<div id="content".*', a); print("  TXT:", limpo(m.group(0) if m else a)[:1500])
