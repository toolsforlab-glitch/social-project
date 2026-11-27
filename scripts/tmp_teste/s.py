import sys, re, os
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
U = ["https://www.senaimt.ind.br/para-voce/cursos/detalhes/QUA-711.01/cursos-de-curta-duracao/eletricista-instalador-residencial/", "https://www.senaimt.ind.br/"]
for i, u in enumerate(U):
    try:
        b = baixar(u, timeout=20).decode("utf-8", "replace"); open(f"../sonda/r{i}.html", "w").write(b)
        t = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", b, flags=re.S)))
        print("OK", len(b), u, "|", t[:160]); [print("   G:", x[:200]) for x in re.findall(r".{0,120}(?:gratu|R\$|valor|fam[íi]lia).{0,80}", t, re.I)[:12]]
        for m in sorted(set(re.findall(r'href="([^"]+)"', b))):
            if re.search(r"famil|capacita|gratu|edital", m, re.I): print("    ", m[:170])
    except Exception as e:
        print("ERRO", type(e).__name__, str(e)[:120], u)
