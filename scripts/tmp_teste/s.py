import sys, re, os
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
U = ["https://www.ms.senai.br/editais", "https://www.ms.senai.br/para-voce", "https://www.ms.senai.br/campanhas", "https://www.ms.senai.br/ultimas-noticias", "https://senaimt.com.br/", "https://www.senaimt.ind.br/"]
for i, u in enumerate(U):
    try:
        b = baixar(u, timeout=20).decode("utf-8", "replace"); open(f"../sonda/r{i}.html", "w").write(b)
        t = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", b, flags=re.S)))
        print("OK", len(b), u, "|", t[:160])
        for m in sorted(set(re.findall(r'href="([^"]+)"', b))):
            if re.search(r"gratu|oportunid|edital|vaga|ingresso|processo|selet|curso|noticias/", m, re.I): print("    ", m[:170])
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:120], u)
