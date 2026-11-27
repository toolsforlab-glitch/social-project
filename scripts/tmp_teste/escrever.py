"""Temporário (27/11/2026): cria os 7 cursos técnicos EJA-EPT do IFB (ensino médio + técnico, noturno), «Por abrir».
Frases dos editais (PDF) conferidas por código; frases das páginas do IFB conferidas no navegador (o IFB pede CAPTCHA
ao GitHub depois de poucos pedidos; regra T10); gratuidade da EJA na LDB conferida por código aqui."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara

hoje = hoje_ceara()
LDB = "https://legis.senado.gov.br/norma/551270/publicacao/34619663"
F_LDB = "assegurarão gratuitamente aos jovens e aos adultos"
try:
    ldb_ok = citacao_valida(F_LDB, texto_de_html(baixar(LDB, timeout=40)))
except Exception as e:  # noqa: BLE001
    print("LDB não abriu", type(e).__name__); ldb_ok = False
print("LDB:", ldb_ok)

GERAL = "https://www.ifb.edu.br/estude-no-ifb/noticias/49199-conheca-os-cursos-na-modalidade-eja-ept"
GRAT = "https://www.ifb.edu.br/estude-no-ifb/noticias/49034-cursos-tecnicos-integrados-a-educacao-de-jovens-e-adultos-eja-inscricoes-abertas"
F_GRAT = "Os cursos são totalmente gratuitos e as inscrições são presenciais."
F_IDADE = "voltada a pessoas com idade mínima de 18 anos que não concluíram o ensino médio na idade escolar"
SEL = "de fluxo contínuo e encerrará ao momento do preenchimento da turma com a totalidade de matriculados ao número de vagas ofertadas"
D11 = "Inscrições abertas de 11 de dezembro de 2026 a 22 de janeiro de 2027."
A = "https://www.ifb.edu.br/attachments/article/"
C = [
 dict(t="Técnico em Administração integrado ao ensino médio (EJA-EPT) – IFB Campus Gama", cid="Gama",
      pag="https://www.ifb.edu.br/estude-no-ifb/noticias/49010", ed=A+"49010/Edital%2037-2026-Sele%C3%A7%C3%A3o%20EJA-EPT-2027.pdf",
      vagas="80", fv="destina-se à oferta de 80 vagas", dur="2 anos e meio", abre="2026-12-11", fd=D11, sel=SEL,
      onde="no IFB Campus Gama (Lote 01, DF 480, Setor de Múltiplas Atividades, Gama/DF), das 8h às 18h", txt="administração, protocolo, arquivo e controlo de estoques"),
 dict(t="Técnico em Modelagem do Vestuário integrado ao ensino médio (EJA-EPT) – IFB Campus Taguatinga", cid="Taguatinga",
      pag="https://www.ifb.edu.br/gama/49023", ed=A+"49023/Edital%20%C3%9Anico%20para%20Ingresso%20de%20Discentes%20nos%20Cursos%20T%C3%A9cnicos%20de%20EJA-EPT%20do%20IFB%20-%20Sele%C3%A7%C3%A3o%202027%20-%20Taguatinga.pdf",
      vagas="80", fv="destina-se à oferta de 80 vagas", dur="3 anos", abre="2026-12-11", fd=D11, sel=SEL,
      onde="no IFB Campus Taguatinga ou online (veja a página do curso)", txt="modelagem e confecção de roupas"),
 dict(t="Técnico em Edificações integrado ao ensino médio (EJA-EPT) – IFB Campus Samambaia", cid="Samambaia",
      pag="https://www.ifb.edu.br/samambaia/49122-curso-tecnico-em-edificacoes-eja-ept-2027", ed=A+"49122/Edital%2026_2026%20-%20DGSA_RIFB_IFBRASILIA%20%20-Processo%20Seletivo%20para%20PROEJA%20em%20Edifica%C3%A7%C3%B5es%20CSAM.pdf",
      vagas="80", fv="destina-se à oferta de 80 vagas", dur="3 anos", abre="2026-12-21",
      fd="Inscrições abertas de 21 de dezembro de 2026 a 22 de janeiro de 2027.", sel=SEL,
      onde="no IFB Campus Samambaia (Rodovia DF-460, Subcentro Leste, Complexo Boca da Mata, Lote 2) ou online", txt="projetos e orçamentos de obras"),
 dict(t="Técnico em Marketing integrado ao ensino médio (EJA-EPT) – IFB Campus Brasília", cid="Brasília (Asa Norte)",
      pag="https://www.ifb.edu.br/brasilia/49096-inscricoes-abertas-para-o-curso-eja-marketing-2027", ed=A+"49096/Edital%2044.2026%20-%20EJA%20EPT%20T%C3%A9cnico%20em%20Marketing.pdf",
      vagas="40", fv="destina-se à oferta de 40 vagas", dur="2 anos e meio", abre="2026-12-11", fd=D11, sel=SEL,
      onde="no IFB Campus Brasília (SGAN 610, módulos D, E, F e G, Asa Norte)", txt="vendas, comunicação e marketing digital"),
 dict(t="Técnico em Produção de Áudio e Vídeo integrado ao ensino médio (EJA-EPT) – IFB Campus Recanto das Emas", cid="Recanto das Emas",
      pag="https://www.ifb.edu.br/recantodasemas/49052-processo-seletivo-para-ingresso-no-curso-tecnico-em-producao-de-audio-e-video-eja-ept", ed=A+"49052/EDITAL_45_EJA.pdf",
      vagas="160", fv="destina-se à oferta de 160 vagas", dur="2 anos e meio", abre="2026-12-11", fd=D11, sel=SEL,
      onde="no IFB Campus Recanto das Emas (Avenida Monjolo, Chácara 22, Núcleo Rural Monjolo, atrás da quadra 300)", txt="captação de imagem e som e edição"),
 dict(t="Técnico em Secretariado integrado ao ensino médio (EJA-EPT) – IFB Campus São Sebastião", cid="São Sebastião",
      pag="https://www.ifb.edu.br/gama/49019", ed=A+"49019/Edital%2013_2026%20-%20DGSS_RIFB_IFBRASILIA.pdf",
      vagas="40", fv="destina-se à oferta de 40 vagas", dur="3 anos", abre="2026-12-11", fd=D11, sel=SEL,
      onde="no IFB Campus São Sebastião", txt="rotinas de escritório, agendas e documentos"),
 dict(t="Técnico em Meio Ambiente integrado ao ensino médio (EJA-EPT) – IFB Campus Estrutural", cid="Estrutural (SCIA)",
      pag="https://www.ifb.edu.br/campus-estrutural/49081-curso-tecnico-em-meio-ambiente-integrado-ao-ensino-medio-eja", ed=A+"49081/Edital%2011-2026%20-%20DGES-RIFB-IFBRASILIA.pdf",
      vagas="40", fv="Este Processo Seletivo, destina-se à oferta de 40 vagas", dur="2 anos e meio", abre="2027-01-04",
      fd="Inscrições abertas de 4 a 22 de janeiro de 2027, caso o número de inscrições seja inferior às vagas",
      sel="As vagas serão preenchidas conforme ordem de chegada dos candidatos",
      onde="pelo formulário online indicado no edital", txt="gestão ambiental, resíduos e qualidade da água"),
]
base = Base(); carregar_config(base)
ids = {r.get("ID") for r in base.tabela("Cursos")}
novos = []
for c in C:
    ident = id_curso(c["pag"], c["t"])
    if ident in ids:
        print("já existe", ident); continue
    ev = [f"gratuito: «{F_GRAT}» ({GRAT})"] + ([f"gratuito: «{F_LDB}» ({LDB})"] if ldb_ok else []) + [
          f"abertura: «{c['fd']}» ({GERAL})", f"vagas: «{c['sel']}» ({c['ed']})", f"vagas: «{c['fv']}» ({c['ed']})",
          f"idade: «{F_IDADE}» ({GERAL})"]
    falta = ["As inscrições de dezembro são para as vagas de ampla concorrência que sobrarem depois das cotas; "
             "fecham quando a turma enche."]
    if c["cid"] in ("Taguatinga", "Samambaia"):
        falta.append("A página geral do IFB diz que a inscrição é «no IFB Campus Gama»; confirme o local na página do curso.")
    if c["abre"] == "2027-01-04":
        falta.append("Só abre se, depois das cotas, sobrarem vagas.")
    novos.append({"ID": ident, "Estado": "Publicado", "Título": c["t"], "Entidade": "Instituto Federal de Brasília (IFB)",
        "Link": c["pag"], "Página do curso": c["pag"], "Destino do link": "curso", "Local": "BR-DF", "Modalidade": "presencial",
        "País": "BR", "Região": "Distrito Federal", "Cidade": c["cid"],
        "Descrição": (f"Para quem tem 18 anos ou mais e não terminou o ensino médio: estuda o ensino médio junto com um curso "
                      f"técnico ({c['txt']}), à noite, durante {c['dur']}. No fim recebe o diploma do ensino médio e o de técnico."),
        "Origem da descrição": "Resumo", "Necessidades": "escola, profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Ter terminado o ensino fundamental (até ao 9.º ano) e ter pelo menos 18 anos até ao dia da matrícula",
        "Idade mínima": "18", "Turno": "noite", "Certificado": "desconhecido", "Inscrições abrem em": c["abre"],
        "Inscrições até": "2027-01-22", "Início": "", "Duração": c["dur"], "Link verificado": "SIM", "Primeiro visto": hoje,
        "Última verificação": hoje, "Origem": "edital", "Precisa de internet": "Não",
        "Notas": f"{hoje}: criado à mão pelo Claude (cursos EJA-EPT 2027 do IFB; editais lidos por código, páginas no navegador, regra T10).",
        "Como me inscrever": (f"1. A partir de {c['abre'][8:10]}/{c['abre'][5:7]}/{c['abre'][:4]} e até 22/01/2027, faça a inscrição "
                              f"{c['onde']}.\n2. Leve os documentos de matrícula pedidos no edital (Anexo C): identidade, CPF, "
                              f"comprovante de residência e o documento de conclusão do ensino fundamental.\n3. As vagas são "
                              f"preenchidas por ordem, até a turma encher: vá cedo."),
        "Nota da verificação": f"{hoje}: edital lido por código; páginas oficiais do IFB conferidas no navegador.",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Por abrir", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, abertura, vagas, idade", "Mudança a rever": "FALSE",
        "O que falta confirmar": " ".join(falta)})
    print("+", ident, c["t"])
base.acrescentar("Cursos", novos)
base.guardar()
print("criados:", len(novos))
