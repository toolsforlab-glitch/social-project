import sys, re, json, html, subprocess, tempfile
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
b=baixar("https://www.rn.senai.br/publicacoes/",timeout=40).decode("utf-8","replace")
print("SCRIPTS:", re.findall(r'<script[^>]+src="([^"]+)"', b)[-6:])
links=[(limpo(t)[:120],h) for h,t in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', b, re.S) if re.search(r"edital|\.pdf|processo|seletiv", h+limpo(t), re.I)]
for l in links[:60]: print("  ",l)
print(limpo(b)[:1500])
for api in ["https://www.rn.senai.br/transparencia/includes/api/api-publicacoes.php?acao=filtros","https://www.rn.senai.br/transparencia/includes/api/api-publicacoes.php?acao=resultado"]:
    try: print("#####",api, baixar(api,timeout=30).decode("utf-8","replace")[:1500])
    except Exception as e: print("ERRO",api,e)
