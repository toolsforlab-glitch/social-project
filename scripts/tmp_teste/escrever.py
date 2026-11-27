"""Temporário (27/11/2026): regra I8 — técnicos integrados do IF Goiano, Campus Porangatu (Edital 001/2026, sorteio)."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara

hoje = hoje_ceara()
P = "https://ps.ifgoiano.edu.br/edital/visualizar/708/"
ED = "https://ps.ifgoiano.edu.br/media/anexos_edital/Edital_PS_T%C3%A9c._Integrados_2027_campus_Porangatu.pdf"
LDB = "https://www.planalto.gov.br/ccivil_03/leis/l9394.htm"
F = {"data": "Inscrições abertas até dia 03/12/2026", "vagas": "REALIZAÇÃO DO SORTEIO ELETRÔNICO"}
t = texto_de_html(baixar(P, timeout=40))
ok = all(citacao_valida(v, t) for v in F.values())
print("frases:", ok, {k: citacao_valida(v, t) for k, v in F.items()})
CURSOS = [("Técnico em Agropecuária integrado ao ensino médio (IF Goiano Porangatu)", "Técnico em Agropecuária Integrado ao Ensino Médio", 80, "agropecuária"),
          ("Técnico em Inteligência Artificial integrado ao ensino médio (IF Goiano Porangatu)", "Técnico em Inteligência Artificial Integrado ao Ensino Médio", 40, "inteligência artificial")]
if ok:
    base = Base(); carregar_config(base)
    ids = {r.get("ID") for r in base.tabela("Cursos")}
    for T, nome_pag, vagas, area in CURSOS:
        if not citacao_valida(nome_pag, t):
            print("sem curso na página:", nome_pag); continue
        ident = id_curso(P, T)
        if ident in ids: print("já existe", ident); continue
        ev = [f"gratuito (lei, vista no navegador a {hoje}): LDB art. 3.º, VI, «gratuidade do ensino público em estabelecimentos oficiais» ({LDB})",
              f"data: «{F['data']}» ({P})", f"vagas: «{F['vagas']}» ({P})", f"curso: «{nome_pag}» ({P})",
              f"edital (conferido por código a {hoje}): «A forma de seleção adotada é o SORTEIO PÚBLICO ELETRÔNICO»; "
              f"«não havendo prova, avaliação de desempenho, análise de histórico escolar»; requisito: «tenha concluído o Ensino "
              f"Fundamental ou que esteja concluindo o Ensino Fundamental no ano de 2026» ({ED})"]
        base.acrescentar("Cursos", [{"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "Instituto Federal Goiano (IF Goiano) – Campus Porangatu",
            "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-GO", "Modalidade": "presencial", "País": "BR",
            "Região": "Goiás", "Cidade": "Porangatu",
            "Descrição": (f"Ensino médio junto com um curso técnico em {area}, gratuito, no IF Goiano em Porangatu, em tempo integral, "
                          f"para quem termina o 9.º ano em 2026 ou já terminou. São {vagas} vagas para começar em 2027. "
                          "Não há prova: as vagas são sorteadas."),
            "Origem da descrição": "Resumo", "Necessidades": "escola, profissao", "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": "Ter terminado o ensino fundamental, ou terminá-lo em 2026", "Certificado": "desconhecido",
            "Inscrições até": "2026-12-03", "Início": "", "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje,
            "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
            "Notas": f"{hoje}: criado à mão pelo Claude (regra I8; Edital 001/2026 do IF Goiano Porangatu, sorteio; frases conferidas por código).",
            "Como me inscrever": ("1. Até 03/12/2026, inscreva-se no site de processos seletivos do IF Goiano (ps.ifgoiano.edu.br), "
                                  "no edital do Campus Porangatu, e escolha o curso.\n2. O sorteio eletrônico é a 08/12/2026 e o "
                                  "resultado final sai a 10/12.\n3. Se for chamado, envie os documentos da matrícula entre 10 e 18/12/2026."),
            "Nota da verificação": f"{hoje}: página do edital e edital em PDF lidos por código; frases conferidas.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "data, vagas", "Mudança a rever": "FALSE",
            "O que falta confirmar": ("A gratuidade do curso apoia-se na LDB (art. 3.º, VI), porque não se achou uma página do IF Goiano "
                                      "que o diga com todas as letras; a página do edital só diz que a inscrição é gratuita.")}])
        print("+", ident)
    base.guardar()
