import json, sys, time
sys.path.insert(0, ".")
from comum import baixar
B = "https://www.sp.senac.br"
try:
    j = json.loads(baixar(f"{B}/o/senac-curso-services/cursos/20125/20102?turmasBolsa=true&start=0&end=5&sort=localized_title_pt_BR_sortable", timeout=40))
    print("cursos total", j.get("total"), [c["title"] for c in j["cursos"]])
    c = j["cursos"][0]
    ci = json.loads(baixar(f"{B}/o/senac-content-services/cursosInfoDetalhe/20125/{c['articleId']}?inscricaoAberta=false&bolsaAberta=true&buscarUnidadesComOferta=true", timeout=40))
    u = ci.get("unidadesComOferta") or []
    print("unidades", [(x["nomeUnidade"], x["categoryId"]) for x in u])
    q = f"codigoFTOferta={c['codigoFT']}&dataEfetivaOferta={c['dataEfetivaFT']}&categoryIds={','.join(str(x['categoryId']) for x in u)}&start=0&end=50&bolsaAberta=true&cursoArticleId={c['articleId']}&considerarDataBolsaFutura=true"
    of = json.loads(baixar(f"{B}/o/senac-oferta-services/ofertasPorCategoryIds/20125?{q}", timeout=40))
    print("ofertas", len(of))
    print("possoFazer", str(ci.get("possoFazerEsseCurso"))[:400])
    print("bolsas page ok", len(baixar(f"{B}/bolsas-de-estudo", timeout=40)))
except Exception as e:
    print("ERRO", type(e).__name__, e)
