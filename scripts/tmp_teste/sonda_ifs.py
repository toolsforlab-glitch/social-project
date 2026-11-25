import sys, re, html
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
def t(u, n=60): return baixar(u, timeout=n).decode("utf-8", "replace")
def limpo(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", s))).strip()
for u in ["https://processoseletivo.ifrn.edu.br/edital/visualizar/696/", "https://processoseletivo.ifrn.edu.br/edital/visualizar/684/",
          "https://processoseletivo.ifrn.edu.br/edital/visualizar/683/"]:
    a = t(u); print("#####", u); print("  hrefs:", sorted(set(re.findall(r"href=['\"]([^'\"#]+)", a)))[:60])
    print("  ", limpo(a)[:1800])
a = t("https://ifce.edu.br/campus/aracati/estude-no-ifce/aracati-selecao-de-participantes-do-curso-fic-empreendedorismo-artesanal-renda-de-labirinto-edital-272026/")
print("##### IFCE Aracati"); print("  hrefs:", [x for x in re.findall(r'href="([^"]+)"', a) if re.search(r"\.pdf|edital|anexo|inscri|forms|@@|download", x, re.I)][:30])
m = re.search(r'(?s)<div id="content".*', a); print("  ", limpo(m.group(0) if m else a)[:3000])
# PDFs do IFRN 68
a = t("https://processoseletivo.ifrn.edu.br/edital/visualizar/696/")
for x in sorted(set(re.findall(r"href=['\"]([^'\"#]+)", a))):
    if re.search(r"arquivo|download|media|documento|\.pdf", x, re.I):
        u = x if x.startswith("http") else "https://processoseletivo.ifrn.edu.br" + x
        try:
            d = baixar(u, timeout=60)
            if d[:4] == b"%PDF":
                tx = texto_de_html(d); print("##### PDF", u, len(tx))
                for pat in [r".{0,200}sorteio.{0,300}", r".{0,200}an[áa]lise.{0,200}", r".{0,150}prova.{0,150}", r".{0,100}idade.{0,150}", r".{0,200}pr[ée]-requisito.{0,300}", r".{0,200}gratuit.{0,200}"]:
                    for m in list(re.finditer(pat, tx, re.I))[:2]: print("   ", pat[:14], "→", m.group(0)[:500])
        except Exception as e: print("ERRO", u, e)
