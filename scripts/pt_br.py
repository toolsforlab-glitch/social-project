"""Passa para português do Brasil os textos já gravados na folha que o site e o responsável leem (21/11/2026).

Roda à mão (rotina “Rodar um passo”, passo pt_br.py). O Claude reescreve cada texto em pt-BR sem mudar o sentido,
e o código confere antes de gravar: as citações entre «» (frases copiadas das páginas oficiais), os links e os números
têm de ficar iguais, e o tamanho não pode mudar muito. A coluna Evidência nunca é tocada, nem as descrições copiadas
letra a letra da página oficial («Origem da descrição» = Texto da página).
"""
import datetime
import json
import re
import sys

from base import DESCRICAO_PAGINA, Base, carregar_config
from comum import claude, custo_estimado, extrair_json

TABELAS = {
    "Cursos": ["Descrição", "Como me inscrever", "Nota da verificação", "O que falta confirmar", "Requisitos",
               "Condição de acesso", "Notas", "Duração"],
    "Antes de começar": ["Para que serve", "Passos", "Onde fazer", "Quanto custa", "Quanto tempo leva",
                         "O que falta confirmar", "Notas"],
    "Notícias": ["Título", "Resumo", "Notas"],
}
LOTE = 25

SISTEMA = """Você converte textos de português de Portugal para português do Brasil (pt-BR), para um site brasileiro \
lido por pessoas com pouca escolaridade. Para cada texto: troque vocabulário, ortografia e construções de Portugal \
pelas do Brasil (ex.: "contacto" → "contato", "registo" → "registro", "equipa" → "equipe", "telemóvel" → "celular", \
"morada" → "endereço", "ecrã" → "tela", "ficheiro" → "arquivo", "noutra" → "em outra", "está a fazer" → "está \
fazendo", "inscrever-se" pode ficar, "contacte" → "entre em contato", aspas «assim» na sua própria redação → "assim"). \
Não mude o sentido, não acrescente nem tire informação, mantenha números, datas, links, quebras de linha e numeração. \
As citações entre «» que são frases copiadas de páginas oficiais ficam EXATAMENTE como estão, com os «». Se o texto \
já estiver em português do Brasil, devolva-o igual. Responda só com JSON entre <json></json>: {"id": "texto convertido"}."""


def confere(antes, depois):
    """O código confere a conversão. Devolve "" se estiver bem, ou o motivo."""
    if not isinstance(depois, str) or not depois.strip():
        return "vazio"
    for cit in re.findall(r"«([^»]{8,})»", antes):
        if cit not in depois:
            return "citação alterada"
    if set(re.findall(r"https?://\S+", antes)) - set(re.findall(r"https?://\S+", depois)):
        return "link alterado"
    if sorted(re.findall(r"\d+", antes)) != sorted(re.findall(r"\d+", depois)):
        return "números alterados"
    if not 0.7 <= len(depois) / max(len(antes), 1) <= 1.4:
        return "tamanho mudou demais"
    return ""


def main():
    base = Base()
    cfg = carregar_config(base)
    modelo = cfg.get("modelo_cursos")
    corte = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
    custo, mudados, recusados = 0.0, 0, []
    for aba, colunas in TABELAS.items():
        linhas = base.tabela(aba)
        itens = {}
        for r in linhas:
            if r.get("Estado") in ("Oculto", "Arquivado", "Expirado"):
                continue
            if aba == "Notícias" and (r.get("Estado") != "Publicado" or (r.get("Data") or "") < corte):
                continue
            for c in colunas:
                t = (r.get(c) or "").strip()
                if not t or len(t) < 4 or re.fullmatch(r"[\d\s.,:/hH-]+", t):
                    continue
                if c == "Descrição" and r.get("Origem da descrição") == DESCRICAO_PAGINA:
                    continue
                itens[f"{r['_linha']}|{c}"] = t
        print(f"{aba}: {len(itens)} textos para conferir")
        chaves = list(itens)
        alteracoes = {}
        for i in range(0, len(chaves), LOTE):
            lote = {k: itens[k] for k in chaves[i:i + LOTE]}
            try:
                texto, uso = claude(modelo, SISTEMA, json.dumps(lote, ensure_ascii=False), max_tokens=12000)
            except Exception as e:  # noqa: BLE001
                print(f"  ! lote {i // LOTE + 1}: {e}")
                continue
            custo += custo_estimado(uso, modelo)
            res = extrair_json(texto) or {}
            for k, antes in lote.items():
                depois = res.get(k)
                if not isinstance(depois, str) or depois.strip() == antes:
                    continue
                motivo = confere(antes, depois)
                if motivo:
                    recusados.append(f"{aba} {k}: {motivo}")
                    continue
                linha, col = k.split("|", 1)
                alteracoes.setdefault(int(linha), {})[col] = depois.strip()
                mudados += 1
        base.atualizar(aba, list(alteracoes.items()))
        print(f"  {aba}: {sum(len(v) for v in alteracoes.values())} textos convertidos")
    base.guardar()
    for r in recusados[:30]:
        print(f"  ✗ {r}")
    print(f"Convertidos: {mudados}; recusados pela conferência: {len(recusados)}; custo estimado: {custo:.3f} USD")


if __name__ == "__main__":
    sys.exit(main())
