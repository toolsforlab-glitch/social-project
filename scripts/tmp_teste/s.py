import sys, re, json
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from base import baixar
U = [
 "https://www.manaus.am.gov.br/wp-json/wp/v2/posts?search=cursos%20gratuitos&per_page=10&_fields=date,link,title",
 "https://www.manaus.am.gov.br/wp-json/wp/v2/posts?search=semtepi%20cursos&per_page=10&_fields=date,link,title",
 "https://www.manaus.am.gov.br/semtepi/",
 "https://www.am.gov.br/wp-json/wp/v2/posts?search=cursos%20gratuitos&per_page=10&_fields=date,link,title",
 "https://www.agenciaamazonas.am.gov.br/wp-json/wp/v2/posts?search=cursos%20gratuitos&per_page=10&_fields=date,link,title",
 "https://www.cetam.am.gov.br/wp-json/wp/v2/posts?per_page=5&_fields=date,link,title",
 "https://www2.ifam.edu.br/noticias",
 "https://portal.ifam.edu.br/",
 "https://www.ifam.edu.br/",
 "https://www2.ifam.edu.br/editais",
]
for u in U:
    try:
        b = baixar(u, timeout=20).decode("utf-8", "replace")
        print("OK", len(b), u)
        if "wp-json" in u:
            try:
                for p in json.loads(b)[:10]:
                    print("   ", p["date"][:10], re.sub("<[^>]+>", "", p["title"]["rendered"])[:110], p["link"])
            except Exception as e: print("   json?", b[:200])
        else:
            t = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", b))
            print("   ", t[:300])
            for m in re.finditer(r'href="([^"]*(?:fic|edita|curso)[^"]*)"', b, re.I):
                print("    link", m.group(1)[:150])
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:150], u)
