import sys, re, datetime
sys.path.insert(0, "scripts")
import ifro_fic as f
hoje = datetime.date(2026, 11, 25)
for e in f.editais_recentes(hoje):
    try:
        pdf, t = f.pdf_do_edital(e["link"])
    except Exception as ex:
        print("ERRO", e["titulo"], ex); continue
    print("=" * 30, e["titulo"], "|", pdf, "| chars", len(t))
    for pat in [r"Vagas.{0,300}", r"Per[ií]odo.{0,200}", r".{0,150}ordem de chegada.{0,80}", r".{0,100}sortei.{0,100}", r"idade m[ií]nima.{0,100}", r"Previs[ãa]o de in[ií]cio.{0,60}"]:
        m = re.search(pat, t, re.I | re.S)
        print("  ", pat[:20], "→", (m.group(0)[:400].replace("\n", " ") if m else None))
    print("  INÍCIO:", t[:500].replace("\n", " "))
