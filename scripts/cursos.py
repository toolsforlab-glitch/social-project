"""Rotina semanal de cursos gratuitos: o Claude pesquisa só em fontes de confiança, classifica cada curso,
e a rotina confirma que o link abre antes de o acrescentar à folha."""
import datetime
import difflib
import hashlib
import os
import re
import sys

from base import VERIFICACAO_INICIAL, Base, carregar_config, hoje_iso
from comum import ErroClaude, claude, custo_estimado, dominio_permitido, extrair_json, hoje, verificar_link

ABA = "Cursos"
LOCALIZACAO = {
    "PT": {"type": "approximate", "country": "PT", "timezone": "Europe/Lisbon"},
    "BR-MA": {"type": "approximate", "country": "BR", "region": "Maranhão", "city": "São Luís", "timezone": "America/Fortaleza"},
    "BR-CE": {"type": "approximate", "country": "BR", "region": "Ceará", "city": "Fortaleza", "timezone": "America/Fortaleza"},
    "BR-AC": {"type": "approximate", "country": "BR", "region": "Acre", "city": "Rio Branco", "timezone": "America/Rio_Branco"},
}
NOMES_LOCAIS = {"BR-MA": "Maranhão", "BR-CE": "Ceará", "BR-AC": "Acre"}

SISTEMA = """Procuras cursos GRATUITOS para pessoas em situação de vulnerabilidade, para um site público \
em português. Pesquisa na web e usa só informação que encontraste nas páginas dos resultados.

Um curso só entra se cumprir TODAS estas regras:
1. É gratuito para quem o frequenta (inscrição e aulas sem custo). Conta como gratuito um programa oficial \
que é gratuito por regra (ex.: Programa Senac de Gratuidade, cursos FIC dos institutos federais, Centec), \
mesmo que a página não o repita em cada turma. Se houver taxa de inscrição, indica-o nos requisitos.
2. Está disponível agora: inscrições abertas, curso de acesso livre a qualquer momento, ou turma com data futura. \
Exclui cursos com inscrições já encerradas ou de anos anteriores. Um programa que abre inscrições \
regularmente (ex.: matrículas todos os meses) conta como disponível se a página mais recente for deste ano: \
diz nos requisitos quando costumam abrir as inscrições.
3. É de nível iniciante ou não exige formação anterior difícil (indica os requisitos que existirem).
4. É de uma entidade de confiança (organismo público, universidade, instituto federal, Sistema S, ONG reconhecida).
5. O link veio dos resultados da pesquisa e é a página PRÓPRIA deste curso (ou desta turma, ou do edital deste \
curso), onde a pessoa se inscreve. Não uses a página geral com a lista de cursos, a página inicial do campus ou \
uma página de pesquisa: abre a lista e usa o link do curso. Exceção: no Senac PSG (psg.ce.senac.br) usa a lista \
de oportunidades, porque as turmas de cada curso são lidas à parte. Se só encontraste o curso numa notícia, procura a página oficial; se não a encontrares, \
usa o link da notícia.

Na dúvida sobre um pormenor, inclui o curso e põe null nesse campo, em vez de o excluir.

NUNCA DEDUZAS. Cada campo só tem valor se a página o disser explicitamente para ESTE curso; senão é null. \
Não uses a data de início das aulas nem datas de etapas de um edital como data limite de inscrição. \
Não concluas que um curso é gratuito só porque a entidade costuma ter cursos gratuitos: nesse caso escreve \
"Confirmar se é gratuito" nos requisitos. Não juntes dados de turmas ou ofertas diferentes no mesmo curso.

Escreve em LINGUAGEM SIMPLES, para quem lê pouco:
- "titulo": nome curto do curso, sem repetir a entidade nem siglas de programas (ex.: "Auxiliar de cozinha").
- "descricao": 1 ou 2 frases com menos de 20 palavras cada, palavras do dia a dia, sem siglas sem explicação. \
Diz o que se aprende e para que serve. Para cursos no Brasil escreve em português do Brasil; em Portugal, \
em português de Portugal; online, em português neutro. Nunca rotules as pessoas (não escrevas "para \
pessoas vulneráveis", "para pobres"); descreve o curso.
- "exclusivo_para": se o curso só aceita um grupo (ex.: "Só para mulheres", "Dos 18 aos 29 anos", \
"Para quem mora em Fortaleza"), escreve isso de forma respeitosa; senão null.
- "requisitos": o que é preciso para entrar (ex.: "Ter CPF", "Ter 16 anos ou mais", "Ter o ensino fundamental"), ou null.
- "certificado": "gratuito", "pago", "sem certificado" ou "desconhecido".
- "necessidades": ids da lista dada a que o curso responde (um ou mais).
- "perfis": ids da lista interna de perfis a quem o curso serve bem (um ou mais; "todos" se for geral).
- Datas no formato AAAA-MM-DD, ou null se não souberes. Não inventes nada."""

CAMPOS = ["titulo", "entidade", "url", "modalidade", "pais", "regiao", "cidade", "descricao", "exclusivo_para",
          "requisitos", "certificado", "necessidades", "perfis", "inscricoes_ate", "inicio", "duracao"]


def ler_data(valor):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(valor or ""))
    if not m:
        return ""
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return ""


def id_curso(url, titulo):
    return "C-" + hashlib.sha1((url + "|" + titulo.strip().lower()).encode()).hexdigest()[:8]


def pedido_para(tarefa, cfg):
    local = tarefa["local"]
    necessidades = ", ".join(f"{n['id']} ({n['rotulo']})" for n in cfg["necessidades"])
    perfis = ", ".join(cfg["perfis_internos"])
    if local == "online":
        onde = ('Cursos 100% online. "modalidade": "online". "pais": "PT", "BR" ou "Internacional" conforme a '
                'entidade. "regiao" e "cidade": null.')
    elif local == "PT":
        onde = ('Cursos presenciais (ou mistos) em Portugal. "modalidade": "presencial" ou "misto". "pais": "PT". '
                '"regiao": o distrito; "cidade": o concelho ou localidade.')
    else:
        estado = NOMES_LOCAIS.get(local, local)
        onde = (f'Cursos presenciais (ou mistos, ou online só para quem mora no estado) no {estado}, Brasil, '
                f'incluindo cidades do interior. "modalidade": "presencial", "misto" ou "online". "pais": "BR". '
                f'"regiao": "{estado}"; "cidade": o município (ou null se for em todo o estado).')
    return (
        f"Data de hoje: {hoje().isoformat()}.\n\nProcura: {tarefa['pedido']}.\n{onde}\n\n"
        f"Lista de necessidades (ids): {necessidades}.\nLista interna de perfis (ids): {perfis}.\n\n"
        f"Devolve no máximo {cfg['max_por_pesquisa']} cursos, os melhores e mais úteis. "
        "Se não encontrares nenhum que cumpra as regras, devolve uma lista vazia.\n"
        "Não escrevas explicações nem listas de candidatos recusados: responde só com o JSON entre "
        "<json></json>, uma lista de objetos com estes campos:\n" + ", ".join(CAMPOS))


def normalizar(c, tarefa, cfg, dominios):
    if not isinstance(c, dict):
        return None, "formato inválido"
    url = (c.get("url") or "").strip()
    if not url.startswith("http"):
        return None, "sem link"
    if not dominio_permitido(url, dominios):
        return None, f"domínio fora da lista ({url})"
    titulo = (c.get("titulo") or "").strip()
    if not titulo:
        return None, "sem título"
    inscricoes = ler_data(c.get("inscricoes_ate"))
    if inscricoes and inscricoes < hoje_iso():
        return None, "inscrições encerradas"
    ids_nec = {n["id"] for n in cfg["necessidades"]}
    local = tarefa["local"]
    modalidade = c.get("modalidade") if c.get("modalidade") in ("online", "presencial", "misto") else \
        ("online" if local == "online" else "presencial")
    pais = c.get("pais") if c.get("pais") in ("PT", "BR", "Internacional") else \
        ("PT" if local == "PT" else "BR" if local.startswith("BR") else "Internacional")
    return {
        "Título": titulo[:200], "Entidade": (c.get("entidade") or "").strip()[:150], "Link": url,
        "Local": local, "Modalidade": modalidade, "País": pais,
        "Região": c.get("regiao") or "", "Cidade": c.get("cidade") or "",
        "Descrição": (c.get("descricao") or "").strip()[:400],
        "Necessidades": ", ".join(n for n in (c.get("necessidades") or []) if n in ids_nec),
        "Perfis": ", ".join(p for p in (c.get("perfis") or []) if p in cfg["perfis_internos"]) or "todos",
        "Condição de acesso": c.get("exclusivo_para") or "", "Requisitos": c.get("requisitos") or "",
        "Certificado": c.get("certificado") if c.get("certificado") in ("gratuito", "pago", "sem certificado") else "desconhecido",
        "Inscrições até": inscricoes, "Início": ler_data(c.get("inicio")), "Duração": c.get("duracao") or "",
    }, None


def procurar_existente(curso, existentes):
    """Mesmo ID, ou mesmo link com título muito parecido."""
    cid = id_curso(curso["Link"], curso["Título"])
    if cid in existentes["por_id"]:
        return existentes["por_id"][cid]
    for r in existentes["por_link"].get(curso["Link"], []):
        if difflib.SequenceMatcher(None, r["Título"].lower(), curso["Título"].lower()).ratio() >= 0.8:
            return r
    return None


def main():
    base = Base()
    cfg_total = carregar_config(base)
    cfg = cfg_total["cursos"]
    modelo = cfg_total.get("modelo_cursos", "claude-haiku-5-5")
    descoberta = cfg.get("dominios_descoberta", set())

    registos = base.tabela(ABA)
    existentes = {"por_id": {r["ID"]: r for r in registos if r.get("ID")}, "por_link": {}}
    for r in registos:
        existentes["por_link"].setdefault(r.get("Link", ""), []).append(r)

    tarefas = cfg["pesquisas"]
    so = os.environ.get("TAREFAS", "").strip()
    if so:
        tarefas = [t for t in tarefas if t["id"] in so.split(",")]
    print(f"Pesquisas ativas: {', '.join(t['id'] for t in tarefas) or 'nenhuma'}")

    hoje_txt = hoje_iso()
    novos, alteracoes, falhas, custo_total, pesquisas_web = [], [], 0, 0.0, 0
    for t in tarefas:
        dominios = cfg["dominios"].get(t["local"], [])
        if not dominios:
            print(f"\n== {t['id']} == sem sites de confiança para {t['local']}; ignorada")
            continue
        ferramenta = {"type": "web_search_20250305", "name": "web_search",
                      "max_uses": cfg.get("max_pesquisas_web", 4), "allowed_domains": dominios}
        if t["local"] in LOCALIZACAO:
            ferramenta["user_location"] = LOCALIZACAO[t["local"]]
        print(f"\n== {t['id']} ==")
        try:
            texto, uso = claude(modelo, SISTEMA, pedido_para(t, cfg), max_tokens=16000, ferramentas=[ferramenta])
        except ErroClaude as e:
            print(f"  ERRO: {e}")
            falhas += 1
            continue
        custo = custo_estimado(uso, modelo)
        custo_total += custo
        pesquisas_web += uso.get("pesquisas_web", 0)
        lista = extrair_json(texto)
        if not isinstance(lista, list):
            print(f"  Sem JSON válido. Fim da resposta: {texto[-400:]!r}")
            continue
        print(f"  {len(lista)} propostos | {uso.get('pesquisas_web', 0)} pesquisas | custo ≈ {custo} USD")
        for c in lista:
            curso, motivo = normalizar(c, t, cfg, dominios)
            if not curso:
                print(f"  - recusado: {motivo}")
                continue
            antigo = procurar_existente(curso, existentes)
            if antigo:
                if antigo.get("_linha") and antigo.get("Estado") not in ("Oculto", "Expirado"):
                    alteracoes.append((antigo["_linha"], {"Última verificação": hoje_txt}))
                print(f"  = já existe ({antigo.get('Estado')}): {antigo['Título']}")
                continue
            estado_http = verificar_link(curso["Link"])
            if estado_http in (404, 410) or (400 <= estado_http < 500 and estado_http not in (401, 403, 405, 429)):
                print(f"  - recusado: link não abre ({estado_http}) {curso['Link']}")
                continue
            curso["Link verificado"] = "SIM" if 200 <= estado_http < 400 else "NÃO"
            notas = []
            if dominio_permitido(curso["Link"], descoberta):
                notas.append("Link de notícia: procurar a página oficial da inscrição.")
            if curso["Link verificado"] == "NÃO":
                notas.append(f"O link não respondeu à verificação automática ({estado_http}).")
            inicio = str(curso.get("Início") or "")
            if inicio and inicio < hoje_txt and not curso.get("Inscrições até"):
                notas.append(f"A turma começou a {inicio}: confirmar se ainda aceita inscrições.")
            curso.update({
                "ID": id_curso(curso["Link"], curso["Título"]),
                "Estado": "Rever" if notas else "Novo",
                "Primeiro visto": hoje_txt, "Última verificação": hoje_txt, "Origem": "rotina",
                "Notas": " ".join(notas), "Como me inscrever": "", "Nota da verificação": "",
                **VERIFICACAO_INICIAL,
                "O que falta confirmar": "Ainda não verificado na página oficial.",
            })
            novos.append(curso)
            existentes["por_id"][curso["ID"]] = curso
            existentes["por_link"].setdefault(curso["Link"], []).append(curso)
            print(f"  + [{curso['Estado']}] {curso['Título']} — {curso['Entidade']}")

    # expirar: inscrições passadas, ou cursos da rotina que deixaram de aparecer há muito tempo
    corte = (hoje() - datetime.timedelta(days=cfg.get("dias_validade", 60))).isoformat()
    expirados = 0
    for r in registos:
        if r.get("Estado") not in ("Novo", "Publicado", "Rever"):
            continue
        fim = ler_data(r.get("Inscrições até"))
        visto = ler_data(r.get("Última verificação")) or ler_data(r.get("Primeiro visto"))
        if (fim and fim < hoje_txt) or (r.get("Origem") == "rotina" and visto and visto < corte):
            alteracoes.append((r["_linha"], {"Estado": "Expirado"}))
            expirados += 1

    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novos)
    base.guardar()
    print(f"\nResumo: {len(novos)} novos, {expirados} expirados.")
    print(f"Pesquisas web: {pesquisas_web} | custo estimado: {round(custo_total, 3)} USD")
    return 1 if tarefas and falhas == len(tarefas) else 0


if __name__ == "__main__":
    sys.exit(main())
