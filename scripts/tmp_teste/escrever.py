"""Temporário (27/11/2026): cria os 8 cursos técnicos EJA EPT 2027.1 do IFMS (Edital 73/2026), inscrições abertas.
O IFMS recusa o GitHub e a VPN: página e edital lidos no Chrome sem VPN (pedido do responsável), frases conferidas
pelo Claude no texto (regra T10); gratuidade da EJA na LDB conferida por código aqui."""
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
PAG = "https://selecao.ifms.edu.br/perfil/estudantes/edital-73-2026-eja-ept-2027-semestre-1-e-2"
ED = "https://selecao.ifms.edu.br/edital/files/edital-73-2026-eja-ept-2027-semestre-1-e-2-edital-73-2026-seletivo-curso-tecnico-integrado-modalidade-eja-ept-2027-retificado-29-10-2026.pdf"
C = [("Administração", "Aquidauana", 40), ("Administração", "Campo Grande", 40), ("Manutenção e Suporte em Informática", "Corumbá", 40),
     ("Manutenção e Suporte em Informática", "Coxim", 40), ("Administração", "Dourados", 40),
     ("Manutenção e Suporte em Informática", "Naviraí", 40), ("Zootecnia", "Nova Andradina", 40), ("Administração", "Paranaíba", 35)]
ev_base = ([f"gratuito: «{F_LDB}» ({LDB})"] if ldb_ok else []) + [
    f"gratuito: «A inscrição neste processo seletivo é gratuita» ({ED})",
    f"data: «Período de inscrições 30/10/2026 a 08/01/2027» ({PAG})",
    f"vagas: «Realização do sorteio eletrônico, para os cursos com número de inscrições homologadas superior ao número de vagas» ({PAG})",
    f"idade: «ter idade mínima de 18 (dezoito anos)» ({ED})",
    f"início: «Previsão de início das aulas 11/02/2027» ({PAG})"]
base = Base(); carregar_config(base)
ids = {r.get("ID") for r in base.tabela("Cursos")}
novos = []
if not ldb_ok:
    print("sem a frase da LDB: nada criado")
    C = []
for curso, cid, vagas in C:
    T = f"Técnico em {curso} integrado ao ensino médio (EJA EPT) – IFMS Campus {cid}"
    ident = id_curso(PAG, T)
    if ident in ids:
        print("já existe", ident); continue
    novos.append({"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Instituto Federal de Mato Grosso do Sul (IFMS)",
        "Link": PAG, "Página do curso": PAG, "Destino do link": "curso", "Local": "BR-MS", "Modalidade": "presencial",
        "País": "BR", "Região": "Mato Grosso do Sul", "Cidade": cid,
        "Descrição": (f"Para quem tem 18 anos ou mais e não terminou o ensino médio: estuda o ensino médio junto com o curso "
                      f"técnico em {curso}, à noite, no IFMS de {cid}. No fim recebe o diploma de técnico, que também vale como "
                      f"ensino médio. São {vagas} vagas; as aulas começam em fevereiro de 2027."),
        "Origem da descrição": "Resumo", "Necessidades": "escola, profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Ter 18 anos até à matrícula e ter terminado (ou estar a terminar) o ensino fundamental",
        "Idade mínima": "18", "Turno": "noite", "Certificado": "desconhecido", "Inscrições até": "2027-01-08",
        "Início": "2027-02-11", "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
        "Origem": "edital", "Precisa de internet": "Não",
        "Notas": f"{hoje}: criado à mão pelo Claude (Edital 73/2026 do IFMS; lido no Chrome sem VPN, regra T10).",
        "Como me inscrever": ("1. Até 08/01/2027, inscreva-se na Central de Seleção do IFMS (selecao.ifms.edu.br, «Página do "
                              "candidato»: faça o cadastro, depois «Inscrições Abertas», Edital 73/2026, e escolha o campus e o "
                              "curso). Sem internet, peça ajuda na Central de Relacionamento (Cerel) do campus.\n2. Se houver mais "
                              "inscritos do que vagas, há sorteio eletrónico a 15/01/2027.\n3. O resultado sai a 21/01/2027; a "
                              "matrícula é de 22 a 26/01/2027."),
        "Nota da verificação": f"{hoje}: página e edital lidos no navegador; frases conferidas no texto.",
        **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev_base)[:1800], "Campos comprovados": "gratuito, data, vagas, idade, início", "Mudança a rever": "FALSE",
        "O que falta confirmar": "O IFMS pode não abrir a turma se houver muito poucos inscritos."})
    print("+", ident, T)
base.acrescentar("Cursos", novos)
base.guardar()
print("criados:", len(novos))
