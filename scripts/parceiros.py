"""Propostas de cursos enviadas por organizações parceiras.

1. Copia as respostas novas do Formulário Google (separador "Respostas ao formulário…") para "Propostas de parceiros".
2. Cada proposta marcada como "Aceite" e ainda sem curso criado é organizada pelo Claude e acrescentada a "Cursos".
"""
import sys

from base import VERIFICACAO_INICIAL, Base, carregar_config, hoje_iso
from comum import ErroClaude, claude, extrair_json
from cursos import id_curso, ler_data

ABA = "Propostas de parceiros"
MAPA = [  # coluna de Propostas ← palavras que aparecem na pergunta do formulário
    ("Organização", ("organiza", "entidade", "instituição")),
    ("Contacto", ("contacto", "contato", "e-mail", "email", "telefone", "whatsapp")),
    ("Título do curso", ("nome do curso", "título", "titulo", "curso")),
    ("Link", ("link", "site", "inscri")),
    ("Cidade", ("cidade", "município", "municipio", "local")),
    ("Modalidade", ("modalidade", "online", "presencial")),
    ("Datas e horários", ("data", "horário", "horario", "quando")),
    ("Para quem é / requisitos", ("para quem", "requisito", "público", "publico")),
    ("Descrição", ("descri", "sobre", "o que se aprende")),
]

SISTEMA = """Organizas propostas de cursos gratuitos enviadas por organizações sociais, para um site público. \
Usa só a informação dada. Escreve em linguagem simples (frases curtas, palavras do dia a dia), em português \
do Brasil para cursos no Brasil e de Portugal para cursos em Portugal. Nunca rotules as pessoas.
Responde só com JSON entre <json></json> com: titulo, descricao (1-2 frases), modalidade (online, presencial \
ou misto), local (um id da lista dada), regiao, cidade, necessidades (ids), perfis (ids), exclusivo_para, \
requisitos, certificado (gratuito, pago, sem certificado ou desconhecido), inscricoes_ate (AAAA-MM-DD ou null), \
inicio (AAAA-MM-DD ou null), duracao, como_me_inscrever (lista de 3 a 5 passos curtos)."""


def importar_formulario(base):
    abas = [a for a in base.abas() if a.lower().startswith(("respostas ao formul", "form responses"))]
    if not abas:
        return 0
    existentes = {(r.get("Data", ""), r.get("Título do curso", "")) for r in base.tabela(ABA)}
    novas = []
    for aba in abas:
        valores = base.valores(aba)
        if len(valores) < 2:
            continue
        cab = [c.lower() for c in valores[0]]
        indices = {}
        for destino, chaves in MAPA:
            for i, pergunta in enumerate(cab):
                if i not in indices.values() and any(k in pergunta for k in chaves):
                    indices[destino] = i
                    break
        for linha in valores[1:]:
            if not any(linha):
                continue
            proposta = {d: (linha[i] if i < len(linha) else "") for d, i in indices.items()}
            proposta["Data"] = linha[0]
            if (proposta["Data"], proposta.get("Título do curso", "")) in existentes:
                continue
            proposta["Estado"] = "Nova"
            novas.append(proposta)
    base.acrescentar(ABA, novas)
    return len(novas)


def criar_cursos(base, cfg):
    locais = cfg["cursos"]["locais"]
    pendentes = [r for r in base.tabela(ABA) if r.get("Estado") == "Aceite" and not r.get("ID do curso criado")]
    if not pendentes:
        return 0
    modelo = cfg.get("modelo_cursos", "claude-haiku-5-5")
    necessidades = ", ".join(f"{n['id']} ({n['rotulo']})" for n in cfg["cursos"]["necessidades"])
    novos, alteracoes = [], []
    for p in pendentes:
        dados = {k: p.get(k, "") for k in ("Organização", "Título do curso", "Link", "Cidade", "Modalidade",
                                            "Datas e horários", "Para quem é / requisitos", "Descrição")}
        pedido = (f"Data de hoje: {hoje_iso()}.\nLocais possíveis (id: nome): "
                  f"{', '.join(l['id'] + ': ' + l['rotulo'] for l in locais)}.\n"
                  f"Necessidades (ids): {necessidades}.\nPerfis (ids): {', '.join(cfg['cursos']['perfis_internos'])}.\n\n"
                  f"Proposta: {dados}")
        try:
            texto, _ = claude(modelo, SISTEMA, pedido, max_tokens=4000)
        except ErroClaude as e:
            print(f"  ERRO: {e}")
            continue
        c = extrair_json(texto)
        if not isinstance(c, dict) or not c.get("titulo"):
            print(f"  ? Proposta sem resposta válida: {dados['Título do curso']}")
            continue
        link = p.get("Link") or ""
        local = c.get("local") if c.get("local") in {l["id"] for l in locais} else cfg.get("territorio_piloto", "")
        curso = {
            "ID": id_curso(link or p.get("Organização", ""), c["titulo"]), "Estado": "Publicado",
            "Título": c["titulo"], "Entidade": p.get("Organização", ""), "Link": link, "Local": local,
            "Modalidade": c.get("modalidade") or "presencial", "País": "PT" if local == "PT" else "BR",
            "Região": c.get("regiao") or "", "Cidade": c.get("cidade") or p.get("Cidade", ""),
            "Descrição": c.get("descricao") or "",
            "Necessidades": ", ".join(c.get("necessidades") or []), "Perfis": ", ".join(c.get("perfis") or []) or "todos",
            "Condição de acesso": c.get("exclusivo_para") or "", "Requisitos": c.get("requisitos") or "",
            "Certificado": c.get("certificado") or "desconhecido",
            "Inscrições até": ler_data(c.get("inscricoes_ate")), "Início": ler_data(c.get("inicio")),
            "Duração": c.get("duracao") or "", "Link verificado": "", "Primeiro visto": hoje_iso(),
            "Última verificação": hoje_iso(), "Origem": "manual",
            "Notas": f"Proposta de {p.get('Organização', '')} ({p.get('Contacto', '')})",
            "Como me inscrever": "\n".join(f"{i}. {s}" for i, s in enumerate((c.get("como_me_inscrever") or [])[:5], 1)),
            "Nota da verificação": "",
            **VERIFICACAO_INICIAL,
            # proposta aceite por uma pessoa: conta como revista; a rotina não altera os campos importantes
            "Revisto por pessoa": hoje_iso(), "Situação das inscrições": "Aberto",
        }
        novos.append(curso)
        alteracoes.append((p["_linha"], {"ID do curso criado": curso["ID"]}))
        print(f"  + {curso['Título']} ({curso['Entidade']})")
    base.acrescentar("Cursos", novos)
    base.atualizar(ABA, alteracoes)
    return len(novos)


def main():
    base = Base()
    cfg = carregar_config(base)
    importadas = importar_formulario(base)
    criados = criar_cursos(base, cfg)
    base.guardar()
    print(f"Propostas importadas do formulário: {importadas} | cursos criados a partir de propostas aceites: {criados}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
