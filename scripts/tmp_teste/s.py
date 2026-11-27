import sys, re, os, time, html as H
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
U = ["https://www.ifb.edu.br/estude-no-ifb/noticias/49199-conheca-os-cursos-na-modalidade-eja-ept",
     "https://www.ifb.edu.br/estude-no-ifb/noticias/49034-cursos-tecnicos-integrados-a-educacao-de-jovens-e-adultos-eja-inscricoes-abertas"]
for i, u in enumerate(U):
    try:
        b = baixar(u, timeout=25).decode("utf-8", "replace"); open(f"../sonda/ifb{i}.html", "w").write(b)
        k = b.find('itemprop="articleBody"'); seg = b[k:k+30000] if k > 0 else b
        seg = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>', r' [\1] ', seg)
        t = H.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", seg, flags=re.S))))
        print("OK", len(b), u); print(t[:7000])
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:120], u)
    time.sleep(5)
