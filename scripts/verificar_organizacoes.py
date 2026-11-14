"""Verificação das organizações e unidades de inscrição, sem Claude.

Para cada organização, lê o texto bruto das páginas indicadas em "Fonte" e confirma, por código,
se cada dado (morada, bairro, CEP, telefone, email, horário, o que levar) aparece lá tal como está
na folha. A rotina nunca altera esses dados: só regista o que está comprovado, o que deixou de
aparecer e o que falta confirmar, e marca "Mudança a rever" quando há risco.

Regras (ver também o separador "Como usar"):
- Só conta como prova o texto da página oficial, lido diretamente. Resumos de modelos não contam.
- Um dado que não aparece na fonte fica por confirmar e não aparece no site.
- Um dado que estava comprovado e deixou de aparecer marca a organização para rever.
- Se a fonte não abre, nada é alterado; só depois de N falhas seguidas a organização vai para rever.
- Organizações revistas por uma pessoa continuam a ser verificadas, mas a rotina apenas avisa.
"""
import os
import re
import sys

from base import HISTORICO, Base, carregar_config, hoje_iso, numero, sim, texto_de_html, trecho, valor_na_fonte
from comum import baixar

ABA = "Organizações"
CAMPOS = [("morada", "Morada", "texto"), ("bairro", "Bairro", "texto"), ("cep", "CEP", "cep"),
          ("telefone", "Telefone", "telefone"), ("whatsapp", "WhatsApp", "telefone"), ("email", "Email", "texto"),
          ("horário", "Horário de atendimento", "texto"), ("o que levar", "O que levar", "texto")]
MAX_POR_EXECUCAO = int(os.environ.get("MAX_ORGANIZACOES", "200"))


def fontes(r):
    return re.findall(r"https?://[^\s|,]+", r.get("Fonte") or "")


def ler_fontes(urls):
    textos, falhas = [], []
    for u in urls:
        try:
            textos.append(texto_de_html(baixar(u, timeout=30)))
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{u} ({type(e).__name__})")
    return textos, falhas


def main():
    base = Base()
    cfg = carregar_config(base)
    if ABA not in base.abas():
        print("Sem separador Organizações.")
        return 0
    limite_falhas = int(numero(cfg.get("falhas_link_para_rever"), 3))
    hoje = hoje_iso()
    alteracoes, historico = [], []
    contagem = {"verificadas": 0, "sem_fonte": 0, "fonte_falhou": 0, "a_rever": 0}

    linhas = [r for r in base.tabela(ABA) if (r.get("Estado") or "") != "Oculto" and r.get("ID")]
    for r in linhas[:MAX_POR_EXECUCAO]:
        urls = fontes(r)
        if not urls:
            contagem["sem_fonte"] += 1
            if r.get("Estado") in ("Novo", "Publicado"):
                alteracoes.append((r["_linha"], {"Mudança a rever": "TRUE",
                                                 "O que falta confirmar": "Sem fonte oficial indicada."}))
            continue
        textos, falhas = ler_fontes(urls)
        campos = {"Última verificação": hoje}
        if not textos:
            n = int(numero(r.get("Falhas seguidas da fonte"), 0)) + 1
            campos["Falhas seguidas da fonte"] = n
            contagem["fonte_falhou"] += 1
            if n >= limite_falhas:
                campos["Mudança a rever"] = "TRUE"
                campos["O que falta confirmar"] = f"A fonte não abre há {n} verificações seguidas: {'; '.join(falhas)}."
                historico.append(registo(r, "Página", "fonte não abre", campos["O que falta confirmar"]))
            alteracoes.append((r["_linha"], campos))
            print(f"  ✗ {r.get('Nome')}: fonte não abriu ({n}/{limite_falhas})")
            continue
        contagem["verificadas"] += 1
        campos["Falhas seguidas da fonte"] = 0

        antes = {c.strip() for c in (r.get("Campos comprovados") or "").split(",") if c.strip()}
        provados, nao, excertos = [], [], []
        for nome, coluna, tipo in CAMPOS:
            v = (r.get(coluna) or "").strip()
            if not v:
                continue
            if valor_na_fonte(v, textos, tipo):
                provados.append(nome)
                if tipo == "texto":
                    ex = next((trecho(v, t) for t in textos if trecho(v, t)), "")
                    if ex:
                        excertos.append(ex)
            else:
                nao.append(nome)
        sumiram = sorted(antes & set(nao))
        motivos = []
        if sumiram:
            motivos.append("Deixou de aparecer na página: " + ", ".join(sumiram) + ". A página pode ter mudado.")
        if nao and not sumiram:
            motivos.append("Não confirmado na página: " + ", ".join(nao) + ".")
        if falhas:
            motivos.append("Uma das fontes não abriu: " + "; ".join(falhas) + ".")

        campos["Campos comprovados"] = ", ".join(provados)
        if excertos:
            campos["Evidência"] = " | ".join(excertos)[:900]
        if motivos:
            campos["Mudança a rever"] = "TRUE"
            # mantém as notas que uma pessoa escreveu e acrescenta o motivo novo
            anterior = (r.get("O que falta confirmar") or "").strip()
            novo = " ".join(motivos)
            campos["O que falta confirmar"] = novo if not anterior or novo in anterior else f"{novo} {anterior}"[:900]
            contagem["a_rever"] += 1
        if sumiram or set(provados) != antes:
            historico.append(registo(r, "Página", "a rever" if motivos else "ok",
                                     " ".join(motivos) or "Campos comprovados: " + ", ".join(provados)))
        alteracoes.append((r["_linha"], campos))
        print(f"  {'!' if motivos else '✓'} {r.get('Nome')}: {', '.join(provados) or 'nada comprovado'}"
              + (f" | {' '.join(motivos)}" if motivos else ""))

    base.atualizar(ABA, alteracoes)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    print(f"\nResumo: {contagem}")
    return 0


def registo(r, tipo, resultado, notas):
    import datetime
    return {"Data e hora": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "ID do curso": r.get("ID", ""), "Título": r.get("Nome", ""), "Tipo de verificação": tipo,
            "Resultado": resultado,
            "Estado antes": r.get("Estado", ""), "Estado depois": r.get("Estado", ""), "Notas": notas[:500]}


if __name__ == "__main__":
    sys.exit(main())
