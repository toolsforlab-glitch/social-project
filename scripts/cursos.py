"""Rotina semanal de cursos gratuitos: o Claude pesquisa só em fontes de confiança, classifica cada curso
e a rotina confirma que o link abre antes de o publicar."""
import datetime
import hashlib
import os
import re
import sys

from comum import (ErroClaude, agora_utc, claude, config, custo_estimado, dominio_permitido,
                   extrair_json, gravar_json, hoje, ler_json, verificar_link)

FICHEIRO = "docs/dados/cursos.json"

LOCALIZACAO = {
    "PT": {"type": "approximate", "country": "PT", "timezone": "Europe/Lisbon"},
    "BR-MA": {"type": "approximate", "country": "BR", "region": "Maranhão", "city": "São Luís", "timezone": "America/Fortaleza"},
    "BR-CE": {"type": "approximate", "country": "BR", "region": "Ceará", "city": "Fortaleza", "timezone": "America/Fortaleza"},
    "BR-AC": {"type": "approximate", "country": "BR", "region": "Acre", "city": "Rio Branco", "timezone": "America/Rio_Branco"},
}

SISTEMA = """Procuras cursos GRATUITOS para pessoas em situação de vulnerabilidade, para um site público \
em português. Pesquisa na web e usa só informação que encontraste nas páginas dos resultados.

Um curso só entra se cumprir TODAS estas regras:
1. É gratuito para quem o frequenta (inscrição e aulas sem custo). Conta como gratuito um programa oficial \
que é gratuito por regra (ex.: formação do IEFP para desempregados, Português Língua de Acolhimento, cursos \
FIC dos institutos federais, Programa Senac de Gratuidade), mesmo que a página não o repita em cada turma.
2. Está disponível agora: inscrições abertas, curso de acesso livre a qualquer momento, ou turma com data futura. \
Exclui cursos com inscrições já encerradas ou de anos anteriores.
3. É de nível iniciante ou não exige formação anterior difícil (indica os requisitos que existirem).
4. É de uma entidade de confiança (organismo público, universidade, instituto federal, Sistema S, ONG reconhecida).
5. O link veio dos resultados da pesquisa e leva a pessoa à inscrição: a página do curso, de um edital/processo \
seletivo, ou a página da oferta da entidade onde se escolhe a turma (ex.: a oferta formativa de um centro do IEFP). \
Não uses notícias genéricas. Se for uma página com várias turmas, o título diz o que é \
(ex.: "Cursos de Português Língua de Acolhimento – IEFP Braga").

Na dúvida sobre um pormenor, inclui o curso e põe null nesse campo, em vez de o excluir.

Para cada curso:
- "descricao": 1 ou 2 frases em linguagem muito simples, que qualquer pessoa entenda. Para cursos no Brasil \
escreve em português do Brasil; em Portugal, em português de Portugal; online, em português neutro. \
Nunca rotules as pessoas (não escrevas "para pessoas vulneráveis", "para pobres", "para prostitutas"); \
descreve o que se aprende e para que serve.
- "exclusivo_para": se o curso só aceita um grupo (ex.: "Só para mulheres", "Dos 18 aos 29 anos", \
"Para pessoas com 50 anos ou mais", "Para migrantes"), escreve isso de forma respeitosa; senão null.
- "requisitos": o que é preciso para entrar (ex.: "Ter CPF", "Ter 16 anos ou mais", "Ter o 9.º ano"), ou null.
- "certificado": "gratuito", "pago", "sem certificado" ou "desconhecido".
- "necessidades": ids da lista dada a que o curso responde (um ou mais).
- "perfis": ids da lista interna de perfis a quem o curso serve bem (um ou mais; "todos" se for geral).
- Datas no formato AAAA-MM-DD, ou null se não souberes. Não inventes nada: se não encontraste, usa null."""

CAMPOS = ["titulo", "entidade", "url", "modalidade", "pais", "regiao", "cidade", "descricao", "exclusivo_para",
          "requisitos", "certificado", "necessidades", "perfis", "inscricoes_ate", "inicio", "duracao"]


def ler_data(valor):
    if not valor or not isinstance(valor, str):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", valor)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


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
        estado = {"BR-MA": "Maranhão", "BR-CE": "Ceará", "BR-AC": "Acre"}[local]
        onde = (f'Cursos presenciais (ou mistos) no estado do {estado}, Brasil, incluindo cidades do interior. '
                f'"modalidade": "presencial" ou "misto". "pais": "BR". "regiao": "{estado}"; "cidade": o município.')
    return (
        f"Data de hoje: {hoje().isoformat()}.\n\nProcura: {tarefa['pedido']}.\n{onde}\n\n"
        f"Lista de necessidades (ids): {necessidades}.\nLista interna de perfis (ids): {perfis}.\n\n"
        f"Devolve no máximo {cfg['max_por_pesquisa']} cursos, os melhores e mais úteis. "
        "Se não encontrares nenhum que cumpra as regras, devolve uma lista vazia.\n"
        "Não escrevas explicações nem listas de candidatos recusados: responde só com o JSON entre "
        "<json></json>, uma lista de objetos com estes campos:\n"
        f"{', '.join(CAMPOS)}")


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
    ids_nec = {n["id"] for n in cfg["necessidades"]}
    necessidades = [n for n in (c.get("necessidades") or []) if n in ids_nec]
    perfis = [p for p in (c.get("perfis") or []) if p in cfg["perfis_internos"]] or ["todos"]
    inscricoes = ler_data(c.get("inscricoes_ate"))
    if inscricoes and inscricoes < hoje().isoformat():
        return None, "inscrições encerradas"
    certificado = c.get("certificado") if c.get("certificado") in ("gratuito", "pago", "sem certificado") else "desconhecido"
    local = tarefa["local"]
    curso = {
        "id": hashlib.sha1(url.encode()).hexdigest()[:10],
        "titulo": titulo[:200], "entidade": (c.get("entidade") or "").strip()[:150], "url": url,
        "local": local,
        "modalidade": c.get("modalidade") if c.get("modalidade") in ("online", "presencial", "misto") else
        ("online" if local == "online" else "presencial"),
        "pais": c.get("pais") if c.get("pais") in ("PT", "BR", "Internacional") else
        ("PT" if local == "PT" else "BR" if local.startswith("BR") else "Internacional"),
        "regiao": c.get("regiao"), "cidade": c.get("cidade"),
        "descricao": (c.get("descricao") or "").strip()[:400],
        "exclusivo_para": c.get("exclusivo_para") or None, "requisitos": c.get("requisitos") or None,
        "certificado": certificado, "necessidades": necessidades, "perfis": perfis,
        "inscricoes_ate": inscricoes, "inicio": ler_data(c.get("inicio")), "duracao": c.get("duracao") or None,
    }
    return curso, None


def main():
    cfg_total = config()
    cfg = cfg_total["cursos"]
    modelo = cfg_total.get("modelo_cursos", "claude-haiku-5-5")
    base = ler_json(FICHEIRO, {"atualizado": None, "cursos": []})
    por_url = {c["url"]: c for c in base["cursos"]}

    tarefas = cfg["pesquisas"]
    so = os.environ.get("TAREFAS", "").strip()
    if so:
        tarefas = [t for t in tarefas if t["id"] in so.split(",")]

    uso_total, custo_total, novos, atualizados, falhas = {}, 0.0, 0, 0, 0
    for t in tarefas:
        dominios = cfg["dominios"][t["local"]]
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
        for k, v in uso.items():
            uso_total[k] = uso_total.get(k, 0) + v
        lista = extrair_json(texto)
        if not isinstance(lista, list):
            print(f"  Sem JSON válido na resposta. Início: {texto[:300]!r}")
            continue
        if not lista:
            print(f"  Lista vazia. Fim da resposta: {texto[-600:]!r}")
        print(f"  {len(lista)} propostos | {uso.get('pesquisas_web', 0)} pesquisas | custo ≈ {custo} USD")
        for c in lista:
            curso, motivo = normalizar(c, t, cfg, dominios)
            if not curso:
                print(f"  - recusado: {motivo}")
                continue
            estado = verificar_link(curso["url"])
            if estado in (404, 410) or (400 <= estado < 500 and estado not in (401, 403, 405, 429)):
                print(f"  - recusado: link não abre ({estado}) {curso['url']}")
                continue
            curso["link_verificado"] = 200 <= estado < 400
            hoje_txt = hoje().isoformat()
            antigo = por_url.get(curso["url"])
            curso["primeiro_visto"] = antigo["primeiro_visto"] if antigo else hoje_txt
            curso["visto_em"] = hoje_txt
            por_url[curso["url"]] = curso
            if antigo:
                atualizados += 1
            else:
                novos += 1
            marca = "" if curso["link_verificado"] else f" (link não confirmado: {estado})"
            print(f"  + {curso['titulo']} — {curso['entidade']}{marca}")

    # limpeza: inscrições passadas ou cursos que deixaram de aparecer há muito tempo
    hoje_txt = hoje().isoformat()
    corte = (hoje() - datetime.timedelta(days=cfg.get("dias_validade", 60))).isoformat()
    antes = len(por_url)
    cursos = [c for c in por_url.values()
              if not (c.get("inscricoes_ate") and c["inscricoes_ate"] < hoje_txt) and c["visto_em"] >= corte]
    removidos = antes - len(cursos)
    cursos.sort(key=lambda c: (c["local"], c["titulo"].lower()))
    gravar_json(FICHEIRO, {"atualizado": agora_utc().isoformat(timespec="minutes"), "cursos": cursos})

    print(f"\nResumo: {novos} novos, {atualizados} atualizados, {removidos} removidos, {len(cursos)} no total.")
    print(f"Pesquisas web: {uso_total.get('pesquisas_web', 0)} | tokens entrada: {uso_total.get('input_tokens', 0)} "
          f"| saída: {uso_total.get('output_tokens', 0)} | custo estimado: {round(custo_total, 3)} USD")
    return 1 if falhas == len(tarefas) else 0


if __name__ == "__main__":
    sys.exit(main())
