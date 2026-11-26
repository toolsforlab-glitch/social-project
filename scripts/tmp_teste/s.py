import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
def t(u, n=40): return baixar(u, timeout=n).decode("utf-8", "replace")
for u in ["https://al.rr.leg.br/2026/11/16/qualificacao-profissional-escolegis/", "https://al.rr.leg.br/2026/11/07/escolegis-cursos/"]:
    p = json.loads(t("https://al.rr.leg.br/wp-json/wp/v2/posts?slug=" + u.rstrip("/").rsplit("/",1)[-1] + "&_fields=date,content,link"))
    for x in p:
        c = x["content"]["rendered"]
        print("#####", x["date"], x["link"]); print(texto_de_html(c)[:3500])
        print("LINKS:", [h for h in re.findall(r'href="([^"]+)"', c)][:15])
posts = json.loads(t("https://rondonia.ro.gov.br/wp-json/wp/v2/posts?categories=205030&per_page=15&_fields=date,link,title"))
for x in posts: print(x["date"][:10], x["title"]["rendered"][:110], x["link"])
