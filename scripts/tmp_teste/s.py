import sys, re, os
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
U = ["https://www.senaimt.com.br/", "https://www.senaimt.com.br/gratuidade", "https://ingresso.senaimt.com.br/",
     "https://www.ms.senai.br/", "https://www.ms.senai.br/gratuidade", "https://www.ms.senai.br/oportunidades/",
     "https://www.senaims.com.br/", "https://www.fiems.com.br/senai", "https://www.senaigo.com.br/", "https://www.senaidf.com.br/"]
for i, u in enumerate(U):
    try:
        b = baixar(u, timeout=20).decode("utf-8", "replace"); open(f"../sonda/r{i}.html", "w").write(b)
        t = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", b, flags=re.S)))
        print("OK", len(b), u, "|", t[:160])
        for m in sorted(set(re.findall(r'href="([^"]+)"', b))):
            if re.search(r"gratu|oportunid|edital|vaga|ingresso|processo|selet", m, re.I): print("    ", m[:170])
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:120], u)
