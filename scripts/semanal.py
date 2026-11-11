"""Gera, uma vez por semana, a publicação para o canal de WhatsApp e a newsletter.
Se houver chave do Brevo, envia a newsletter à lista e a publicação de WhatsApp por email ao administrador."""
import datetime
import html
import json
import os
import sys
import urllib.error
import urllib.request

from comum import caminho, config, hoje, ler_json

BREVO = "https://api.brevo.com/v3"


def cursos_da_semana(cfg, dias=7):
    corte = (hoje() - datetime.timedelta(days=dias)).isoformat()
    cursos = ler_json("docs/dados/cursos.json", {"cursos": []})["cursos"]
    novos = [c for c in cursos if c.get("primeiro_visto", "") >= corte]
    # variedade: alterna entre locais
    por_local = {}
    for c in sorted(novos, key=lambda c: (c.get("inscricoes_ate") or "9999")):
        por_local.setdefault(c["local"], []).append(c)
    escolhidos = []
    while len(escolhidos) < cfg["semanal"]["max_cursos_whatsapp"] and any(por_local.values()):
        for local in list(por_local):
            if por_local[local] and len(escolhidos) < cfg["semanal"]["max_cursos_whatsapp"]:
                escolhidos.append(por_local[local].pop(0))
    return escolhidos, len(novos)


def noticias_da_semana(cfg, dias=7):
    corte = (hoje() - datetime.timedelta(days=dias)).isoformat()
    dados = ler_json("docs/dados/noticias.json", {"dias": []})
    escolhidas = []
    for dia in dados["dias"]:
        if dia["data"] < corte:
            continue
        escolhidas.extend(dia["itens"][:2])  # as duas mais importantes de cada dia
    return escolhidas[: cfg["semanal"]["max_noticias_newsletter"]]


def onde(c, locais):
    if c["modalidade"] == "online":
        return "online"
    partes = []
    for x in (c.get("cidade"), c.get("regiao")):
        if x and x not in partes:
            partes.append(x)
    sitio = ", ".join(partes)
    return sitio or locais.get(c["local"], "")


def texto_whatsapp(cfg, cursos, total):
    url = cfg["url_site"].rstrip("/") + "/cursos.html"
    locais = {l["id"]: l["rotulo"] for l in cfg["cursos"]["locais"]}
    if not cursos:
        return ("📚 *Cursos gratuitos*\n\nEsta semana não entraram cursos novos, mas a lista continua disponível:\n"
                f"{url}")
    linhas = ["📚 *Cursos gratuitos desta semana*", ""]
    for c in cursos:
        linhas.append(f"✅ *{c['titulo']}*")
        detalhe = onde(c, locais)
        if c.get("inscricoes_ate"):
            d = c["inscricoes_ate"]
            detalhe += f" · inscrições até {d[8:10]}/{d[5:7]}"
        linhas.append(detalhe)
        if c.get("exclusivo_para"):
            linhas.append(c["exclusivo_para"])
        linhas.append(c["url"])
        linhas.append("")
    if total > len(cursos):
        linhas.append(f"E mais {total - len(cursos)} cursos novos esta semana.")
    linhas.append(f"👉 Veja todos e escolha o que quer aprender: {url}")
    return "\n".join(linhas)


def html_newsletter(cfg, noticias, cursos):
    nome = html.escape(cfg["nome"])
    site = cfg["url_site"].rstrip("/")
    locais = {l["id"]: l["rotulo"] for l in cfg["cursos"]["locais"]}
    partes = [
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:620px;margin:0 auto;color:#1a1f2b;line-height:1.55">',
        f'<div style="background:#1d3f8f;color:#fff;padding:18px 22px;font-size:22px;font-weight:bold">{nome}</div>',
        f'<div style="padding:8px 22px 0"><p style="color:#4a5163">{html.escape(cfg["slogan"])}. '
        f'Resumo da semana de {hoje().strftime("%d/%m/%Y")}.</p>',
    ]
    if noticias:
        partes.append('<h2 style="color:#1d3f8f;font-size:20px;margin:24px 0 8px">Notícias da semana</h2>')
        for n in noticias:
            partes.append(
                f'<p style="margin:0 0 4px"><a href="{html.escape(n["link"])}" style="color:#1d3f8f;font-weight:bold;'
                f'text-decoration:none">{html.escape(n["titulo"])}</a></p>'
                f'<p style="margin:0 0 16px">{html.escape(n["resumo"])} <span style="color:#4a5163">'
                f'({html.escape(n["fonte"])})</span></p>')
    if cursos:
        partes.append('<h2 style="color:#1d3f8f;font-size:20px;margin:24px 0 8px">Cursos gratuitos novos</h2>')
        for c in cursos:
            partes.append(
                f'<p style="margin:0 0 4px"><a href="{html.escape(c["url"])}" style="color:#1d3f8f;font-weight:bold;'
                f'text-decoration:none">{html.escape(c["titulo"])}</a></p>'
                f'<p style="margin:0 0 16px">{html.escape(c.get("descricao") or "")} '
                f'<span style="color:#4a5163">({html.escape(onde(c, locais))})</span></p>')
    partes.append(
        f'<p style="margin-top:24px"><a href="{site}/cursos.html" style="color:#1d3f8f">Ver todos os cursos</a> · '
        f'<a href="{site}/noticias.html" style="color:#1d3f8f">Ver todas as notícias</a> · '
        f'<a href="{html.escape(cfg["links"].get("playlist_ongs", ""))}" style="color:#1d3f8f">Podcasts</a></p>')
    partes.append('<p style="color:#4a5163;font-size:13px;margin-top:28px">Recebe este email porque subscreveu a newsletter. '
                  'Pode cancelar a qualquer momento: {{ unsubscribe }}</p></div></div>')
    return "\n".join(partes)


def brevo(metodo, rota, corpo):
    chave = os.environ.get("BREVO_API_KEY", "").strip()
    req = urllib.request.Request(BREVO + rota, method=metodo, data=json.dumps(corpo).encode("utf-8"), headers={
        "api-key": chave, "content-type": "application/json", "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            texto = r.read().decode("utf-8")
            return json.loads(texto) if texto else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Brevo {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")


def main():
    cfg = config()
    cursos, total = cursos_da_semana(cfg)
    noticias = noticias_da_semana(cfg)
    wa = texto_whatsapp(cfg, cursos, total)
    news = html_newsletter(cfg, noticias, cursos)

    data = hoje().isoformat()
    os.makedirs(caminho("semanal"), exist_ok=True)
    os.makedirs(caminho("docs", "semanal"), exist_ok=True)
    for pasta, sufixo in ((caminho("semanal"), f"{data}-"), (caminho("docs", "semanal"), "")):
        with open(os.path.join(pasta, f"{sufixo}whatsapp.txt"), "w", encoding="utf-8") as f:
            f.write(wa + "\n")
        with open(os.path.join(pasta, f"{sufixo}newsletter.html"), "w", encoding="utf-8") as f:
            f.write(news + "\n")
    print("Publicação para o WhatsApp:\n")
    print(wa)
    print(f"\nNewsletter: {len(noticias)} notícias, {len(cursos)} cursos.")

    if not os.environ.get("BREVO_API_KEY"):
        print("\nBrevo ainda não configurado: nada foi enviado. O texto fica em docs/semanal/whatsapp.txt.")
        return 0
    falhou = 0
    admin = os.environ.get("EMAIL_ADMIN", "").strip()
    remetente = {"name": cfg["semanal"]["newsletter_remetente_nome"] or cfg["nome"],
                 "email": cfg["semanal"]["newsletter_remetente_email"] or admin}
    if admin:
        try:
            brevo("POST", "/smtp/email", {
                "sender": remetente, "to": [{"email": admin}],
                "subject": f"Publicação para o canal de WhatsApp ({hoje().strftime('%d/%m')})",
                "textContent": "Copie o texto abaixo e cole-o no canal de WhatsApp:\n\n" + wa})
            print("Publicação de WhatsApp enviada por email ao administrador.")
        except RuntimeError as e:
            print(f"Falhou o email ao administrador: {e}")
            falhou = 1
    lista = os.environ.get("BREVO_LISTA_ID", "").strip()
    if lista and (noticias or cursos):
        try:
            campanha = brevo("POST", "/emailCampaigns", {
                "name": f"Newsletter {data}", "subject": f"{cfg['nome']}: a semana no setor social",
                "sender": remetente, "htmlContent": news, "recipients": {"listIds": [int(lista)]}})
            brevo("POST", f"/emailCampaigns/{campanha['id']}/sendNow", {})
            print("Newsletter enviada.")
        except (RuntimeError, KeyError, ValueError) as e:
            print(f"Falhou o envio da newsletter: {e}")
            falhou = 1
    return falhou


if __name__ == "__main__":
    sys.exit(main())
