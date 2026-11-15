"""Auditoria e publicação dos guias "Antes de começar" (CPF, conta gov.br, CadÚnico).

Um guia só é publicado sozinho depois de duas verificações independentes contra a página oficial (coluna Fonte):

1. Por código: todas as frases guardadas em Evidência têm de existir, letra a letra, no texto da página.
2. Por um segundo modelo (modelo_auditoria), que não escreveu o guia: recebe o texto da página e cada passo
   do guia, e só confirma um passo se copiar as frases exatas da página que o provam. O código confere essas
   frases. Na dúvida, o passo não é confirmado.

Se tudo passar, o guia Novo passa a Publicado. Se falhar, fica como está (um guia que a rotina publicou volta
a Rever) e o motivo fica escrito. A rotina não mexe em guias com "Revisto por pessoa", Oculto, ou com
"Mudança a rever" marcada. Para não gastar, só volta a auditar quando a página ou o guia mudam.
"""
import hashlib
import re
import sys

from base import HISTORICO, Base, carregar_config, citacao_valida, hoje_iso, sim, texto_de_html
from comum import ErroClaude, baixar, claude, custo_estimado, extrair_json

ABA = "Antes de começar"
MAX_CARACTERES = 20000
CAMPOS = [("Onde fazer", "Onde se faz: "), ("Quanto custa", "Quanto custa: "), ("Quanto tempo leva", "Quanto tempo leva: ")]

AUDITOR = """És um auditor independente. Um site público, lido por pessoas com poucos recursos, vai publicar um \
guia passo a passo sobre um serviço do governo. Recebes o texto da página oficial e a lista numerada das \
afirmações do guia. Não foste tu que as escreveste e o teu trabalho é procurar erros: uma instrução errada pode \
fazer alguém perder uma viagem ou pagar o que não devia.

Para cada afirmação responde "confirmada" só se TUDO o que ela diz (lugares, valores, documentos, idades, \
prazos, ordem dos passos) estiver explicitamente na página, e copia em "frases" as frases EXATAS da página que \
o provam (letra a letra, cada uma até 30 palavras; várias se for preciso). Linguagem mais simples do que a da \
página é aceitável; informação a mais ou diferente não é. Em todos os outros casos responde "não confirmada" e \
diz em "motivo", numa frase curta, o que a página não diz ou diz de outra maneira. Não uses conhecimento geral.

Devolve só JSON entre <json></json>: {"afirmacoes": [{"n": 1, "veredicto": "confirmada" ou "não confirmada", \
"frases": ["..."], "motivo": "..."}]}"""


def afirmacoes_do_guia(g):
    lista = [l.strip() for l in str(g.get("Passos") or "").splitlines() if l.strip()]
    for coluna, rotulo in CAMPOS:
        if (g.get(coluna) or "").strip():
            lista.append(rotulo + g[coluna].strip())
    return lista


def evidencias_em_falta(g, pagina):
    falta = []
    for frase in re.findall(r"«(.*?)»", g.get("Evidência") or ""):
        for parte in re.split(r"\s*\[\.\.\.\]\s*", frase):
            if len(parte.strip()) >= 8 and not citacao_valida(parte, pagina):
                falta.append(parte.strip()[:70])
    return falta


def auditar(modelo, afirmacoes, pagina):
    pedido = ("Afirmações do guia:\n" + "\n".join(f"{i}. {a}" for i, a in enumerate(afirmacoes, 1))
              + f"\n\nTexto da página oficial:\n{pagina}")
    lista, custo = None, 0.0
    for _ in range(2):  # uma resposta ilegível é uma falha técnica: tenta outra vez, e não conta como reprovação
        texto, uso = claude(modelo, AUDITOR, pedido, max_tokens=8000)
        custo += custo_estimado(uso, modelo)
        res = extrair_json(texto)
        lista = res.get("afirmacoes") if isinstance(res, dict) else None
        if isinstance(lista, list):
            break
    if not isinstance(lista, list):
        raise ErroClaude("a auditoria não devolveu uma resposta legível")
    falhas = []
    for i, a in enumerate(afirmacoes, 1):
        v = next((x for x in lista if isinstance(x, dict) and str(x.get("n")) == str(i)), {})
        frases = [str(f) for f in (v.get("frases") or []) if str(f).strip()]
        if v.get("veredicto") != "confirmada":
            falhas.append(f"«{a[:60]}…»: {str(v.get('motivo') or 'não confirmada')[:140]}")
        elif not frases or not all(citacao_valida(f, pagina) for f in frases):
            falhas.append(f"«{a[:60]}…»: a frase indicada pelo auditor não está na página")
    return falhas, custo


def main():
    base = Base()
    cfg = carregar_config(base)
    if ABA not in base.abas():
        return 0
    modelo = cfg.get("modelo_auditoria") or "claude-sonnet-5-5"
    hoje = hoje_iso()
    alteracoes, historico, custo_total = [], [], 0.0
    for g in base.tabela(ABA):
        estado = (g.get("Estado") or "").strip()
        if not g.get("ID") or estado not in ("Novo", "Publicado") or (g.get("Revisto por pessoa") or "").strip():
            continue
        if sim(g.get("Mudança a rever")):
            print(f"  – {g['ID']}: tem 'Mudança a rever' marcada; fica para uma pessoa.")
            continue
        url = next(iter(re.findall(r"https?://[^\s|,]+", g.get("Fonte") or "")), "")
        try:
            pagina = texto_de_html(baixar(url, timeout=40))[:MAX_CARACTERES] if url else ""
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {g['ID']}: a fonte não abriu ({type(e).__name__}); nada alterado.")
            continue
        afirmacoes = afirmacoes_do_guia(g)
        impressao = hashlib.sha1((pagina + "|" + "|".join(afirmacoes)).encode()).hexdigest()[:12]
        if impressao == (g.get("Impressão da auditoria") or "").strip():
            alteracoes.append((g["_linha"], {"Última verificação": hoje}))
            print(f"  = {g['ID']}: página e guia iguais à última auditoria.")
            continue
        problemas = []
        if not pagina:
            problemas.append("sem fonte oficial indicada")
        else:
            falta = evidencias_em_falta(g, pagina)
            if falta:
                problemas.append("frases da Evidência que já não estão na página: " + "; ".join(f"«{f}»" for f in falta[:4]))
            else:
                try:
                    falhas, custo = auditar(modelo, afirmacoes, pagina)
                    custo_total += custo
                    problemas += falhas
                except ErroClaude as e:
                    print(f"  ERRO no Claude ({g['ID']}): {e}; nada alterado.")
                    continue
        campos = {"Última verificação": hoje, "Impressão da auditoria": impressao}
        if problemas:
            campos["Auditoria"] = (f"{hoje}: não passou: " + " | ".join(problemas))[:1500]
            if estado == "Publicado":
                campos["Estado"] = "Rever"
            print(f"  ! {g['ID']}: {len(problemas)} problemas")
        else:
            campos["Auditoria"] = (f"{hoje}: ok. Frases da Evidência conferidas na página e {len(afirmacoes)} afirmações "
                                   f"confirmadas por um segundo modelo ({modelo}), com frases conferidas por código.")
            if estado == "Novo":
                campos["Estado"] = "Publicado"
            print(f"  ✓ {g['ID']}: auditoria ok" + (" → Publicado" if estado == "Novo" else ""))
        if "Estado" in campos:
            historico.append({"Data e hora": hoje, "ID do curso": g["ID"], "Título": g.get("Título", ""),
                              "Tipo de verificação": "Auditoria do guia", "Resultado": campos["Estado"],
                              "Estado antes": estado, "Estado depois": campos["Estado"], "Notas": campos["Auditoria"][:500]})
        alteracoes.append((g["_linha"], campos))
    base.atualizar(ABA, alteracoes)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"Guias: custo estimado da auditoria {round(custo_total, 3)} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
