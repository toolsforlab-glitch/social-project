"""Uma vez por semana: publicação para o canal de WhatsApp, cartaz em PDF com QR code e newsletter.
Se houver chave do Brevo, envia a newsletter e manda a publicação de WhatsApp por email ao administrador.
Lê os dados já exportados para docs/dados pelo construir_site.py."""
import datetime
import html
import json
import os
import sys
import urllib.error
import urllib.request

from base import Base, carregar_config, hoje_iso
from comum import caminho, hoje, ler_json

BREVO = "https://api.brevo.com/v3"
NOMES = {"BR-CE": "Ceará", "BR-MA": "Maranhão", "BR-AC": "Acre", "PT": "Portugal"}


def data_curta(iso):
    return f"{iso[8:10]}/{iso[5:7]}" if iso and len(iso) >= 10 else ""


def onde(c):
    if c.get("modalidade") == "online":
        return "on-line"
    partes = []
    for x in (c.get("cidade"), c.get("regiao")):
        if x and x not in partes:
            partes.append(x)
    return ", ".join(partes)


def selecionar_cursos(cfg, dias=7):
    cursos = ler_json("docs/dados/cursos.json", {"cursos": []})["cursos"]
    hoje_txt = hoje_iso()
    corte = (hoje() - datetime.timedelta(days=dias)).isoformat()
    limite = (hoje() + datetime.timedelta(days=7)).isoformat()
    piloto = cfg.get("territorio_piloto", "")
    ultimos = sorted((c for c in cursos if c.get("inscricoes_ate") and hoje_txt <= c["inscricoes_ate"] <= limite),
                     key=lambda c: c["inscricoes_ate"])
    novos = [c for c in cursos if c.get("primeiro_visto", "") >= corte and c not in ultimos]
    # presenciais do território primeiro, depois on-line
    novos.sort(key=lambda c: (c.get("local") != piloto, c.get("inscricoes_ate") or "9999"))
    return ultimos, novos, len(cursos)


def texto_whatsapp(cfg, ultimos, novos):
    piloto = NOMES.get(cfg.get("territorio_piloto", ""), "")
    url = cfg["url_site"].rstrip("/") + "/cursos.html"
    maximo = cfg["semanal"]["max_cursos_whatsapp"]
    linhas = [f"📚 *Cursos gratuitos{(' no ' + piloto) if piloto else ''}*", ""]

    def bloco(c):
        detalhe = onde(c)
        if c.get("inscricoes_ate"):
            detalhe += f" · inscrições até {data_curta(c['inscricoes_ate'])}"
        out = [f"✅ *{c['titulo']}*", detalhe]
        if c.get("exclusivo_para"):
            out.append(c["exclusivo_para"])
        out += [c["url"], ""]
        return out

    if ultimos:
        linhas += ["⏰ *Últimos dias para se inscrever*", ""]
        for c in ultimos[:3]:
            linhas += bloco(c)
    restantes = maximo - min(len(ultimos), 3)
    if novos and restantes > 0:
        linhas += ["🆕 *Novos esta semana*", ""]
        for c in novos[:restantes]:
            linhas += bloco(c)
    if not ultimos and not novos:
        linhas += ["Esta semana não entraram cursos novos, mas a lista continua disponível.", ""]
    linhas.append(f"👉 Veja todos e escolha o que você quer aprender: {url}")
    linhas.append("Compartilhe com quem precisa 💙")
    return "\n".join(linhas)


def cartaz_pdf(cfg, ultimos, novos, destino):
    """Cartaz A4 para imprimir: até 6 cursos e um QR code para o canal ou para a página de cursos."""
    import qrcode
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    anil = HexColor("#1d3f8f")
    piloto = NOMES.get(cfg.get("territorio_piloto", ""), "")
    alvo = cfg["links"].get("canal_whatsapp") or (
        cfg["url_site"].rstrip("/") + "/cursos.html" + (f"?onde={cfg['territorio_piloto']}" if piloto else ""))
    vistos, lista = set(), []
    for c in ultimos[:3] + [c for c in novos if c.get("modalidade") != "online"] + novos:
        if c["id"] not in vistos and len(lista) < 6:
            vistos.add(c["id"])
            lista.append(c)

    w, h = A4
    pdf = canvas.Canvas(destino, pagesize=A4)
    pdf.setFillColor(anil)
    pdf.rect(0, h - 120, w, 120, stroke=0, fill=1)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawString(40, h - 70, "Cursos gratuitos")
    pdf.setFont("Helvetica", 18)
    pdf.drawString(40, h - 100, f"{('no ' + piloto + ', ') if piloto else ''}com inscrições abertas")

    from reportlab.lib.utils import simpleSplit
    y = h - 165
    pdf.setFillColor(HexColor("#1a1f2b"))
    for c in lista:
        linhas = simpleSplit(c["titulo"], "Helvetica-Bold", 17, w - 100)[:2]
        if y - 22 * len(linhas) - 20 < 240:
            break
        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawString(40, y, "•")
        for i, linha in enumerate(linhas):
            pdf.drawString(58, y - 21 * i, linha)
        y -= 21 * (len(linhas) - 1)
        detalhe = onde(c) or ""
        if c.get("inscricoes_ate"):
            detalhe += f"  ·  inscrições até {data_curta(c['inscricoes_ate'])}"
        pdf.setFont("Helvetica", 13)
        pdf.drawString(58, y - 19, detalhe[:80])
        y -= 52
    if not lista:
        pdf.setFont("Helvetica", 16)
        pdf.drawString(40, y, "Veja a lista atualizada toda semana no link abaixo.")

    caminho_qr = destino + ".qr.png"
    qrcode.make(alvo, box_size=10, border=2).save(caminho_qr)
    pdf.drawImage(ImageReader(caminho_qr), w - 210, 50, 170, 170)
    os.remove(caminho_qr)
    pdf.setFillColor(anil)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, 170, "Aponte a câmera do celular")
    pdf.drawString(40, 146, "para ver todos os cursos")
    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(HexColor("#4a5163"))
    pdf.drawString(40, 115, "e saber como se inscrever. É grátis.")
    pdf.drawString(40, 60, f"{cfg['nome']} · atualizado em {hoje().strftime('%d/%m/%Y')}")
    pdf.showPage()
    pdf.save()


def noticias_da_semana(cfg, dias=7):
    corte = (hoje() - datetime.timedelta(days=dias)).isoformat()
    escolhidas = []
    for dia in ler_json("docs/dados/noticias.json", {"dias": []})["dias"]:
        if dia["data"] >= corte:
            escolhidas.extend(dia["itens"][:2])
    return escolhidas[: cfg["semanal"]["max_noticias_newsletter"]]


def html_newsletter(cfg, noticias, cursos):
    nome = html.escape(cfg["nome"])
    site = cfg["url_site"].rstrip("/")
    partes = [
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:620px;margin:0 auto;color:#1a1f2b;line-height:1.55">',
        f'<div style="background:#1d3f8f;color:#fff;padding:18px 22px;font-size:22px;font-weight:bold">{nome}</div>',
        f'<div style="padding:8px 22px 0"><p style="color:#4a5163">Resumo da semana de {hoje().strftime("%d/%m/%Y")}.</p>',
    ]
    if cursos:
        partes.append('<h2 style="color:#1d3f8f;font-size:20px;margin:24px 0 8px">Cursos gratuitos para compartilhar</h2>')
        for c in cursos:
            partes.append(
                f'<p style="margin:0 0 4px"><a href="{html.escape(c["url"])}" style="color:#1d3f8f;font-weight:bold;'
                f'text-decoration:none">{html.escape(c["titulo"])}</a></p>'
                f'<p style="margin:0 0 16px">{html.escape(c.get("descricao") or "")} '
                f'<span style="color:#4a5163">({html.escape(onde(c))})</span></p>')
    if noticias:
        partes.append('<h2 style="color:#1d3f8f;font-size:20px;margin:24px 0 8px">Notícias do setor social</h2>')
        for n in noticias:
            partes.append(
                f'<p style="margin:0 0 4px"><a href="{html.escape(n["link"])}" style="color:#1d3f8f;font-weight:bold;'
                f'text-decoration:none">{html.escape(n["titulo"])}</a></p>'
                f'<p style="margin:0 0 16px">{html.escape(n["resumo"])} <span style="color:#4a5163">'
                f'({html.escape(n["fonte"])})</span></p>')
    partes.append(f'<p style="margin-top:24px"><a href="{site}/cursos.html" style="color:#1d3f8f">Ver todos os cursos</a> · '
                  f'<a href="{site}/semanal/cartaz.pdf" style="color:#1d3f8f">Baixar o cartaz da semana</a></p>')
    partes.append('<p style="color:#4a5163;font-size:13px;margin-top:28px">Você recebe este e-mail porque se inscreveu. '
                  'Pode cancelar quando quiser: {{ unsubscribe }}</p></div></div>')
    return "\n".join(partes)


def brevo(metodo, rota, corpo):
    req = urllib.request.Request(BREVO + rota, method=metodo, data=json.dumps(corpo).encode("utf-8"), headers={
        "api-key": os.environ.get("BREVO_API_KEY", "").strip(), "content-type": "application/json",
        "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            texto = r.read().decode("utf-8")
            return json.loads(texto) if texto else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Brevo {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")


def main():
    base = Base()
    cfg = carregar_config(base)
    ultimos, novos, total = selecionar_cursos(cfg)
    wa = texto_whatsapp(cfg, ultimos, novos)
    noticias = noticias_da_semana(cfg)
    news = html_newsletter(cfg, noticias, (ultimos + novos)[:8])

    data = hoje_iso()
    os.makedirs(caminho("semanal"), exist_ok=True)
    os.makedirs(caminho("docs", "semanal"), exist_ok=True)
    for pasta, prefixo in ((caminho("semanal"), f"{data}-"), (caminho("docs", "semanal"), "")):
        with open(os.path.join(pasta, f"{prefixo}whatsapp.txt"), "w", encoding="utf-8") as f:
            f.write(wa + "\n")
        with open(os.path.join(pasta, f"{prefixo}newsletter.html"), "w", encoding="utf-8") as f:
            f.write(news + "\n")
    cartaz_pdf(cfg, ultimos, novos, caminho("docs", "semanal", "cartaz.pdf"))
    print("Publicação para o WhatsApp:\n")
    print(wa)
    print(f"\nCartaz: docs/semanal/cartaz.pdf | newsletter: {len(noticias)} notícias, {len(ultimos + novos)} cursos")

    semana = (hoje() - datetime.timedelta(days=hoje().weekday())).isoformat()
    if semana not in {r.get("Semana (segunda-feira)") for r in base.tabela("Métricas")}:
        base.acrescentar("Métricas", [{"Semana (segunda-feira)": semana, "Cursos novos": len(novos) + len(ultimos),
                                       "Notas": f"{total} cursos visíveis no site"}])
    base.guardar()

    if not os.environ.get("BREVO_API_KEY"):
        print("Brevo ainda não configurado: nada foi enviado. O texto fica em docs/semanal/whatsapp.txt.")
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
                "textContent": "Copie o texto abaixo e cole-o no canal de WhatsApp:\n\n" + wa +
                               f"\n\nCartaz para imprimir: {cfg['url_site'].rstrip('/')}/semanal/cartaz.pdf"})
            print("Publicação de WhatsApp enviada por email ao administrador.")
        except RuntimeError as e:
            print(f"Falhou o email ao administrador: {e}")
            falhou = 1
    lista = os.environ.get("BREVO_LISTA_ID", "").strip()
    if lista and (noticias or ultimos or novos):
        try:
            campanha = brevo("POST", "/emailCampaigns", {
                "name": f"Newsletter {data}", "subject": f"{cfg['nome']}: cursos gratuitos e notícias da semana",
                "sender": remetente, "htmlContent": news, "recipients": {"listIds": [int(lista)]}})
            brevo("POST", f"/emailCampaigns/{campanha['id']}/sendNow", {})
            print("Newsletter enviada.")
        except (RuntimeError, KeyError, ValueError) as e:
            print(f"Falhou o envio da newsletter: {e}")
            falhou = 1
    return falhou


if __name__ == "__main__":
    sys.exit(main())
