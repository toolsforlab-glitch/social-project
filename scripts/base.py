"""Acesso à base de dados no Google Sheets.

Em produção usa a conta de serviço (segredos GOOGLE_CREDENTIALS e FOLHA_ID).
Para testes, com MODO_LOCAL=1, usa a cópia em dados_locais/folha.json.
"""
import datetime
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
        self.folha = gspread.authorize(credenciais).open_by_key(folha)
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
        self.folha.worksheet(aba).append_rows(
            linhas, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS", table_range="A1")
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
                       "Próxima verificação": ""}


def curso_no_site(r, cfg):
    """Um curso aparece se o Estado o permitir e as inscrições não estiverem encerradas."""
    return visivel(r.get("Estado"), cfg) and (r.get("Situação das inscrições") or "").strip() != "Encerrado"


def registo_historico(r, tipo, resultado, depois, notas=""):
    """Linha para o separador Histórico de verificações."""
    agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    return {"Data e hora": agora, "ID do curso": r.get("ID", ""), "Título": r.get("Título", ""),
            "Tipo de verificação": tipo, "Resultado": resultado,
            "Situação antes": r.get("Situação das inscrições", ""),
            "Situação depois": depois.get("Situação das inscrições", r.get("Situação das inscrições", "")),
            "Estado antes": r.get("Estado", ""), "Estado depois": depois.get("Estado", r.get("Estado", "")),
            "Notas": notas}


def hoje_iso():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()
