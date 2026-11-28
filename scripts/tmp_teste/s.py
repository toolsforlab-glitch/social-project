import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import senac_sc as m
from concurrent.futures import ThreadPoolExecutor
from comum import baixar
from base import texto_de_html, citacao_valida
links, total = m.cursos_abertos(); print("links", len(links), total)
f = texto_de_html(baixar(m.FAQ, timeout=60))
print("faq:", citacao_valida(m.FRASE_GRATUIDADE, f), citacao_valida(m.FRASE_RENDA, f), citacao_valida(m.FRASE_INSCRICAO, f))
with ThreadPoolExecutor(6) as ex:
    cs = [c for c in ex.map(lambda u: m._seguro(m.ler_curso, u), links) if c]
n = 0
for c in cs:
    g = [t for t in c["turmas"] if t["gratis"]]
    if not g: continue
    area = m._AREA.search(c["requisitos"])
    print("##", c["titulo"], "|", c["horas"], "h | área:", area.group(0) if area else "", "| req:", c["itens_req"], "| desc:", c["descricao"][:100])
    for t in g:
        n += 1; print("   ", t["codigo"], "|", t["unidade"], "|", t["cidade"], "|", t["dias"][:60], "|", t["ini"], t["fim"], "|", t["vagas"])
print("turmas grátis:", n)
