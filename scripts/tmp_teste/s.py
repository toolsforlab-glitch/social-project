import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
def corpo(b):
    m = re.search(r"(?s)<main.*?</main>|<article.*?</article>", b); return limpo(m.group(0) if m else b)
for u in ["https://www.rn.senai.br/gratuidade", "https://www.rn.senai.br/assets/js/oportunidades.js?v=1"]:
    try:
        b=baixar(u,timeout=40).decode("utf-8","replace"); print("#####",u,len(b))
        t=corpo(b) if "js" not in u[-8:] else b
        i=t.find("ratuit"); print(t[:4000] if "oportunidades.js" in u else t[max(0,i-1500):i+3500])
    except Exception as e: print("ERRO",u,type(e).__name__,str(e)[:100])
b=baixar("https://www.sesiac.org.br/educacao/educacao-basica/educacao-de-jovens-e-adultos-nova-eja-profissionalizante.html",timeout=40).decode("utf-8","replace")
t=limpo(b); i=t.find("Nova EJA"); print("##### SESI EJA"); print(t[i:i+3500])
