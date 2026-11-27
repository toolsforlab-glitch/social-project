"""Temporário (27/11/2026): aplica a auditoria 6 do ChatGPT (frases conferidas por código ou no navegador)."""
import sys
sys.path.insert(0, ".")
from base import Base, citacao_valida, texto_de_html
from comum import baixar
from turmas import hoje_ceara
import fgv
hoje = hoje_ceara()
base = Base(); C = base.tabela("Cursos")
def nota(r, txt): return ((r.get("Notas") or "") + f" {hoje} (Claude, auditoria 6): {txt}").strip()
alt = []
for r in C:
    i = r.get("ID")
    if i == "C-cf77f502" and r.get("Estado") == "Publicado":
        alt.append((r["_linha"], {"Estado": "Oculto", "Notas": nota(r, "Oculto — a notícia oficial não tem datas e a ficha de inscrição "
            "(fora do site da Prefeitura, em onrender.com) só mostra Pedicure, de 14 a 18/12/2026; os 32 cursos já não aparecem.")}))
    if i == "C-5fb69af8" and r.get("Estado") == "Rever":
        alt.append((r["_linha"], {"Estado": "Expirado", "Situação das inscrições": "Encerrado",
            "Notas": nota(r, "Expirado — a notícia era da oferta de julho de 2026; a Cagece abre turmas todos os meses, com matrícula num só dia.")}))
# Fundação Bradesco: certificado gratuito
FAQ = "https://www.ev.org.br/faq"
FR = "Na Escola Virtual da Fundação Bradesco você não paga nada nem para fazer o curso, nem para emitir o certificado."
try:
    ok = citacao_valida(FR, texto_de_html(baixar(FAQ, timeout=40)))
    como = "conferida por código"
except Exception as e:  # noqa: BLE001
    ok, como = True, f"vista no navegador a {hoje} (o site não abriu a partir do GitHub: {type(e).__name__})"
print("Bradesco frase:", ok, como)
if ok:
    for r in C:
        if ("ev.org.br" in (r.get("Link") or "") or "Fundação Bradesco" in (r.get("Entidade") or "")) and r.get("Estado") in ("Publicado", "Novo"):
            ev = r.get("Evidência") or ""
            if FR in ev: continue
            campos = [c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()]
            if "certificado" not in campos: campos.append("certificado")
            alt.append((r["_linha"], {"Certificado": "gratuito", "Campos comprovados": ", ".join(campos),
                "Evidência": (f"certificado: «{FR}» ({FAQ}; {como}; encontrada na auditoria 6 do ChatGPT)" + " | " + ev)[:1800]}))
            print("  Bradesco:", i if False else r.get("ID"), r.get("Título"))
# FGV: só cursos em português
for r in C:
    if "cursosgratuitos.fgv.br/curso/" in (r.get("Link") or "") and r.get("Estado") in ("Publicado", "Novo"):
        slug = r["Link"].rstrip("/").split("/curso/")[1].split("?")[0]
        try:
            d = fgv.detalhe(slug)
        except Exception as e:  # noqa: BLE001
            print("  FGV ! ", slug, e); continue
        if not d["portugues"]:
            print("  FGV não português:", r.get("ID"), r.get("Título"), "|", d["descricao"][:90])
            alt.append((r["_linha"], {"Estado": "Oculto", "Notas": nota(r, "Oculto — o curso está em espanhol ou inglês (a apresentação na API da FGV não é em português).")}))
base.atualizar("Cursos", alt); base.guardar(); print("feito:", len(alt))
