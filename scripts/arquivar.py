"""Tira da base os cursos e as turmas que já terminaram, sem os apagar: passam para separadores de arquivo.

Regras (só linhas que já não aparecem no site há pelo menos N dias; N = arquivo_dias na Configuração, 30 por omissão):
- Turmas: Situação = Encerrada e prazo de inscrição (ou, se não houver, início) há mais de N dias.
- Cursos: Estado = Expirado e última verificação há mais de N dias; ou curso criado pelas turmas (Senac, Centec)
  sem turmas abertas há mais de N dias.
- Nunca se arquiva um curso Oculto (é o que impede que volte a ser criado) nem um curso com "Revisto por pessoa".
As linhas arquivadas ficam em "Arquivo de cursos" e "Arquivo de turmas", com a data em que foram arquivadas.
Para recuperar uma linha, basta copiá-la de volta.
"""
import datetime
import sys

from base import Base, carregar_config, hoje_iso, numero


def mover(base, aba, arquivo, escolher, hoje):
    if aba not in base.abas():
        return 0
    cab = base.cabecalho(aba)
    linhas = [r for r in base.tabela(aba) if escolher(r)]
    if not linhas:
        return 0
    base.criar_aba(arquivo, cab + ["Arquivado em"])
    base.acrescentar(arquivo, [{**{c: r.get(c, "") for c in cab if c}, "Arquivado em": hoje} for r in linhas])
    base.remover_linhas(aba, [r["_linha"] for r in linhas])
    return len(linhas)


def main():
    base = Base()
    cfg = carregar_config(base)
    hoje = hoje_iso()
    dias = int(numero(cfg.get("arquivo_dias"), 30))
    corte = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=dias)).isoformat()

    def turma_antiga(t):
        ref = (t.get("Prazo de inscrição") or t.get("Início") or t.get("Última verificação") or "")[:10]
        return (t.get("Situação") or "").strip() == "Encerrada" and ref and ref < corte

    def curso_antigo(r):
        estado = (r.get("Estado") or "").strip()
        if not r.get("ID") or estado == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            return False
        visto = (r.get("Última verificação") or r.get("Primeiro visto") or "")[:10]
        if not visto or visto >= corte:
            return False
        # cursos acompanhados turma a turma (Senac, Centec): sem turmas abertas há mais de N dias
        por_turmas = r.get("Origem") == "turmas" or any(
            f in (r.get("Link") or "") for f in ("psg.ce.senac.br", "centec.org.br/cursos-formacao",
                                                 "ma.senac.br/editais-psg"))
        return estado == "Expirado" or (por_turmas and r.get("Situação das inscrições") == "Encerrado")

    n_turmas = mover(base, "Turmas", "Arquivo de turmas", turma_antiga, hoje)
    n_cursos = mover(base, "Cursos", "Arquivo de cursos", curso_antigo, hoje)
    base.guardar()
    print(f"Arquivo: {n_cursos} cursos e {n_turmas} turmas terminados há mais de {dias} dias passaram para o arquivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
