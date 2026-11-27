"""Temporário (27/11/2026): Acredita no Primeiro Passo – Qualifica Piauí (Edital 29/2026 – FADEX). A FADEX recusa o GitHub
(405): as frases foram conferidas no navegador do responsável (regra T10), no texto do próprio PDF."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config
from cursos import id_curso
from turmas import hoje_ceara

P = "https://www.fadex.org.br/editais/29-2026-edital-de-selecao-de-participantes-para-o-programa-acredita-no-primeiro-passo-qualifica-piaui"
E = "https://www.fadex.org.br/api/arquivos/publico/editais/antigos/88f8ead18afd21344d8247b62bbb7c074c670dbd98906db487874c068f4d0b5c.pdf"
TITULO = "Acredita no Primeiro Passo – Qualifica Piauí: 8 cursos de qualificação profissional para quem está no CadÚnico"
F = {"data": "As inscrições serão gratuitas e contínuas, permanecendo abertas enquanto houver vagas disponíveis",
     "pagina": "Recebimento contínuo Em andamento A partir de 22/10/2026",
     "vagas": "as inscrições deferidas até a data de fechamento do ciclo serão classificadas pela ordem cronológica de inscrição",
     "certificado": "os(as) participantes receberão gratuitamente, durante os cursos:",
     "certificado2": "Certificado de conclusão, observados os critérios do item 6.1.",
     "idade": "Ter idade entre 16 (dezesseis) e 65 (sessenta e cinco) anos na data da inscrição",
     "público": "Estar regularmente inscrito(a) no CadÚnico, com cadastro ativo no momento da inscrição",
     "presencial": "As ações do Programa ocorrerão em formato presencial"}
hoje = hoje_ceara()
base = Base(); carregar_config(base)
ident = id_curso(P, TITULO)
if any(r.get("ID") == ident for r in base.tabela("Cursos")):
    print("já existe", ident); sys.exit(0)
ev = [f"data: «{F['data']}» ({E})", f"data: «{F['pagina']}» ({P})", f"vagas: «{F['vagas']}» ({E})",
      f"certificado: «{F['certificado']} […] {F['certificado2']}» ({E})", f"idade: «{F['idade']}» ({E})",
      f"público: «{F['público']}» ({E})", f"modalidade: «{F['presencial']}» ({E})"]
base.acrescentar("Cursos", [{
    "ID": ident, "Estado": "Publicado", "Título": TITULO,
    "Entidade": "Governo do Piauí (SETRE) e FADEX – Programa Acredita no Primeiro Passo",
    "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-PI", "Modalidade": "presencial",
    "País": "BR", "Região": "Piauí", "Cidade": "",
    "Descrição": ("Cursos presenciais de qualificação profissional para quem está no CadÚnico, em cerca de 30 cidades do Piauí, "
                  "entre elas Teresina, Parnaíba, Picos, Floriano, Campo Maior e São Raimundo Nonato. Cursos: Saúde Digital, "
                  "Cuidador Social, Agente Social, Salgadeiro, Instalador de Painéis de Energia Solar, Confeiteiro, Panificação "
                  "e Maquiagem. Quem participa recebe kit, apostila, uniforme, lanche em cada encontro e certificado."),
    "Origem da descrição": "Resumo", "Necessidades": "profissao, emprego, renda", "Perfis": "todos",
    "Condição de acesso": "Estar no CadÚnico e morar numa das cidades do programa",
    "Requisitos": "\n".join([F["idade"], F["público"],
                             "Residir em um dos municípios contemplados pelo Programa, relacionados no item 3.2"]),
    "Idade mínima": "16", "Idade máxima": "65", "Prioridade CadÚnico": "Sim",
    "Certificado": "gratuito", "Inscrições até": "", "Início": "", "Duração": "", "Link verificado": "SIM",
    "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "edital", "Precisa de internet": "Sim",
    "Notas": (f"{hoje}: criado à mão pelo Claude a partir do Edital nº 29/2026 – FADEX (pista da auditoria do ChatGPT); "
              "frases conferidas no navegador do responsável, porque a FADEX recusa o GitHub (regra T10)."),
    "Como me inscrever": ("1. Preencha o formulário de inscrição indicado no edital (acredita-inscricoes.vercel.app). As inscrições "
                          "ficam abertas enquanto houver vagas.\n2. Escolha o curso; pode escolher mais de um, se os horários "
                          "não coincidirem.\n3. A cada turma formada, as inscrições são analisadas e classificadas por ordem de "
                          "inscrição. Os resultados saem no site da FADEX (fadex.org.br) e da SETRE."),
    "Nota da verificação": f"{hoje}: edital lido no navegador (texto do PDF); frases conferidas.",
    **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
    "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "data, vagas, idade, certificado", "Mudança a rever": "FALSE",
    "O que falta confirmar": ("O edital não diz com estas palavras que o curso é gratuito: diz que são gratuitos a inscrição, o "
                              "kit, a apostila, o uniforme, o lanche e o certificado. As turmas de cada cidade, com local, datas "
                              "e horários, ainda vão ser divulgadas."),
}])
base.guardar()
print("criado", ident)
