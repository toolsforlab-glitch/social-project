import sys, re, os
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
U = ["https://novidades.senaimt.ind.br/ser-familia-capacita"]
for i, u in enumerate(U):
    try:
        b = baixar(u, timeout=20).decode("utf-8", "replace"); open(f"../sonda/r{i}.html", "w").write(b)
        t = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", b, flags=re.S)))
        print("OK", len(b), u, "|", t[:6000]); [print("   G:", x[:200]) for x in re.findall(r".{0,120}(?:gratu|R\$|valor|fam[íi]lia).{0,80}", t, re.I)[:12]]
        for m in sorted(set(re.findall(r'href="([^"]+)"', b))):
            if re.search(r"inscri|famil|edital|form|pdf|whats", m, re.I): print("    ", m[:170])
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:120], u)
