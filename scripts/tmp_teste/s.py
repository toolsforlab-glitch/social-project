import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
for u in ["https://www.rn.senai.br/oportunidades/", "https://www.sesiac.org.br/educacao/educacao-basica/educacao-de-jovens-e-adultos-nova-eja-profissionalizante.html"]:
    try:
        b=baixar(u,timeout=40).decode("utf-8","replace"); t=limpo(b); print("#####",u,len(b))
        for m in re.finditer(r"[^.]{0,300}(gratuit|edital|sorteio|ordem de|baixa renda|regimenta|matr[íi]cula|inscri)[^.]{0,300}", t, re.I): print("  >", m.group(0)[:500])
        print("LINKS:", [ (limpo(x)[:60],h) for h,x in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', b, re.S) if re.search(r"edital|pdf|regimen|gratu|inscri|eja", h+limpo(x), re.I)][:25])
        print("SCRIPTS:", re.findall(r'<script[^>]+src="([^"]+)"', b)[:10])
    except Exception as e: print("ERRO",u,type(e).__name__,str(e)[:100])
