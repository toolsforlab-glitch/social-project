"""Acesso à base de dados no Google Sheets.

Em produção usa a conta de serviço (segredos GOOGLE_CREDENTIALS e FOLHA_ID).
Para testes, com MODO_LOCAL=1, usa a cópia em dados_locais/folha.json.
"""
import datetime
import re
import json
import os

from comum import caminho, config

VERDADE = {"TRUE", "VERDADEIRO", "SIM", "YES", "1", "X", "✓"}
ESTADOS_VISIVEIS = {"Publicado"}


def sim(valor):
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().upper() in VERDADE


def numero(valor, padrao):
    try:
        return int(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        return padrao


def seguro(valor):
    """Evita que texto seja lido como fórmula pela folha."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "@"):
        return "'" + valor
    return valor


def letra(indice):
    s = ""
    indice += 1
    while indice:
        indice, resto = divmod(indice - 1, 26)
        s = chr(65 + resto) + s
    return s


class Base:
    def __init__(self):
        self.local = os.environ.get("MODO_LOCAL") == "1"
        if self.local:
            self.ficheiro = caminho("dados_locais", "folha.json")
            with open(self.ficheiro, encoding="utf-8") as f:
                self.dados = json.load(f)
            print("Base de dados: cópia local (modo de teste)")
            return
        cred = os.environ.get("GOOGLE_CREDENTIALS", "").strip()
        folha = os.environ.get("FOLHA_ID", "").strip()
        if not cred or not folha:
            raise SystemExit("Faltam os segredos GOOGLE_CREDENTIALS e/ou FOLHA_ID.")
        import gspread
        from google.oauth2.service_account import Credentials
        credenciais = Credentials.from_service_account_info(
            json.loads(cred), scopes=["https://www.googleapis.com/auth/spreadsheets"])
        # BackOffHTTPClient: quando o Google responde "demasiados pedidos por minuto" (429), espera e repete
        self.folha = gspread.authorize(credenciais, http_client=gspread.BackOffHTTPClient).open_by_key(folha)
        self._cache = {}
        print("Base de dados: Google Sheets")

    # ---------------------------------------------------------- leitura
    def valores(self, aba):
        if self.local:
            return self.dados.get(aba, [])
        if aba not in self._cache:
            try:
                self._cache[aba] = self.folha.worksheet(aba).get_all_values()
            except Exception:  # noqa: BLE001  (aba inexistente)
                self._cache[aba] = []
        return self._cache[aba]

    def abas(self):
        if self.local:
            return list(self.dados)
        return [w.title for w in self.folha.worksheets()]

    def cabecalho(self, aba):
        v = self.valores(aba)
        return list(v[0]) if v else []

    def tabela(self, aba):
        v = self.valores(aba)
        if not v:
            return []
        cab = v[0]
        registos = []
        for n, linha in enumerate(v[1:], start=2):
            if not any(str(c).strip() for c in linha):
                continue
            r = {cab[j]: (linha[j] if j < len(linha) else "") for j in range(len(cab)) if cab[j]}
            r["_linha"] = n
            registos.append(r)
        return registos

    # ---------------------------------------------------------- escrita
    def acrescentar(self, aba, registos):
        if not registos:
            return
        cab = self.cabecalho(aba)
        linhas = [[seguro(r.get(c, "")) for c in cab] for r in registos]
        if self.local:
            self.dados[aba].extend(linhas)
            return
        # escreve logo a seguir à última linha com conteúdo; linhas só com caixas por marcar (FALSE) contam como vazias
        folha = self.folha.worksheet(aba)
        valores = self.valores(aba)
        ultima = max((n for n, linha in enumerate(valores, start=1)
                      if any(str(c).strip() not in ("", "FALSE") for c in linha)), default=0)
        falta = ultima + len(linhas) - folha.row_count
        if falta > 0:
            folha.add_rows(falta)
        for i in range(0, len(linhas), 200):
            folha.batch_update([{"range": f"A{ultima + 1 + i}", "values": linhas[i:i + 200]}],
                               value_input_option="USER_ENTERED")
        self._cache.pop(aba, None)

    def remover_linhas(self, aba, linhas):
        """Apaga linhas inteiras (números de linha da folha). De baixo para cima, para os números não mudarem."""
        linhas = sorted(set(linhas), reverse=True)
        if not linhas:
            return
        if self.local:
            for n in linhas:
                del self.dados[aba][n - 1]
            return
        folha = self.folha.worksheet(aba)
        for n in linhas:
            folha.delete_rows(n)
        self._cache.pop(aba, None)

    def criar_aba(self, aba, cabecalho):
        if aba in self.abas():
            return
        if self.local:
            self.dados[aba] = [list(cabecalho)]
            return
        folha = self.folha.add_worksheet(title=aba, rows=200, cols=len(cabecalho))
        folha.batch_update([{"range": "A1", "values": [list(cabecalho)]}], value_input_option="USER_ENTERED")
        folha.freeze(rows=1)
        self._cache.pop(aba, None)

    def atualizar(self, aba, alteracoes):
        """alteracoes: lista de (número da linha, {coluna: valor})."""
        alteracoes = [(n, c) for n, c in alteracoes if c]
        if not alteracoes:
            return
        cab = self.cabecalho(aba)
        if self.local:
            for n, campos in alteracoes:
                linha = self.dados[aba][n - 1]
                while len(linha) < len(cab):
                    linha.append("")
                for col, val in campos.items():
                    linha[cab.index(col)] = val
            return
        pedidos = [{"range": f"{letra(cab.index(col))}{n}", "values": [[seguro(val)]]}
                   for n, campos in alteracoes for col, val in campos.items()]
        for i in range(0, len(pedidos), 400):
            self.folha.worksheet(aba).batch_update(pedidos[i:i + 400], value_input_option="USER_ENTERED")
        self._cache.pop(aba, None)

    def guardar(self):
        if self.local:
            with open(self.ficheiro, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=1)



# -------------------------------------------------------------- necessidades («O que você quer aprender?»)
# Lista única para todos os scripts que pedem ao Claude para classificar cursos. Os ids não mudam (estão gravados
# na coluna Necessidades da aba Cursos); o texto no site vem da aba Necessidades. A explicação de cada id vai no
# pedido ao Claude, para não confundir os temas (regra do responsável, 25/11/2026: «Terminar a escola» é só EJA
# e supletivo; as matérias soltas vão para «materias»; «mudar» passou a ser desenvolvimento pessoal e no trabalho).
NECESSIDADES_GUIA = [
    ("digital", "usar o computador, o celular e a internet (informática básica, serviços digitais)"),
    ("tecnologia", "trabalhar com tecnologia (programação, dados, redes, manutenção de computadores)"),
    ("portugues", "aprender português (leitura, escrita, gramática, comunicação)"),
    ("linguas", "aprender outra língua (inglês, espanhol, Libras...)"),
    ("profissao", "aprender uma profissão (curso que prepara para um ofício ou ocupação)"),
    ("mudar", "desenvolvimento pessoal e no trabalho (comportamento, organização, inteligência emocional, carreira)"),
    ("escola", "terminar a escola: SÓ EJA, supletivo ou curso que dá o diploma do ensino fundamental ou médio"),
    ("materias", "estudar matérias da escola (matemática, português, ciências, história, filosofia...) sem dar diploma"),
    ("emprego", "encontrar emprego (currículo, entrevista, preparação para o mercado)"),
    ("negocio", "abrir o próprio negócio (empreendedorismo, vendas, gestão de pequeno negócio)"),
    ("dinheiro", "organizar o dinheiro (finanças pessoais, dívidas, poupança)"),
    ("direitos", "conhecer os direitos (cidadania, direitos trabalhistas, sociais, do consumidor)"),
]
NECESSIDADES = [i for i, _ in NECESSIDADES_GUIA]
EJA = re.compile(r"\b(eja|supletivo|encceja|educa[çc][ãa]o de jovens(?:,)? (?:e )?adultos|eleva[çc][ãa]o de escolaridade|"
                 r"integrad[oa] ao ensino (?:m[ée]dio|fundamental))\b", re.I)


def necessidades_para_claude():
    """Texto da lista de necessidades para os pedidos ao Claude: «id = explicação; …»."""
    return "; ".join(f"{i} = {d}" for i, d in NECESSIDADES_GUIA)

# -------------------------------------------------------------- configuração

def carregar_config(base):
    """Junta a configuração da folha (regras e separador Configuração) aos valores por omissão de config.json."""
    cfg = config()
    conf = {r["Chave"].strip(): r.get("Valor", "") for r in base.tabela("Configuração") if r.get("Chave")}

    cfg["nome"] = conf.get("nome") or cfg.get("nome")
    cfg["nome_provisorio"] = sim(conf.get("nome_provisorio", "SIM"))
    cfg["slogan"] = conf.get("slogan") or cfg.get("slogan")
    cfg["url_site"] = conf.get("url_site") or cfg.get("url_site")
    cfg["links"] = {
        "playlist_ongs": conf.get("link_playlist_ongs", cfg["links"].get("playlist_ongs", "")),
        "canal_whatsapp": conf.get("link_canal_whatsapp", ""),
        "formulario_parceiros": conf.get("link_formulario_parceiros", ""),
    }
    cfg["publicacao_automatica"] = sim(conf.get("publicacao_automatica", "SIM"))
    cfg["territorio_piloto"] = conf.get("territorio_piloto", "").strip()
    cfg["verificar_cursos"] = sim(conf.get("verificar_cursos", "SIM"))
    cfg["modelo_noticias"] = conf.get("modelo_noticias") or cfg.get("modelo_noticias")
    cfg["modelo_cursos"] = conf.get("modelo_cursos") or cfg.get("modelo_cursos")

    n = cfg["noticias"]
    n["max_por_dia"] = numero(conf.get("noticias_max_por_dia"), n["max_por_dia"])
    n["dias_guardados"] = numero(conf.get("noticias_dias_no_site"), n["dias_guardados"])
    n["horas_janela"] = numero(conf.get("noticias_horas_janela"), n["horas_janela"])
    fontes = [{"nome": r["Nome"], "url": r["Link do feed (RSS)"], "idioma": r.get("Idioma") or "en"}
              for r in base.tabela("Fontes de notícias") if sim(r.get("Ativa")) and r.get("Link do feed (RSS)")]
    n["fontes"] = fontes or n["fontes"]
    temas = {r["ID"]: r["Texto no site"] for r in base.tabela("Temas") if sim(r.get("Ativo")) and r.get("ID")}
    n["temas"] = temas or n["temas"]

    c = cfg["cursos"]
    c["max_pesquisas_web"] = numero(conf.get("cursos_max_pesquisas_web"), c["max_pesquisas_web"])
    c["max_por_pesquisa"] = numero(conf.get("cursos_max_por_pesquisa"), c["max_por_pesquisa"])
    c["dias_validade"] = numero(conf.get("cursos_dias_validade"), c["dias_validade"])
    locais = sorted((r for r in base.tabela("Locais") if sim(r.get("Ativo")) and r.get("ID")),
                    key=lambda r: numero(r.get("Ordem"), 99))
    if locais:
        c["locais"] = [{"id": r["ID"], "rotulo": r["Texto no site"]} for r in locais]
    ids_locais = {l["id"] for l in c["locais"]}
    pesquisas = [{"id": r["ID"], "local": r["Local"], "pedido": r["O que procurar"]}
                 for r in base.tabela("Pesquisas de cursos")
                 if sim(r.get("Ativa")) and r.get("ID") and r.get("Local") in ids_locais]
    c["pesquisas"] = pesquisas
    dominios = {}
    for r in base.tabela("Sites de confiança"):
        if sim(r.get("Ativo")) and r.get("Domínio"):
            dominios.setdefault(r["Local"], []).append(r["Domínio"].strip().lower())
            # entidade onde uma pessoa confirmou que todos os cursos são gratuitos (coluna "Tudo gratuito")
            if sim(r.get("Tudo gratuito")):
                c.setdefault("dominios_gratuitos", set()).add(r["Domínio"].strip().lower())
            # entidade onde uma pessoa confirmou que um curso com este botão na página tem inscrições abertas
            # (coluna "Inscrição aberta quando a página mostra"; ex.: Fundação Bradesco, «Quero me matricular»)
            if (r.get("Inscrição aberta quando a página mostra") or "").strip():
                c.setdefault("botao_inscricao", {})[r["Domínio"].strip().lower()] = r["Inscrição aberta quando a página mostra"].strip()
            if "só para descobrir" in (r.get("Notas") or "").lower():
                c.setdefault("dominios_descoberta", set()).add(r["Domínio"].strip().lower())
    c["dominios"] = dominios or c["dominios"]
    nec = sorted((r for r in base.tabela("Necessidades") if sim(r.get("Ativa")) and r.get("ID")),
                 key=lambda r: numero(r.get("Ordem"), 99))
    if nec:
        c["necessidades"] = [{"id": r["ID"], "rotulo": r["Texto no site"]} for r in nec]
    perfis = [r["ID"] for r in base.tabela("Perfis") if sim(r.get("Ativo")) and r.get("ID")]
    c["perfis_internos"] = perfis or c["perfis_internos"]

    s = cfg["semanal"]
    s["max_cursos_whatsapp"] = numero(conf.get("whatsapp_max_cursos"), s["max_cursos_whatsapp"])
    s["max_noticias_newsletter"] = numero(conf.get("newsletter_max_noticias"), s["max_noticias_newsletter"])
    s["newsletter_remetente_nome"] = conf.get("newsletter_remetente_nome") or cfg["nome"]
    s["newsletter_remetente_email"] = conf.get("newsletter_remetente_email", "")
    return cfg


def visivel(estado, cfg):
    estado = (estado or "").strip()
    return estado in ESTADOS_VISIVEIS or (estado == "Novo" and cfg.get("publicacao_automatica", True))


SITUACOES = {"aberto": "Aberto", "encerrado": "Encerrado", "incerto": "Por confirmar"}
HISTORICO = "Histórico de verificações"

# Valores iniciais das colunas de verificação, para cursos acabados de criar
VERIFICACAO_INICIAL = {"Situação das inscrições": "Por confirmar", "Verificar automaticamente": "TRUE",
                       "Falhas seguidas do link": 0, "Impressão da página": "", "Página mudou em": "",
                       "Próxima verificação": "", "Evidência": "", "Campos comprovados": "",
                       "Revisto por pessoa": "", "Mudança a rever": "FALSE", "O que falta confirmar": ""}

# Coluna "Origem da descrição": "Texto da página" (copiado letra a letra da página oficial) ou "Resumo"
# (reescrito em linguagem simples; no site aparece com «Em resumo:»). Um resumo só diz o que se aprende
# com o que a página diz, e para que serve só quando a página o disser (regra do responsável, 20/11/2026).
DESCRICAO_PAGINA, DESCRICAO_RESUMO = "Texto da página", "Resumo"

# Nomes usados na coluna "Campos comprovados"
CAMPOS_PROVA = {"situacao": "situação", "gratuito": "gratuito", "inscricoes_ate": "data", "restricoes": "restrições",
                "idade_minima": "idade", "idade_maxima": "idade máxima", "escolaridade_minima": "escolaridade", "renda_maxima": "renda",
                "prioridade_cadunico": "cadunico", "turnos": "turno", "precisa_internet": "internet",
                "ajuda_custo": "ajuda", "documentos": "documentos", "publico": "público",
                "acessibilidade": "acessibilidade", "conteudo": "conteúdo", "para_que_serve": "para que serve", "programa": "programa",
                "certificado": "certificado", "sob_demanda": "sob demanda"}
# Curso sob demanda (regra do responsável, 21/11/2026): só para cursos CLARAMENTE sob demanda. A página do curso tem
# de o dizer com palavras suas (no seu ritmo, a qualquer momento, sob demanda, acesso imediato, autoinstrucional…);
# um botão "Inscreva-se" sozinho não chega. Nesses cursos não se exige a frase "inscrições abertas", desde que o
# curso não tenha datas de turma ou prazo e a página não diga que encerrou. Exceção: entidades em que uma pessoa
# marcou o botão em Sites de confiança (coluna "Inscrição aberta quando a página mostra", ex.: Fundação Bradesco).
ACAO_SOB_DEMANDA = re.compile(r"no seu (pr[óo]prio )?ritmo|a qualquer (momento|hora)|sob demanda|autoinstrucional|"
                              r"acesso (imediato|livre)|comece (quando|agora|j[áa])|quando (voc[êe] )?quiser|"
                              r"em qualquer hor[áa]rio|inscri[çc][õo]es permanentes|fluxo cont[íi]nuo|"
                              r"pode se inscrever a qualquer|sem data (de|para) (in[íi]cio|come[çc]ar)", re.I)
ENCERRADO = re.compile(r"inscri[çc][õo]es\s+(est[ãa]o\s+)?encerrad|esgotad|curso\s+(foi\s+)?encerrad|"
                       r"n[ãa]o\s+h[áa]\s+vagas|indispon[íi]vel", re.I)

# Acessibilidade para pessoas com deficiência: uma etiqueta só existe quando a frase da fonte nomeia o recurso.
# Um curso DE Libras ou SOBRE acessibilidade não conta (isso é o tema, não um recurso oferecido a quem estuda).
ACESSIBILIDADE = [
    ("Com intérprete de Libras", r"int[ée]rprete|tradutor[a-z]*\W+(?:\w+\W+){0,3}libras|libras\W+(?:\w+\W+){0,3}(?:int[ée]rprete|tradu)"),
    ("Local acessível", r"(?:local|espa[çc]o|ambiente|pr[ée]dio|sala|instala[çc][õo]es|unidade)s?\s+(?:\w+\s+){0,2}acess[íi]ve(?:l|is)"
                        r"|acessibilidade arquitet|\brampas?\b|elevador|cadeirantes?|mobilidade reduzida"),
    ("Material em braile", r"braile|braille"),
    ("Com audiodescrição", r"audiodescri"),
    ("Com legendas", r"legendas?\b|legendad"),
    ("Recursos de acessibilidade", r"tecnologias? assistivas?|leitor(?:es)? de tela|recursos? de acessibilidade|\bledor\b"),
]
NEGACAO_ACESSIBILIDADE = r"\bn[ãa]o\s+(?:h[áa]|tem|possui|oferece|disp[õo]e|conta|garante)|\bsem\s+(?:int[ée]rprete|acessibilidade|legenda)"


def etiquetas_acessibilidade(frase):
    """Etiquetas de acessibilidade que a frase da fonte nomeia, ex.: "Com intérprete de Libras". Frase negativa: nenhuma."""
    t = (frase or "").lower()
    if not t or re.search(NEGACAO_ACESSIBILIDADE, t):
        return []
    return [texto for texto, padrao in ACESSIBILIDADE if re.search(padrao, t)]

# Públicos prioritários: um perfil só fica num curso quando a frase da fonte (que diz para quem é o curso ou para
# quem há vagas reservadas) contém uma destas palavras. É a segunda barreira, por código, contra perfis deduzidos.
PERFIS_PALAVRAS = {
    "mulheres": r"\bmulher",
    "lgbtqia": r"lgbt|\btrans\b|transexua|transg[êe]ner|travesti|n[ãa]o.bin[áa]ri",
    "populacao_negra": r"\bnegr[oa]s?\b|popula[çc][ãa]o negra|\bpret[oa]s\b|\bpard[oa]s\b|afrodescend|igualdade racial",
    "rurais_indigenas_quilombolas": r"ind[íi]gen|quilombol|ribeirinh|\bciganos?\b|comunidades? rura|do campo\b",
    "pessoas_com_deficiencia": r"defici[êe]ncia|\bpcd\b",
    "migrantes_refugiados": r"migrant|imigrant|refugiad|estrangeir",
    "situacao_de_rua": r"situa[çc][ãa]o de rua|sem.abrigo",
    "saida_sistema_prisional": r"egress[oa]s? do sistema|prisional|privad[oa]s? de liberdade|apenad",
    "jovens": r"\bjove(m|ns)\b|primeiro emprego|juventude",
    "50mais": r"\b(50|60) anos ou mais|maiores de (50|60)|a partir d[eo]s? (50|60) anos|acima d[eo]s? (50|60) anos"
              r"|terceira idade|pessoas? idosas?|\bidos[oa]s\b|\b60\+",
    "desempregados": r"desempregad|desocupad",
}


GRUPOS_TEXTO = {"mulheres": "mulheres", "populacao_negra": "pessoas negras",
                "pessoas_com_deficiencia": "pessoas com deficiência", "migrantes_refugiados": "migrantes e refugiados",
                "situacao_de_rua": "pessoas em situação de rua", "saida_sistema_prisional": "egressos do sistema prisional",
                "jovens": "jovens", "50mais": "pessoas com 50 anos ou mais", "desempregados": "pessoas desempregadas"}


def etiqueta_publico(frase):
    """Etiqueta curta para o site a partir da frase da fonte, ex.: "Vagas reservadas para pessoas com deficiência".
    É uma característica do curso (como o horário): só existe quando a fonte o diz, e ninguém tem de dizer quem é."""
    t = (frase or "").lower()
    nomes = []
    for p in perfis_da_frase(frase):
        if p == "lgbtqia":
            nomes.append("pessoas trans e travestis" if "travesti" in t else
                         "pessoas trans" if re.search(r"\btrans\b|transexua|transg", t) else "pessoas LGBTQIA+")
        elif p == "rurais_indigenas_quilombolas":
            nomes += [n for n, padrao in (("indígenas", r"ind[íi]gen"), ("quilombolas", r"quilombol"),
                                          ("ciganos", r"cigan"), ("comunidades rurais", r"rura|do campo|ribeirinh"))
                      if re.search(padrao, t)]
        elif p == "mulheres" and re.search(r"mulher(es)?\s+trans", t) and not re.search(r"mulher(es)?(?!\s+trans)\b", t):
            continue  # "mulheres trans": fica só "pessoas trans"
        elif p == "50mais":
            nomes.append("pessoas com 60 anos ou mais" if re.search(r"\b60\b", t) else
                         "pessoas idosas" if re.search(r"idos|terceira idade", t) else GRUPOS_TEXTO[p])
        else:
            nomes.append(GRUPOS_TEXTO[p])
    if not nomes:
        return ""
    grupos = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]
    if re.search(r"exclusiv|somente|apenas|\bsó\b|unicamente", t):
        return "Só para " + grupos
    if re.search(r"reserv|\bcotas?\b", t):
        return "Vagas reservadas para " + grupos
    if re.search(r"prioridad|prefer[êe]nc|priorit", t):
        return "Prioridade para " + grupos
    return "Para " + grupos


def etiqueta_idade(minima, maxima):
    """Etiqueta para cursos só para uma faixa de idade, a partir das idades comprovadas na fonte."""
    if maxima and maxima <= 29:
        return f"Para jovens de {minima} a {maxima} anos" if minima else f"Para jovens até {maxima} anos"
    if minima and minima >= 60 and not maxima:
        return f"Para pessoas com {minima} anos ou mais"
    return ""


def perfis_da_frase(frase):
    """Perfis que a frase da fonte nomeia (ex.: "vagas reservadas a pessoas com deficiência" → pessoas_com_deficiencia)."""
    t = (frase or "").lower()
    return [p for p, padrao in PERFIS_PALAVRAS.items() if re.search(padrao, t)]
# coluna da folha onde fica cada dado extra (só é escrito se estiver comprovado e a coluna estiver vazia)
COLUNAS_BARREIRAS = {"idade_minima": "Idade mínima", "idade_maxima": "Idade máxima", "escolaridade_minima": "Escolaridade mínima",
                     "renda_maxima": "Renda máxima", "prioridade_cadunico": "Prioridade CadÚnico", "turnos": "Turno",
                     "precisa_internet": "Precisa de internet", "ajuda_custo": "Ajuda de custo ou transporte",
                     "documentos": "Documentos pedidos"}
ESCOLARIDADES = ["Nenhuma", "Saber ler e escrever", "Fundamental incompleto", "Fundamental completo",
                 "Médio incompleto", "Médio completo", "Superior"]


# Gratuidade: só conta uma frase que diga que o curso não tem custo («gratuito», «gratuitamente», «sem custo»,
# «bolsa integral»…). O nome do programa («Programa Senac de Gratuidade») não serve: concluir que o curso é
# gratuito pelo nome é dedução (regra do responsável, 20/11/2026). Sem frase, o site mostra «Gratuidade por confirmar».
_GRATUIDADE = re.compile(r"gratuit|sem\s+(qualquer\s+)?(custo|pagamento|cobran|[ôo]nus|mensalidade|taxa)|custo\s+zero|"
                         r"100\s*%\s*(\(cem\s+por\s+cento\)\s*)?de\s+isen[çc][ãa]o|n[ãa]o\s+(h[áa]|haver[áa]|ser[áa]|tem|possui|ter[áa])\s+"
                         r"(nenhum(a)?\s+|qualquer\s+)?(cobrad|cobran|custo|taxa)", re.I)
# 24/11/2026: «bolsa integral» / «bolsa de estudo 100%» deixou de contar como gratuidade (decisão do responsável:
# bolsa pressupõe concorrência). «Bolsas gratuitas» continua a contar (tem a palavra «gratuitas»).
_GRATUIDADE_NEGADA = re.compile(r"n[ãa]o\s+(é|são|e|sao|será|serão)\s+gratuit", re.I)


# «A inscrição no processo seletivo é gratuita» fala só da inscrição, não do curso (SENAI PE, 23/11/2026)
_SO_INSCRICAO = re.compile(r"inscri", re.I)
_FALA_DO_CURSO = re.compile(r"curso|bolsa|aula|estud|matr[ií]cula|capacita|forma[çc]|qualifica|certificad|oficina|treinament", re.I)


# Cursos cuja entrada exige prova (prova objetiva, vestibular, nota do ENEM, exame de seleção) ficam fora do site
# (decisão do responsável, 23/11/2026). Pertencer a um grupo (renda, CadÚnico, mulheres, LGBTQIA+, migrantes, pessoas
# com deficiência) NÃO é prova e continua a valer como pré-requisito.
_EXIGE_PROVA = re.compile(
    r"prova (?:objetiva|escrita|de conhecimentos?|de sele[çc][ãa]o|classificat[óo]ria|eliminat[óo]ria)|"
    r"\bvestibular|exame de sele[çc][ãa]o|exame classificat[óo]rio|teste seletivo|"
    r"(?:nota|notas|m[ée]dia|pontua[çc][ãa]o|resultado)s? (?:obtidas? )?(?:no|do|nas provas do) ENEM|"
    r"ingresso pelo ENEM|pontos no ENEM|avalia[çc][ãa]o escrita|"
    # 24/11/2026 (regra do responsável): também fica fora o que obriga a disputar a vaga mostrando que se sabe mais:
    # redação, entrevista de nível ou de conhecimento, análise de currículo. Sorteio e ordem de inscrição continuam.
    r"prova de reda[çc][ãa]o|reda[çc][ãa]o (?:eliminat|classificat)|"
    r"entrevista (?:para (?:a )?verifica[çc][ãa]o (?:do|de) n[íi]vel|de n[íi]vel|t[ée]cnica|de conhecimentos?)|"
    r"verifica[çc][ãa]o (?:do|de) n[íi]vel de profici[êe]ncia|teste de nivelamento (?:eliminat|classificat|para ingresso)|"
    r"an[áa]lise (?:de|do) curr[íi]culo|an[áa]lise curricular", re.I)


def exige_prova(texto):
    """A frase do texto que mostra que a entrada no curso exige prova, ou "" (cursos assim ficam fora do site)."""
    m = _EXIGE_PROVA.search(texto or "")
    if not m:
        return ""
    ini = max(0, (texto or "").rfind(".", 0, m.start()) + 1)
    fim = (texto or "").find(".", m.end())
    return re.sub(r"\s+", " ", texto[ini:fim if fim > 0 else m.end() + 120]).strip()[:300]


def gratuidade_explicita(frase):
    """True se a frase diz, com palavras suas, que não há custo (e não o nega). Uma frase que só fala da inscrição
    («a inscrição é gratuita») não prova que o curso é gratuito."""
    frase = frase or ""
    if _SO_INSCRICAO.search(frase) and not _FALA_DO_CURSO.search(frase):
        return False
    return bool(_GRATUIDADE.search(frase)) and not _GRATUIDADE_NEGADA.search(frase)


def frase_de_gratuidade(texto):
    """A primeira frase do texto que diz explicitamente que não há custo, tal como está escrita (ou "")."""
    for frase in re.split(r"(?<=[.;!?])\s+|\n+", texto or ""):
        frase = re.sub(r"\s+", " ", frase).strip()
        if 8 <= len(frase) <= 400 and gratuidade_explicita(frase):
            return frase
    return ""


# Provas encontradas pelo GPT (consultar_gpt.py) e conferidas por código, guardadas na Evidência assim:
#   rótulo: «frase» (link; encontrada pelo GPT, conferida por código)
# ou, para sites que os servidores do GitHub não conseguem abrir (gov.br), conferidas no navegador do responsável:
#   rótulo: «frase» (link; encontrada no navegador (Chrome), conferida por código)
MARCA_GPT = "encontrada pelo GPT, conferida por código"
MARCA_CHATGPT = "encontrada pelo ChatGPT, conferida por código"
MARCA_NAVEGADOR = "encontrada no navegador (Chrome), conferida por código"
_PROVA_GPT = re.compile(r"([\wçãáéíóúâêô ]+): «([^»]*)» \((https?://[^;)\s]+); ([^»|]*?conferida por código)\)")


def provas_do_gpt(evidencia):
    """[(rótulo, frase, link, texto inteiro do item)] das provas do GPT guardadas na Evidência."""
    return [(m.group(1).strip(), m.group(2), m.group(3), m.group(0).strip()) for m in _PROVA_GPT.finditer(evidencia or "")]


def certificado_da_frase(valor, frase):
    """Certificado só com frase que fale de certificado e diga como é: «gratuito» (não há custo), «pago» ou «sem
    certificado». Devolve o valor confirmado pela frase, ou "" (a regra vale para o Claude e para o GPT)."""
    valor, frase = str(valor or "").strip().lower(), frase or ""
    if "certificad" not in frase.lower():
        return ""
    # o certificado tem de ser o que é gratuito: «certificado gratuito», «o certificado é emitido gratuitamente»;
    # «curso gratuito e com certificado» não chega (é o curso que é gratuito)
    if valor == "gratuito" and gratuidade_explicita(frase) and re.search(
            r"certifica\w*(\s+\S+){0,5}?\s+(gratuit|sem\s+(qualquer\s+)?(custo|[ôo]nus|taxa|cobran)|isent|"
            r"n[ãa]o\s+(tem|possui|ter[áa]|h[áa])\s+(nenhum(a)?\s+|qualquer\s+)?(custo|taxa|cobran))", frase, re.I):
        return "gratuito"
    # «Totalmente gratuitos, inclusive o certificado.» (perguntas frequentes da Aprenda Mais, MEC, 24/11/2026)
    if valor == "gratuito" and re.search(r"gratuit\w*,?\s+(?:inclusive|incluindo|at[ée])\s+(?:o\s+)?certificad", frase, re.I):
        return "gratuito"
    # «O certificado é reconhecido e chancelado pela Microsoft e pelo Ministério do Trabalho, sendo gratuito e emitido
    # automaticamente pela plataforma» (FAQ da Escola do Trabalhador 4.0, 24/11/2026): o sujeito de «sendo gratuito»
    # é o certificado, na mesma frase
    if valor == "gratuito" and re.search(r"\bo\s+certificado\b[^.]{0,120}?,\s*sendo\s+gratuit", frase, re.I):
        return "gratuito"
    # «você não paga nada nem para fazer o curso, nem para emitir o certificado» (FAQ da Fundação Bradesco, 22/11/2026)
    if valor == "gratuito" and re.search(r"n[ãa]o\s+(paga|pagar[áa]?|cobra|[ée]\s+cobrad\w*)\s+(nada|nenhum\w*|qualquer)"
                                        r"[^.]{0,80}?certificad", frase, re.I):
        return "gratuito"
    if valor == "pago" and re.search(r"\bpag[oa]\b|taxa|r\$|valor\s+de", frase, re.I):
        return "pago"
    if valor == "sem certificado" and re.search(r"n[ãa]o\s+(h[áa]|emite|oferece|fornece|possui|d[áa]|geram?)\s+"
                                                 r"(direito\s+a\s+)?certificad|sem\s+certificad", frase, re.I):
        return "sem certificado"
    return ""


def gratuidade_comprovada(r):
    """Gratuidade com prova: revista por uma pessoa, entidade marcada «Tudo gratuito» por uma pessoa, ou uma frase
    guardada na Evidência que diz explicitamente que não há custo."""
    if (r.get("Revisto por pessoa") or "").strip():
        return True
    if not comprovado(r, "gratuito"):
        return False
    evidencia = r.get("Evidência") or ""
    if "Tudo gratuito" in evidencia:
        return True
    return any(gratuidade_explicita(f) for f in re.findall(r"«([^»]*)»", evidencia))


def comprovado(r, campo):
    """Um campo conta como comprovado se uma pessoa reviu o curso ou se a verificação guardou prova dele."""
    if (r.get("Revisto por pessoa") or "").strip():
        return True
    return campo in [c.strip() for c in (r.get("Campos comprovados") or "").lower().split(",")]


def _normal(texto):
    texto = (texto or "").lower().replace("\u00a0", " ")
    texto = re.sub(r"[\"'“”‘’«»]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def citacao_valida(citacao, pagina):
    """A citação tem de existir, quase letra a letra, no texto da página. Evita afirmações deduzidas."""
    c = _normal(citacao)
    return len(c) >= 8 and c in _normal(pagina)


def curso_no_site(r, cfg):
    """Um curso aparece se o Estado o permitir, as inscrições não estiverem encerradas e o certificado não for pago.
    Decisão do responsável (24/11/2026): «Ou é grátis ou não é» — um curso gratuito com certificado pago não entra."""
    return (visivel(r.get("Estado"), cfg) and (r.get("Situação das inscrições") or "").strip() != "Encerrado"
            and (r.get("Certificado") or "").strip() != "pago")


def registo_historico(r, tipo, resultado, depois, notas=""):
    """Linha para o separador Histórico de verificações."""
    agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    return {"Data e hora": agora, "ID do curso": r.get("ID", ""), "Título": r.get("Título", ""),
            "Tipo de verificação": tipo, "Resultado": resultado,
            "Situação antes": r.get("Situação das inscrições", ""),
            "Situação depois": depois.get("Situação das inscrições", r.get("Situação das inscrições", "")),
            "Estado antes": r.get("Estado", ""), "Estado depois": depois.get("Estado", r.get("Estado", "")),
            "Notas": notas}


# ---------- Prova a partir do texto bruto das páginas (sem modelo pelo meio) ----------
import html as _html
import unicodedata as _ud


def texto_de_html(bruto):
    """Texto visível de uma página HTML (ou de um PDF, como os editais). Nunca usar resumos de modelos para preencher
    dados."""
    if isinstance(bruto, bytes) and bruto[:4] == b"%PDF":
        import io
        from pypdf import PdfReader
        texto = "\n".join((pagina.extract_text() or "") for pagina in PdfReader(io.BytesIO(bruto)).pages)
        return re.sub(r"\s+", " ", texto).strip()
    if isinstance(bruto, bytes):
        bruto = bruto.decode("utf-8", "replace")
    bruto = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", bruto)
    bruto = re.sub(r"(?s)<[^>]+>", " ", bruto)
    return re.sub(r"\s+", " ", _html.unescape(bruto)).strip()


def _comparavel(texto):
    """Normalização só para comparar: sem acentos, minúsculas, pontuação e espaços uniformes."""
    t = _ud.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not _ud.combining(c)).lower()
    t = t.replace("’", "'").replace("–", "-").replace("—", "-").replace("º", "o")
    t = re.sub(r"\s*([,;:/().\-|])\s*", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def valor_na_fonte(valor, textos, tipo="texto"):
    """True se o valor aparece, tal como está, em pelo menos um dos textos das fontes."""
    if not valor:
        return None
    if tipo in ("telefone", "cep"):
        so_digitos = ["".join(re.findall(r"\d", t)) for t in textos]
        partes = [p for p in re.split(r"/", str(valor)) if re.search(r"\d", p)]
        return all(any("".join(re.findall(r"\d", p)) in d for d in so_digitos) for p in partes)
    alvo = _comparavel(str(valor))
    return any(alvo in _comparavel(t) for t in textos)


def trecho(valor, texto, largura=70):
    """Pequeno excerto do texto da fonte à volta do valor, para a coluna Evidência."""
    a, b = _comparavel(texto), _comparavel(str(valor))
    i = a.find(b)
    if i < 0:
        return ""
    return a[max(0, i - largura): i + len(b) + largura].strip()


def hoje_iso():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


# Aba "Pendências para verificar" (regra do responsável, 22/11/2026): SEMPRE que uma rotina encontra um problema que
# uma pessoa tem de ver (uma fonte que não abre, uma lista oficial vazia, uma página que mudou de endereço), fica uma
# linha nesta aba com o que verificar e os links. Não se repete: se já houver uma linha aberta (Feito por marcar)
# com o mesmo Link 1, só se atualiza "Visto pela última vez".
PENDENCIAS = "Pendências para verificar"


def registar_pendencia(base, problema, verificar, link1, link2="", origem="rotina"):
    hoje = datetime.date.today().isoformat()
    try:
        linhas = base.tabela(PENDENCIAS)
        abertas = [r for r in linhas if not sim(r.get("Feito")) and (r.get("Link 1") or "").strip() == link1]
        livres = [r for r in linhas if not (r.get("Problema") or "").strip()]  # linhas só com a caixa por marcar
        nova = {"Feito": "FALSE", "Aberta em": hoje, "Visto pela última vez": hoje, "Problema": problema[:500],
                "O que verificar": verificar[:500], "Link 1": link1, "Link 2": link2, "Origem": origem, "Notas": ""}
        if abertas:
            base.atualizar(PENDENCIAS, [(abertas[0]["_linha"], {"Visto pela última vez": hoje})])
        elif livres:
            base.atualizar(PENDENCIAS, [(livres[0]["_linha"], nova)])
        else:
            base.acrescentar(PENDENCIAS, [{"Feito": "FALSE", "Aberta em": hoje, "Visto pela última vez": hoje,
                                           "Problema": problema[:500], "O que verificar": verificar[:500],
                                           "Link 1": link1, "Link 2": link2, "Origem": origem, "Notas": ""}])
        print(f"  → pendência registada: {problema[:90]}")
    except Exception as e:  # noqa: BLE001
        print(f"  ! não foi possível registar a pendência ({e})")
