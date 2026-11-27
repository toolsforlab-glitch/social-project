"""Temporário (27/11/2026): regra I8 — vagas remanescentes dos técnicos integrados ao ensino médio do IFMT (Edital
205/2026, sorteio), como curso geral (M8): a lista de cursos por campus fica em seletivo.ifmt.edu.br, que não abre daqui."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara

hoje = hoje_ceara()
P = "https://ifmt.edu.br/blog/ingresso-2027-1-lancado-edital-com-196-vagas-para-cursos-tecnicos-integrados-em-10-campi-do-ifmt/"
SOBRE = "https://ifmt.edu.br/estude-no-ifmt/sobre/"
F = {"data": "no período de 23 de novembro a 08 de dezembro de 2026 estão abertas as inscrições para o processo seletivo de vagas remanescentes dos cursos presenciais Técnicos Integrados ao Ensino Médio do IFMT para 2027/1",
     "vagas": "Caso haja mais inscritos do que o número de vagas, a seleção dos candidatos será realizada por meio de Sorteio Público",
     "requisito": "ter concluído o ensino fundamental ou equivalente até a data da matrícula"}
FS = {"gratuito": "Sim, todos os nossos cursos de nível médio, graduação e pós-graduação lato e stricto sensu são gratuitos."}
t = texto_de_html(baixar(P, timeout=40)); ts = texto_de_html(baixar(SOBRE, timeout=40))
ok = all(citacao_valida(v, t) for v in F.values()) and citacao_valida(FS["gratuito"], ts)
print("frases:", ok, {k: citacao_valida(v, t) for k, v in F.items()})
if ok:
    base = Base(); carregar_config(base)
    T = "Cursos técnicos integrados ao ensino médio – vagas que sobraram (IFMT, 10 campi, sorteio)"
    ident = id_curso(P, T)
    if ident not in {r.get("ID") for r in base.tabela("Cursos")}:
        ev = [f"gratuito: «{FS['gratuito']}» ({SOBRE})"] + [f"{k}: «{v}» ({P})" for k, v in F.items()]
        base.acrescentar("Cursos", [{"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Instituto Federal de Mato Grosso (IFMT)",
            "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-MT", "Modalidade": "presencial", "País": "BR",
            "Região": "Mato Grosso",
            "Cidade": "Alta Floresta, Barra do Garças, Cáceres, Canarana, Cuiabá, Pontes e Lacerda, Rondonópolis, São Vicente, Sorriso e Tangará da Serra",
            "Descrição": ("Ensino médio junto com um curso técnico, gratuito, no IFMT, para quem terminou o 9.º ano. São 196 vagas que "
                          "sobraram em 10 campi para começar em 2027. Se houver mais inscritos do que vagas, há sorteio público a 15 de dezembro."),
            "Origem da descrição": "Resumo", "Necessidades": "escola, profissao", "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": "Ter terminado o ensino fundamental (ou equivalente) até à matrícula", "Certificado": "desconhecido",
            "Inscrições até": "2026-12-08", "Início": "", "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje,
            "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
            "Notas": f"{hoje}: criado à mão pelo Claude (regra I8, decisão do responsável de 27/11; Edital 205/2026 do IFMT; frases conferidas por código).",
            "Como me inscrever": ("1. Até 08/12/2026, inscreva-se no site de seleção do IFMT (seletivo.ifmt.edu.br), no Edital 205/2026, "
                                  "e veja lá os cursos de cada campus.\n2. Se houver mais inscritos do que vagas, há sorteio público a "
                                  "15/12/2026, às 14h30 (transmitido no YouTube do IFMT); o resultado final sai a 18/12.\n3. Siga a "
                                  "matrícula no início de janeiro, conforme o edital."),
            "Nota da verificação": f"{hoje}: notícia oficial do IFMT e página «Estude no IFMT» lidas por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, data, vagas", "Mudança a rever": "FALSE",
            "O que falta confirmar": ("A lista de cursos por campus está no Edital 205/2026 (seletivo.ifmt.edu.br), que não abriu daqui. "
                                      "A notícia diz «matrícula entre 05 e 07 de janeiro de 2026», provavelmente 2027: confirme no edital.")}])
        base.guardar(); print("+", ident)
