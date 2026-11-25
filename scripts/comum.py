"""Funções partilhadas pelas rotinas: configuração, ficheiros, Claude e verificação de links."""
import datetime
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL_ANTHROPIC = "https://api.anthropic.com/v1/messages"
AGENTE = "Mozilla/5.0 (compatible; ProjetoSocialBot/1.0; +https://github.com)"


def caminho(*partes):
    return os.path.join(RAIZ, *partes)


def ler_json(rel, padrao):
    p = caminho(rel) if not os.path.isabs(rel) else rel
    if not os.path.exists(p):
        return padrao
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def gravar_json(rel, dados):
    p = caminho(rel) if not os.path.isabs(rel) else rel
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
        f.write("\n")


def config():
    return ler_json("config.json", {})


def hoje():
    return datetime.datetime.now(datetime.timezone.utc).date()


def agora_utc():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------- Claude

class ErroClaude(Exception):
    pass


def _post_claude(corpo, tentativas=5):
    chave = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not chave:
        raise ErroClaude("Falta o segredo ANTHROPIC_API_KEY.")
    dados = json.dumps(corpo).encode("utf-8")
    espera = 10
    for n in range(tentativas):
        req = urllib.request.Request(URL_ANTHROPIC, data=dados, method="POST", headers={
            "x-api-key": chave, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            texto = e.read().decode("utf-8", "replace")[:500]
            if e.code in (429, 500, 502, 503, 529) and n < tentativas - 1:
                print(f"  Claude respondeu {e.code}; nova tentativa em {espera}s")
                time.sleep(espera)
                espera *= 2
                continue
            raise ErroClaude(f"Erro {e.code} da API: {texto}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  Sem resposta da API ({type(e).__name__}); tentativa {n + 1}")
            if n < min(tentativas, 2) - 1:
                time.sleep(espera)
                espera *= 2
                continue
            raise ErroClaude(f"Sem ligação à API: {e}")
    raise ErroClaude("Falhou depois de várias tentativas.")


def somar_uso(total, uso):
    for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        total[k] = total.get(k, 0) + (uso.get(k) or 0)
    pesquisas = (uso.get("server_tool_use") or {}).get("web_search_requests") or 0
    total["pesquisas_web"] = total.get("pesquisas_web", 0) + pesquisas
    return total


# Regra do responsável (21/11/2026): tudo o que as rotinas escrevem para o site e para a folha é em português do
# Brasil. Vai no fim de todas as instruções ao Claude.
IDIOMA = """

IDIOMA: todos os textos que você escrever (descrições, notas, passos de inscrição, resumos, motivos, títulos de \
notícias) devem estar em português do Brasil (pt-BR), com vocabulário, ortografia e construções do Brasil: \
"você", "celular", "contato", "registro", "equipe", "tela", "arquivo", "endereço", "ônibus", "fato", "acessar", \
"compartilhar", "em outra" (não "noutra"), gerúndio ("está fazendo", não "está a fazer"), pronomes antes do verbo \
("se inscrever", "a inscrição se abre") e aspas "assim" (não «assim»). Nunca use formas de Portugal. As frases \
copiadas das páginas oficiais (evidências e citações) ficam exatamente como estão na página.

LINGUAGEM SIMPLES (regra do responsável, 25/11/2026): nos textos que você mesmo escreve (descrições, resumos, \
passos de inscrição), use palavras do dia a dia, para quem estudou pouco. Mas REQUISITOS, condições de acesso, \
renda, idade e escolaridade são copiados exatamente como a fonte os escreve (mesmo com "per capita" ou "2,0"): \
não reescreva nem resuma condições, porque isso pode mudar o sentido. Separe cada condição com ";"."""


def claude(modelo, sistema, pedido, max_tokens=4000, ferramentas=None, max_continuacoes=4, pensar=None):
    """Pede uma resposta ao Claude. Devolve (texto, uso). Trata as pausas longas da pesquisa web."""
    mensagens = [{"role": "user", "content": pedido}]
    sistema = (sistema or "") + IDIOMA
    uso_total = {}
    textos = []
    for _ in range(max_continuacoes + 1):
        corpo = {"model": modelo, "max_tokens": max_tokens, "system": sistema, "messages": mensagens}
        if ferramentas:
            corpo["tools"] = ferramentas
        if pensar is False:
            corpo["thinking"] = {"type": "disabled"}  # extração de tabelas longas: o raciocínio gastava o limite
        try:
            resp = _post_claude(corpo)
        except ErroClaude as ex:
            # alguns modelos desligam o raciocínio com outro valor (a própria API diz qual)
            if pensar is False and "between_tools" in str(ex):
                corpo["thinking"] = {"type": "between_tools"}
                resp = _post_claude(corpo)
            else:
                raise
        depurar(f"resposta-{int(time.time() * 1000)}.json", resp)
        somar_uso(uso_total, resp.get("usage") or {})
        conteudo = resp.get("content") or []
        textos.append("".join(b.get("text", "") for b in conteudo if b.get("type") == "text"))
        if resp.get("stop_reason") == "pause_turn":
            mensagens.append({"role": "assistant", "content": conteudo})
            continue
        break
    return "".join(textos), uso_total


def extrair_json(texto):
    """Encontra o JSON dentro de <json>...</json>, de um bloco ``` ou o primeiro [..]/{..}."""
    m = re.search(r"<json>\s*(.*?)\s*</json>", texto, re.S)
    candidato = m.group(1) if m else None
    if candidato is None:
        m = re.search(r"```(?:json)?\s*(.*?)```", texto, re.S)
        candidato = m.group(1) if m else None
    if candidato is None:
        inicio = min([i for i in (texto.find("["), texto.find("{")) if i >= 0], default=-1)
        if inicio < 0:
            return None
        candidato = texto[inicio:]
    candidato = candidato.strip()
    for fim in range(len(candidato), 0, -1):
        if candidato[fim - 1] in "]}":
            try:
                return json.loads(candidato[:fim])
            except json.JSONDecodeError:
                continue
    return None


def depurar(nome, conteudo):
    if os.environ.get("DEPURAR") == "1":
        os.makedirs(caminho("logs"), exist_ok=True)
        with open(caminho("logs", nome), "w", encoding="utf-8") as f:
            f.write(conteudo if isinstance(conteudo, str) else json.dumps(conteudo, ensure_ascii=False, indent=1))


def custo_estimado(uso, modelo):
    precos = config().get("precos_por_milhao_tokens", {}).get(modelo, [3, 15])
    entrada = (uso.get("input_tokens", 0) + uso.get("cache_creation_input_tokens", 0)) * precos[0] / 1e6
    entrada += uso.get("cache_read_input_tokens", 0) * precos[0] * 0.1 / 1e6
    saida = uso.get("output_tokens", 0) * precos[1] / 1e6
    web = uso.get("pesquisas_web", 0) * 10 / 1000
    return round(entrada + saida + web, 4)


# ---------------------------------------------------------------- Links

def verificar_link(url, timeout=25):
    """Devolve o código HTTP final (0 se não respondeu)."""
    for metodo in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=metodo, headers={
            "User-Agent": AGENTE, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "pt-PT,pt-BR;q=0.9,pt;q=0.8,en;q=0.5"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if metodo == "HEAD" and e.code in (403, 404, 405, 501):
                continue
            return e.code
        except Exception:
            if metodo == "HEAD":
                continue
            return 0
    return 0


_CONTEXTOS = {}


def _contexto_com_intermedio(host):
    """Alguns sites (ex.: fiema.org.br) não enviam o certificado intermédio. Em vez de desligar a verificação,
    vai-se buscar o intermédio ao endereço que o próprio certificado indica (AIA) e verifica-se com ele."""
    if host in _CONTEXTOS:
        return _CONTEXTOS[host]
    import ssl
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID
    folha = x509.load_pem_x509_certificate(ssl.get_server_certificate((host, 443), timeout=20).encode())
    aia = folha.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    urls = [d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS]
    dados = urllib.request.urlopen(urls[0], timeout=20).read()
    try:
        intermedio = x509.load_der_x509_certificate(dados)
    except ValueError:
        intermedio = x509.load_pem_x509_certificate(dados)
    contexto = ssl.create_default_context()
    contexto.load_verify_locations(cadata=intermedio.public_bytes(Encoding.PEM).decode())
    _CONTEXTOS[host] = contexto
    return contexto


def baixar(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        contexto = _contexto_com_intermedio(urllib.parse.urlparse(url).hostname)
        with urllib.request.urlopen(req, timeout=timeout, context=contexto) as r:
            return r.read()


def baixar_final(url, timeout=30):
    """Como baixar(), mas devolve também o endereço onde se chegou depois dos redirecionamentos
    (ex.: um link de inscrição que, sem sessão iniciada, vai parar à página de acesso)."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.geturl()
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        contexto = _contexto_com_intermedio(urllib.parse.urlparse(url).hostname)
        with urllib.request.urlopen(req, timeout=timeout, context=contexto) as r:
            return r.read(), r.geturl()


def dominio_permitido(url, dominios):
    m = re.match(r"https?://([^/:?#]+)", url or "")
    if not m:
        return False
    host = m.group(1).lower()
    return any(host == d or host.endswith("." + d) for d in dominios)
