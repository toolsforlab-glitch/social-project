import re, sys
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
U = [
 "https://www.go.senac.br/", "https://www.go.senac.br/psg/", "https://www.go.senac.br/capacitarse", "https://www.go.senac.br/cursos-gratuitos/",
 "https://www.df.senac.br/cursos-gratuitos", "https://www.df.senac.br/",
 "https://www.mt.senac.br/", "https://www.mt.senac.br/psg",
 "https://www.ms.senac.br/cursos-gratuitos", "https://ww3.ms.senac.br/", "https://www.ms.senac.br/",
 "https://senaigo.com.br/", "https://www.senaidf.org.br/", "https://www.senaimt.ind.br/", "https://www.ms.senai.br/",
 "https://www.ifg.edu.br/", "https://selecao.ifg.edu.br/", "https://www.ifgoiano.edu.br/", "https://selecao.ifmt.edu.br/", "https://selecao.ifms.edu.br/", "https://www.ifb.edu.br/",
 "https://goias.gov.br/", "https://www.agenciabrasilia.df.gov.br/", "https://www.mt.gov.br/", "https://www.ms.gov.br/",
 "https://www.goiania.go.gov.br/", "https://www.cuiaba.mt.gov.br/", "https://www.campogrande.ms.gov.br/",
]
for u in U:
    try:
        b = baixar(u, timeout=15)
        h = b.decode("utf-8", "replace"); t = texto_de_html(b)
        tit = (re.search(r"<title[^>]*>([^<]{0,90})", h, re.I) or [None, ""])[1].strip()
        kw = sorted(set(m.group(0).lower() for m in re.finditer(r"gratuit\w*|gratuidade|psg|inscri\w+ abert\w*|edita\w+|wp-json|rest_route", t + h, re.I)))[:8]
        links = [l for l in dict.fromkeys(re.findall(r'href="([^"]+)"', h)) if re.search(r"gratu|psg|edita|curso|selec|capacit|inscri", l, re.I)][:12]
        print(f"\nOK {u} | {len(b)} B | {tit} | {kw}\n   {links}")
    except Exception as e:
        print(f"\nFALHA {u} | {type(e).__name__} {str(e)[:70]}")
