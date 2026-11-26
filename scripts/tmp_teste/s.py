import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
for u in ["https://gorecife.recife.pe.gov.br/", "https://gorecife.recife.pe.gov.br/cursos", "https://www.iema.ma.gov.br/", "https://iema.ma.gov.br/editais"]:
    try:
        b = baixar(u, timeout=30).decode("utf-8", "replace")
        print("#####", u, len(b)); print(limpo(b)[:1500])
        print("SCRIPTS:", re.findall(r'<script[^>]+src="([^"]+)"', b)[:8])
        print("API?:", sorted(set(re.findall(r'["\'](/?api/[^"\']+|https?://[^"\']*api[^"\']*)["\']', b)))[:15])
        print("LINKS:", [ (limpo(t)[:60], h) for h, t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S) if re.search(r"curso|edital|inscri|vaga", limpo(t)+h, re.I)][:25])
    except Exception as e:
        print("ERRO", u, type(e).__name__, str(e)[:150])
