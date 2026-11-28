"""Temporário (28/11/2026): Ceprocamp (Prefeitura de Campinas/Fumec), cursos técnicos do 1.º semestre de 2027 — por abrir
(inscrições de 01 a 15/12/2026). O site da Fumec recusa o GitHub (tempo esgotado): página e edital (PDF lido por código no
Chrome, sem abrir o PDF numa aba) vistos pelo Claude a 28/11."""
import sys
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config
from cursos import id_curso
from turmas import hoje_ceara
hoje = hoje_ceara()
base = Base(); carregar_config(base)
ids = {r.get("ID") for r in base.tabela("Cursos")}
P = "https://fumec.sp.gov.br/ceprocamp/"
ED = "https://www.fumec.sp.gov.br//sites/www.fumec.sp.gov.br/files/1.edital_tecnico_1o_sem_2027.docx.pdf"
INS = "https://inscricoes-ceprocamp.campinas.sp.gov.br/"
VP = f"vista no navegador a {hoje}; o site recusa o GitHub"
VE = f"edital lido no navegador a {hoje} (texto extraído do PDF por código; o site recusa o GitHub)"
F = [("abertura", "Inscrições, via internet, para os Cursos Técnicos. 01 a 15 de dezembro de 2026", P, VP),
     ("data", "Inscrições de 01 a 15 de dezembro", P, VP),
     ("gratuito", "Os cursos oferecidos pelo Centro de Educação Profissional de Campinas - CEPROCAMP são totalmente gratuitos", ED, VE),
     ("vagas", ("A classificação de todos os candidatos dos cursos Técnicos, incluindo aqueles que concorrem pelo sistema de cotas, "
                "levará em consideração os seguintes critérios"), ED, VE),
     ("turmas", ("Técnico em Administração: tarde (Centro), noite (José Alves) e manhã (Campo Grande), 30 vagas cada; Técnico em "
                 "Enfermagem: manhã (Centro), 30 vagas — Tabelas 1 a 3 do edital"), ED, VE)]
T = "Cursos técnicos gratuitos do Ceprocamp (Prefeitura de Campinas): Administração e Enfermagem, 1.º semestre de 2027"
i = id_curso(P, T)
if i not in ids:
    base.acrescentar("Cursos", [{"ID": i, "Estado": "Publicado", "Título": T, "Entidade": "Ceprocamp – Fundação Municipal para Educação Comunitária (Fumec), Prefeitura de Campinas",
        "Link": P, "Página do curso": P, "Destino do link": "curso", "Local": "BR-SP", "Modalidade": "presencial", "País": "BR",
        "Região": "São Paulo", "Cidade": "Campinas (Centro, Cidade Satélite Íris e Jardim Santa Clara/Campo Grande)",
        "Descrição": ("Cursos técnicos totalmente gratuitos da Prefeitura de Campinas: Técnico em Administração (3 turmas: manhã, tarde e "
                      "noite) e Técnico em Enfermagem (manhã), 30 vagas por turma, com aulas a partir de 4 de fevereiro de 2027. "
                      "A inscrição é pela internet, de 1 a 15 de dezembro de 2026. Não há prova: a classificação é por pontos "
                      "(ter estudado em escola pública, renda da família e idade)."),
        "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
        "Requisitos": ("Ensino médio concluído, ou cursando a 2.ª ou 3.ª série, ou a EJA do ensino médio; 16 anos (Administração) ou "
                       "18 anos (Enfermagem) até o primeiro dia de aula"),
        "Idade mínima": 16, "Certificado": "desconhecido", "Inscrições abrem em": "2026-12-01", "Inscrições até": "2026-12-15",
        "Início": "2027-02-04", "Duração": "3 a 4 módulos semestrais",
        "Turmas abertas (cartão geral)": 4, "Turmas contadas em": hoje, "O que se contou": "turmas",
        "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "página oficial", "Precisa de internet": "Sim",
        "Notas": f"{hoje}: criado à mão pelo Claude (outras cidades de SP). Edital Fumec/Ceprocamp nº 05/2026.",
        "Como me inscrever": ("1. De 01 a 15/12/2026, faça a inscrição pela internet no site de inscrições do Ceprocamp.\n"
                              "2. Indique se estudou em escola pública e a renda da família: a classificação é por pontos.\n"
                              "3. A classificação provisória sai a 06/01/2027 e a definitiva a 13/01/2027.\n"
                              "4. Se for convocado, faça a matrícula a 14 ou 15/01/2027, com os documentos pedidos no edital."),
        "Nota da verificação": f"{hoje}: página e edital do Ceprocamp lidos pelo Claude no navegador (o site recusa o GitHub).", **VERIFICACAO_INICIAL,
        "Situação das inscrições": "Por abrir", "Verificar automaticamente": "FALSE",
        "Evidência": " | ".join(f"{k}: «{x}» ({u}; {v})" for k, x, u, v in F)[:1800],
        "Campos comprovados": "abertura, data, gratuito, vagas", "Mudança a rever": "FALSE",
        "O que falta confirmar": ("A classificação é por pontos do edital: 70% das vagas para quem estudou em escola pública, renda per capita "
                                  "da família e faixa etária (mais pontos para os mais novos); há cotas para pessoas pretas ou pardas e para "
                                  "pessoas com deficiência.")}])
    base.guardar(); print("+", i, T)
