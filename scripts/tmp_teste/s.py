import sys, re, ssl, urllib.request, html
sys.path.insert(0, ".")
from comum import baixar
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
for u in ["https://psg.pi.senac.br/", "https://psg.pi.senac.br/vagas/", "https://psg.ce.senac.br/oportunidades/", "https://portal.ac.senac.br/psg/editais",
          "https://senaiac.org.br/senai-abre-120-vagas-para-cursos-gratuitos-em-rio-branco/"]:
    try:
        b = baixar(u, timeout=40).decode("utf-8", "replace")
        print("OK", u, len(b), "|", limpo(b)[:300])
    except Exception as e:
        print("ERRO", u, type(e).__name__, str(e)[:200])
try:
    ctx = ssl.create_default_context()
    import socket
    s = ctx.wrap_socket(socket.create_connection(("psg.pi.senac.br", 443), timeout=20), server_hostname="psg.pi.senac.br")
    c = s.getpeercert(); print("CERT PI:", c.get("notAfter"))
except Exception as e:
    print("CERT PI ERRO:", type(e).__name__, str(e)[:200])
