import sys, re, json, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
u="https://www.rn.senai.br/transparencia/includes/api/api-oportunidades.php?acao=resultado&modalidade=&produto=&cidade=&area=&curso="
try:
    b=baixar(u,timeout=40).decode("utf-8","replace"); print("##### SENAI RN", len(b)); print(b[:300]); print(limpo(b)[:6000])
    print("LINKS:", re.findall(r'href="([^"]+)"', b)[:30])
except Exception as e: print("ERRO RN", e)
for u in ["https://www.sesiac.org.br/", "https://www.sesiac.org.br/eja", "https://www.fieac.org.br/", "https://acre.sesi.org.br/"]:
    try:
        b=baixar(u,timeout=30).decode("utf-8","replace"); print("#####",u,len(b))
        for h,t in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', b, re.S):
            if re.search(r"eja|jovens|educa|matr", h+limpo(t), re.I): print("  ",limpo(t)[:80],"|",h)
    except Exception as e: print("ERRO",u,type(e).__name__,str(e)[:100])
