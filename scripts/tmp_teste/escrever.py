"""Temporário (28/11/2026): EJA da rede estadual do Rio de Janeiro (Matrícula Fácil 2027, 1.ª fase até 04/12/2026).
Frases vistas no navegador pelo Claude a 28/11; conferidas aqui por código quando a página abre a partir do GitHub."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara
hoje = hoje_ceara()
base = Base(); carregar_config(base)
ids = {r.get("ID") for r in base.tabela("Cursos")}


def conferir(url, frases):
    try:
        t = texto_de_html(baixar(url, timeout=40).decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        print("não abriu:", url, repr(e)[:120]); return f"vista no navegador a {hoje}; a página não abriu a partir do GitHub"
    falta = [k for k, v in frases.items() if not citacao_valida(v, t)]
    print(url, "falta:", falta)
    return f"conferida por código a {hoje}" if not falta else f"vista no navegador a {hoje} (por código faltou: {', '.join(falta)})"


CAL = "https://www.matriculafacil.rj.gov.br/Calendario/Index"
RES = "https://www.matriculafacil.rj.gov.br/Resolucao/Index"
HOME = "https://www.matriculafacil.rj.gov.br/"
LDB = "https://legis.senado.gov.br/norma/551270/publicacao/34619663"
Fc = {"data": "Inscrição da 1ª Fase da Matrícula Fácil 2027 www.matriculafacil.rj.gov.br 12/11/2026 a 04/12/2026"}
Fr = {"idade": ("somente poderão ser matriculados no Ensino Fundamental para Jovens e Adultos Presencial os alunos com idade mínima de "
                "15 (quinze) anos completos ou a completar até 31/01/2027 e no Ensino Médio para Jovens e Adultos Presencial os alunos "
                "com idade mínima de 18 (dezoito) anos completos ou a completar até 31/01/2027")}
Fh = {"vagas": "A 1ª FASE NÃO É POR ORDEM DE INSCRIÇÃO."}
Fl = {"gratuito": "assegurarão gratuitamente aos jovens e aos adultos"}
T = "Matrícula 2027 na EJA da rede estadual do Rio de Janeiro (ensino fundamental e médio)"
i = id_curso(HOME, T)
if i not in ids:
    vc, vr, vh, vl = conferir(CAL, Fc), conferir(RES, Fr), conferir(HOME, Fh), conferir(LDB, Fl)
    ev = ([f"{k}: «{x}» ({CAL}; {vc})" for k, x in Fc.items()] + [f"{k}: «{x}» ({RES}; {vr})" for k, x in Fr.items()]
          + [f"{k}: «{x}» ({HOME}; {vh})" for k, x in Fh.items()] + [f"{k}: «{x}» ({LDB}; LDB art. 37, regra F6; {vl})" for k, x in Fl.items()])
    base.acrescentar("Cursos", [{"ID": i, "Estado": "Publicado", "Título": T, "Entidade": "Governo do Estado do Rio de Janeiro – Secretaria de Estado de Educação (Seeduc)",
        "Link": HOME, "Página do curso": HOME, "Destino do link": "curso", "Local": "BR-RJ", "Modalidade": "presencial", "País": "BR",
        "Região": "Rio de Janeiro", "Cidade": "Todo o estado do Rio de Janeiro",
        "Descrição": ("Para jovens e adultos que querem terminar o ensino fundamental (a partir de 15 anos) ou o ensino médio (a partir de "
                      "18 anos) na escola pública estadual do Rio de Janeiro, em 2027. A inscrição é pela internet, no Matrícula Fácil, até "
                      "4 de dezembro de 2026. Não é por ordem de inscrição: o resultado sai a 17 de dezembro e a matrícula confirma-se na "
                      "escola de 18 a 22 de janeiro de 2027."),
        "Origem da descrição": "Resumo", "Necessidades": "escola", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": "Ensino fundamental: 15 anos completos ou a completar até 31/01/2027; ensino médio: 18 anos completos ou a completar até 31/01/2027",
        "Idade mínima": 15, "Certificado": "desconhecido", "Inscrições até": "2026-12-04", "Início": "2027-02-11", "Duração": "",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
        "Notas": f"{hoje}: criado à mão pelo Claude (EJA do Rio de Janeiro). Gratuidade pela LDB (regra F6, rede pública).",
        "Como me inscrever": ("1. Até 04/12/2026, entre no site Matrícula Fácil e clique em «Faça a sua Inscrição».\n"
                              "2. Escolha EJA no ensino fundamental ou no ensino médio e as escolas que prefere.\n"
                              "3. A partir de 17/12/2026, consulte em que escola ficou.\n"
                              "4. De 18 a 22/01/2027 (dias úteis), vá à escola com os documentos para confirmar a matrícula."),
        "Nota da verificação": f"{hoje}: calendário e regras do Matrícula Fácil lidos pelo Claude ({vc}).", **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "data, idade, gratuito, vagas", "Mudança a rever": "FALSE",
        "O que falta confirmar": "As vagas são distribuídas pelos critérios da Seeduc (não por ordem de inscrição); a lista de escolas com EJA está no site."}])
    base.guardar(); print("+", i, T)
