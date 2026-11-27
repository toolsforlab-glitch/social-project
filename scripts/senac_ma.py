"""Editais do Programa Senac de Gratuidade do Maranhão (Senac MA) e do Acre (Senac AC): turmas lidas do documento
oficial. A lista de editais muda de um Senac para o outro (Maranhão: lista pública em JSON; Acre: página com os PDFs
no separador «Aberto», sem datas); a leitura, a prova por código e a auditoria são as mesmas (ver FONTES).

O Senac MA publica um edital por oferta (cerca de três por semana), com um documento (PDF ou Word) que diz o
período de inscrição, onde e como se inscrever e, no Anexo I, os cursos com datas, horário, vagas e local.
O site tem uma lista pública dos editais (ma.senac.br/v1/public/notices). Este script:

1. lê a lista e escolhe os editais recentes que ainda não foram tratados;
2. tira o texto do documento (PDF: pypdf; Word antigo: antiword; Word novo: o XML do ficheiro);
3. pede ao Claude que extraia o período de inscrição, o modo e o local, e cada curso do Anexo I, SEMPRE com a
   frase exata do documento;
4. confere por código cada frase no texto do documento, e que a frase de cada curso contém o nome do curso e a
   data de início; o que não se confirma é deitado fora;
5. AUDITORIA antes de publicar: datas válidas e coerentes (início ≤ fim da inscrição, inscrição perto da data do
   edital, aulas depois da inscrição), horário com sentido, cidade escrita no documento;
6. grava uma linha por curso no separador Turmas e cria o curso em Cursos (Local BR-MA). O curso é publicado
   sozinho quando tem turma aberta aprovada e o documento diz que é do Programa Senac de Gratuidade;
7. termo aditivo: as turmas do edital alterado passam a Rever (o aditivo muda prazos), até uma pessoa rever.

A situação de cada turma vem só das datas do documento: Aberta até ao fim do dia em que a inscrição termina.
O selo "aberto/encerrado" da lista do Senac não é usado.
"""
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import zipfile
import html as _html

DIAS_POR_ABRIR = 60  # cursos «por abrir» aparecem até 60 dias antes da abertura (app.js usa o mesmo número)

from base import (registar_pendencia, HISTORICO, frase_de_gratuidade, gratuidade_comprovada, gratuidade_explicita, VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, etiquetas_acessibilidade,
                  perfis_da_frase, sim)
from comum import ErroClaude, baixar, claude, custo_estimado, extrair_json, gravar_json, ler_json
from turmas import ABA, chave, garantir_aba, hoje_ceara, id_curso, id_turma, necessidades, registo

# Cada Senac regional publica os editais do Programa Senac de Gratuidade à sua maneira; o resto é igual.
FONTES = [
    {"nome": "Senac MA", "uf": "MA", "local": "BR-MA", "regiao": "Maranhão",
     "entidade": "Senac Maranhão (Programa Senac de Gratuidade)", "estado": "estado/senac_ma.json",
     "lista": "https://ma.senac.br/editais-psg/", "prefixo_turma": "https://ma.senac.br/editais_psg/",
     "api": "https://ma.senac.br/v1/public/notices?type=psg&page=1&per_page=30", "site": "https://ma.senac.br"},
    {"nome": "Senac AC", "uf": "AC", "local": "BR-AC", "regiao": "Acre",
     "entidade": "Senac Acre (Programa Senac de Gratuidade)", "estado": "estado/senac_ac.json",
     "lista": "https://portal.ac.senac.br/psg/editais", "prefixo_turma": "https://portal.ac.senac.br/psg/assets/arquivos/"},
    {"nome": "Senai MA", "uf": "MA", "local": "BR-MA", "regiao": "Maranhão",
     "entidade": "Senai Maranhão (Programa SENAI de Gratuidade Regimental)", "estado": "estado/senai_ma.json",
     "programa": "Programa SENAI de Gratuidade Regimental", "listar": "senai_ma",
     "lista": "https://www.fiema.org.br/editais/11/Processos+Seletivos+-+Alunos",
     "prefixo_turma": "https://www.fiema.org.br/edital/"},
    {"nome": "Senac PI", "uf": "PI", "local": "BR-PI", "regiao": "Piauí",
     "entidade": "Senac Piauí (Programa Senac de Gratuidade)", "estado": "estado/senac_pi.json",
     "listar": "senac_pi", "lista": "https://psg.pi.senac.br/vagas/",
     "prefixo_turma": "https://psg.pi.senac.br/media/", "anexo": r"ANEXO\s+II\b", "max_caracteres": 48000, "inscricao_continua": True,
     "nota": "Neste Senac os cursos estão no ANEXO II (o Anexo I é a ficha de inscrição). A inscrição costuma ser "
             "«a partir do dia X até o limite de vagas»: nesse caso devolve inscricao.inicio = X, inscricao.fim = null "
             "e em inscricao.frase a frase do cronograma (Anexo III) com «limite de vagas». Se no fim do texto houver "
             "COMUNICADOS DE ALTERAÇÃO, eles mudam o edital: para um curso alterado usa as datas novas e, em «frase», "
             "a frase do comunicado com o nome do curso e o novo período."},
    {"nome": "Senac AL", "uf": "AL", "local": "BR-AL", "regiao": "Alagoas",
     "entidade": "Senac Alagoas (Programa Senac de Gratuidade)", "estado": "estado/senac_al.json",
     "listar": "senac_al", "lista": "https://psg.al.senac.br/editais", "max_caracteres": 48000, "inicio_opcional": True,
     "prefixo_turma": "https://psg.al.senac.br/admin/wp-content/uploads/",
     "nota": "Os editais do Senac Alagoas chamam-se «Edital de Bolsas Gratuitas» (a frase de gratuidade pode ser "
             "a do título ou do preâmbulo, ex.: «concessão de bolsas gratuitas nos cursos»). A inscrição costuma "
             "ser presencial, na unidade indicada no anexo. A tabela do anexo tem, em cada linha, a coluna "
             "«PERÍODO DE INSCRIÇÃO / MATRÍCULA» (ex.: «01/12/2026 a 11/12/2026»): é ESSE o período de inscrição "
             "(não o «PERÍODO DE EFETIVAÇÃO DAS MATRÍCULAS», que é mais longo); no texto, as duas datas dessa "
             "coluna podem estar em linhas seguidas («01/12/2026 a» e, na linha seguinte, «11/12/2026»); em "
             "«inscricao.frase» copia essas linhas. Em «local_inscricao» põe a unidade e o endereço do anexo. "
             "Em «frase» de cada curso copia a linha com o nome do curso; a data de início do curso pode não estar "
             "na mesma linha: nesse caso devolve inicio_aulas = null. Alguns editais têm VÁRIOS anexos (Anexo I, II, III…), "
             "cada um com o seu «PERÍODO DE INSCRIÇÃO / MATRÍCULA»: nesse caso devolve, em CADA turma, "
             "«inscricao_inicio», «inscricao_fim» e «frase_inscricao» (as linhas com as duas datas do anexo dessa "
             "turma, ex.: «04/01/2027 a» e «18/01/2027»), e «inscricao» geral pode ser null; e também «local_inscricao» "
             "e «frase_local_inscricao» com o «LOCAL DE INSCRIÇÃO / MATRÍCULA» desse anexo (ex.: «Instituto Ouro "
             "Preto Rua Padre Cícero, nº 86A – Ouro Preto – Maceió/AL», copiado das linhas do texto). Na tabela, a "
             "primeira coluna é o SEGMENTO (Saúde, Beleza, Moda, Comércio, Gestão…): não faz parte do nome do curso "
             "(«Moda Costureiro» → curso «Costureiro»). "
             "Se no fim do texto houver COMUNICADOS, eles mudam o edital: usa as datas novas e, "
             "nessa informação, a frase do comunicado."},
    {"nome": "Senai AL", "uf": "AL", "local": "BR-AL", "regiao": "Alagoas",
     "entidade": "SENAI Alagoas (Edital de Gratuidade)", "estado": "estado/senai_al.json",
     "programa": "Gratuidade Regimental do SENAI", "listar": "senai_al",
     "lista": "https://al.senai.br/edital-gratuidade/",
     "prefixo_turma": "https://al.senai.br/wp-content/uploads/",
     "nota": "Os editais do SENAI Alagoas chamam-se «Edital de Gratuidade» (vagas gratuitas para pessoas de baixa "
             "renda). No fim do texto vem o bloco do edital na página oficial, com «Período de inscrição», «Local "
             "para inscrição» e «Início das aulas»: podes copiar as frases desse bloco (valem tanto como as do PDF). "
             "Se o local de inscrição for um link (ex.: formulário Google), devolve-o em «link_inscricao» de cada "
             "turma, copiado letra a letra. Os PDFs costumam ser digitalizados e o texto vem de OCR: a tabela do "
             "ANEXO I tem uma linha por turma («Curso | CH | Vagas | Turno | Data de Início | Cidade | Link»); o "
             "nome do curso pode vir com a primeira letra cortada (ex.: «ISISTENTE DE …» é «ASSISTENTE DE …»): em "
             "«curso» escreve o nome certo, mas em «frase» copia a linha exatamente como está no texto. A coluna "
             "do link costuma sair ilegível no OCR: nesse caso usa o link do bloco da página. Se houver "
             "COMUNICADOS no fim, eles prevalecem."},
    {"nome": "Senai PE", "uf": "PE", "local": "BR-PE", "regiao": "Pernambuco",
     "entidade": "SENAI Pernambuco (Gratuidade Regimental)", "estado": "estado/senai_pe.json",
     "programa": "Gratuidade Regimental do SENAI", "listar": "senai_pe",
     "lista": "https://www.pe.senai.br/editais/",
     "prefixo_turma": "https://www.pe.senai.br/wp-content/uploads/",
     "nota": "Os editais do SENAI Pernambuco concedem «bolsas de estudo» (gratuidade regimental) em cursos de "
             "qualificação ou aperfeiçoamento. A frase da inscrição costuma ser «As inscrições estarão abertas entre "
             "os dias X a Y». A tabela de cursos está no ANEXO I e, para cada turma, o texto pode ter um link de "
             "inscrição (depois de «INSCRIÇÃO:»): devolve-o em «link_inscricao», copiado letra a letra, ou null. "
             "Atenção: «A inscrição no processo seletivo é gratuita» NÃO prova que o curso é gratuito (fala só da "
             "inscrição); «bolsas integrais» ou «bolsas de estudo» também NÃO provam (bolsa não garante gratuidade, decisão do "
             "responsável de 25/11/2026): para «gratuidade» só serve uma frase que diga que o curso é gratuito ou sem custo; "
             "senão, null. "
             "Se no fim do texto houver ERRATAS ou NOTAS DE CANCELAMENTO, elas mudam o edital: usa as datas novas e, "
             "nessa informação, a frase da errata."},
    {"nome": "Senac AM", "uf": "AM", "local": "BR-AM", "regiao": "Amazonas",
     "entidade": "Senac Amazonas (Programa Senac de Gratuidade)", "estado": "estado/senac_am.json",
     "listar": "senac_am", "lista": "https://am.senac.br/programa-senac-de-gratuidade/consulta-de-vaga/",
     "max_por_execucao": 20,  # muitas aberturas curtas, com inscrições de 1 a 3 dias
     "prefixo_turma": "https://portalsenac.am.senac.br/portal_senac/web/uploads/psg/", "anexo": r"ANEXO\s+I\b",
     "nota": "No Senac Amazonas cada «Abertura de Vagas» é um PDF curto: o ANEXO I tem o cronograma (a linha "
             "«Inscrições» com o período e o local, presencial ou online) e o ANEXO II o «QUADRO DE VAGAS_PSG» (uma "
             "linha por curso: município e unidade, curso, pré-requisitos, carga horária, início, término, horário, "
             "número de vagas). A gratuidade, a renda e a forma de preenchimento das vagas NÃO estão na abertura: "
             "estão no edital geral do PSG 2026, cujos trechos conferidos vêm no fim do texto («TRECHOS DO EDITAL "
             "GERAL»): podes copiar essas frases para «gratuidade», «renda» e «selecao». NÃO devolvas (deixa fora de "
             "«turmas») os cursos cujos pré-requisitos exigem já trabalhar na profissão ou ter experiência "
             "profissional (ex.: «Requisito específico: atuar como cabeleireiro(a)», «Comprovante de atuação "
             "profissional»), nem os que são só para pessoas indicadas por uma empresa ou instituição parceira "
             "(regra do responsável: cursos só para quem já tem emprego, cargo ou profissão ficam fora). Se no fim "
             "houver COMUNICADOS ou ERRATAS, eles prevalecem. Em «frase» de cada curso copia o texto do quadro desde o "
             "NOME do curso até às datas de início e término (os pré-requisitos ficam no meio e vêm incluídos), "
             "mesmo que passe de 40 palavras. Se a linha «Inscrições» tiver um só dia (ex.: «Inscrições 25/11/2026»), "
             "devolve inicio = fim = esse dia; se tiver dois dias («17/11/2026 e 19/11/2026»), o primeiro e o "
             "último; em «inscricao.frase» copia a linha «Inscrições …»."},
    {"nome": "Senac RO", "uf": "RO", "local": "BR-RO", "regiao": "Rondônia",
     "entidade": "Senac Rondônia (Programa Senac de Gratuidade)", "estado": "estado/senac_ro.json",
     "listar": "senac_ro", "lista": "https://www.ro.senac.br/edital-psg/", "extrator": "pdftotext",
     "api": "https://www.ro.senac.br/wp-json/wp/v2/media?search=Edital-PSG&per_page=60&_fields=date,source_url",
     "prefixo_turma": "https://www.ro.senac.br/wp-content/uploads/",
     "nota": "Nos editais do Senac Rondônia a forma de seleção costuma estar no item 2 («O critério inicial será a "
             "ordem de inscrição dos candidatos…»): copia-a para «selecao». A inscrição é online, num formulário do "
             "site (ex.: «https://www.ro.senac.br/formulario-inscricao-edital-psg-16-2026/»): devolve-o em "
             "«link_inscricao» de cada turma, copiado letra a letra (sem espaços). O Anexo I tem os cursos por "
             "município e unidade (Porto Velho, Cacoal, Jaru, Ji-Paraná, Vilhena, Ariquemes…). NÃO devolvas as turmas "
             "cujos pré-requisitos exigem já trabalhar na profissão ou ter experiência profissional (regra do "
             "responsável). Se no fim houver RETIFICAÇÕES, elas mudam o edital: usa as datas e os cursos novos."},
    {"nome": "Senac AP", "uf": "AP", "local": "BR-AP", "regiao": "Amapá",
     "entidade": "Senac Amapá (Programa Senac de Gratuidade)", "estado": "estado/senac_ap.json",
     "listar": "senac_ap", "lista": "https://www.ap.senac.br/psg",
     "api": "https://cms.ap.senac.br/api/v1/selection-processes", "extrator": "pdftotext",
     "prefixo_turma": "https://cms.ap.senac.br/storage/selection-process/",
     "nota": "Nos editais do Senac Amapá o «Anexo 1» tem os cursos (carga horária, vagas, turno, pré-requisitos) e o "
             "«Anexo 2» o cronograma (período de inscrição e de matrícula). A gratuidade costuma estar no item 1.2 («As "
             "vagas provenientes deste edital não terão ônus para o aluno selecionado»): podes copiá-la para "
             "«gratuidade». A inscrição é pela internet em https://send3.ap.senac.br/send3/site/psg (modo «online»; "
             "devolve esse endereço em «link_inscricao» de cada turma). As unidades são o CEP Senac Macapá e a UI "
             "Senac Santana: «cidade» = Macapá ou Santana. Em «selecao», a frase do item 4 sobre como as vagas são "
             "preenchidas, se for por ordem de inscrição ou sorteio. NÃO devolvas as turmas cujos pré-requisitos exigem "
             "já trabalhar na profissão ou ter experiência profissional, nem as só para pessoas indicadas por uma "
             "empresa ou instituição parceira (regra do responsável). Se no fim houver ERRATAS, elas prevalecem."},
    {"nome": "Senai AP", "uf": "AP", "local": "BR-AP", "regiao": "Amapá",
     "entidade": "SENAI Amapá (Gratuidade Regimental)", "estado": "estado/senai_ap.json",
     "listar": "senai_ap", "lista": "https://www.ap.senai.br/senai/processo-seletivo/publica%C3%A7%C3%B5es.html",
     "prefixo_turma": "https://www.ap.senai.br/", "extrator": "pdftotext-layout", "layout": True,
     "max_caracteres": 90000,
     "max_tokens": 48000, "limpar": r"HASH TOTVS:[ 0-9A-F-]+", "janela_inscricao": 150, "prova_janela": 5,
     "nota": "Nos editais de cursos gratuitos do SENAI Amapá (Macapá, Santana, às vezes Oiapoque) a inscrição costuma ser "
             "PRESENCIAL, na secretaria da unidade; nos editais semestrais o período dura meses (ex.: «29/06 a "
             "30/10/2026», no Anexo II, cronograma); copia a frase do período para «inscricao». A tabela do Anexo I "
             "tem uma coluna de perfil com texto longo, por isso o nome do curso e a data de início ficam em linhas "
             "diferentes: em «frase» copia o BLOCO de linhas seguidas, tal como aparecem (com as barras « | »), desde a "
             "linha com o nome do curso até à linha com a data de início; em «curso» o nome EXATAMENTE como está na "
             "tabela, sem acrescentar modalidade, ciclo ou turno (esses vão em «horario» e noutros campos). Em "
             "«selecao», a frase sobre como as vagas são preenchidas (ordem de inscrição/chegada, sorteio…). Se a seleção "
             "tiver prova, entrevista, análise de currículo ou ENEM, NÃO devolvas turmas (regra do responsável). NÃO "
             "devolvas as turmas cujos pré-requisitos exigem já trabalhar na profissão, ter experiência profissional ou "
             "vínculo com uma empresa (ex.: aprendizagem industrial, contrato de aprendiz). ATENÇÃO aos cursos de "
             "APERFEIÇOAMENTO: se o edital pedir para eles comprovação de experiência (carteira de trabalho, certificados "
             "ou «outra evidência» de experiência), NÃO devolvas nenhuma turma de aperfeiçoamento desse edital; as de "
             "qualificação profissional continuam. Também não devolvas as turmas só para pessoas "
             "indicadas por uma empresa ou instituição parceira. Cursos para um público (mulheres, pessoas com 50 anos "
             "ou mais) entram: o requisito vai em «requisitos». Se no fim houver RETIFICAÇÕES, elas prevalecem."},
    {"nome": "Senai AM", "uf": "AM", "local": "BR-AM", "regiao": "Amazonas",
     "entidade": "SENAI Amazonas (Programa SENAI de Gratuidade)", "estado": "estado/senai_am.json",
     "programa": "Programa SENAI de Gratuidade", "listar": "senai_am",
     "lista": "https://fieam.org.br/senai/wp-content/uploads/sites/16/",
     "prefixo_turma": "https://fieam.org.br/senai/wp-content/uploads/sites/16/",
     "layout": True, "partes": 4, "ancora_com_data": True, "codigo_turma": r"[A-Z]{2,4}\.[A-Z0-9]{2,4}\.\d{2,4}",
     "link_inscricao_regex": r"pelo endereço\s+(https://forms\.(?:cloud\.microsoft|office\.com|gle)/\S+)", "max_extra": 70000, "max_tokens": 32000, "max_caracteres": 30000,
     "nota": "No SENAI Amazonas a «Chamada Pública» (texto principal) tem as regras: a gratuidade («Os cursos "
             "ofertados serão 100% gratuitos»), a forma de seleção (item 1.17, «ordem de data e horário de "
             "inscrição»), a baixa renda (item 1.20, declaração do candidato: copia essa frase para «renda») e o "
             "período de inscrição (item 1.4: «As inscrições serão realizadas a partir das 8h do dia …, pelo endereço "
             "… e serão encerradas às 12h do dia …»; modo «online»; o endereço do formulário vai em «link_inscricao» "
             "de cada turma, copiado letra a letra). A lista de turmas NÃO está na chamada: está no fim, no DOCUMENTO "
             "OFICIAL LIGADO AO EDITAL «Programação de cursos» (planilha com curso, código da turma, carga horária, "
             "vagas, tipo de ação, período, horário e pré-requisitos; as células longas partem-se em várias linhas). "
             "Uma entrada em «turmas» por CÓDIGO DE TURMA (ex.: «APP.CLP.051»), com o código em «codigo» (campo "
             "extra, copiado letra a letra). Em «frase» copia o texto desde o "
             "início do nome do curso até ao período (datas de início e término), tal como aparece, mesmo que o nome "
             "venha partido à volta do código. Em «curso» o nome completo, juntando as partes. Todas as turmas são em "
             "Manaus: «cidade» = «Manaus», mesmo nas EaD e semipresenciais. Os pré-requisitos (escolaridade, idade, "
             "outro curso feito antes) não excluem a turma; mas NÃO devolvas as turmas cujo pré-requisito exija já "
             "trabalhar na profissão ou ter experiência profissional (regra do responsável: cursos só para quem já "
             "tem emprego, cargo ou profissão ficam fora)."},
    {"nome": "Senai PI", "uf": "PI", "local": "BR-PI", "regiao": "Piauí",
     "entidade": "SENAI Piauí (Programa SENAI de Gratuidade Regimental)", "estado": "estado/senai_pi.json",
     "programa": "Programa SENAI de Gratuidade Regimental", "listar": "senai_pi",
     "lista": "https://fiepi.com.br/servicos/cursos-nivel-medio-senai-gratuidade/",
     "prefixo_turma": "https://fiepi.com.br/media/uploads/",
     "nota": "Se no fim do texto houver RETIFICAÇÕES, elas mudam o edital: usa as datas retificadas e, nessa "
             "informação, a frase da retificação."},
]
MESES = {m: i + 1 for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                                          "setembro", "outubro", "novembro", "dezembro"])}
MAX_RECENTES_SEM_DATA = 20  # Acre: a lista não tem datas; só os 20 editais mais recentes do ano entram
DIAS_RECENTES = 15       # inscrições duram 3 a 7 dias: editais mais antigos já não têm inscrição aberta
MAX_POR_EXECUCAO = 12    # limite de documentos lidos com o Claude por execução (controla o custo)
MAX_CARACTERES = 30000
DIAGNOSTICO = os.environ.get("SENAC_MA_DIAGNOSTICO", "")  # pasta onde guardar texto e resposta de cada edital
MAX_TENTATIVAS = 2       # um edital sem nada comprovado é relido uma vez; à segunda fica de lado

SEM_FRASE_GRATUIDADE = "O edital não diz por escrito que o curso é gratuito (só nomeia o programa de gratuidade)."
# texto antigo (até 27/11/2026), que dizia «Senac» também nos editais do SENAI: é substituído quando a linha é relida
SEM_FRASE_GRATUIDADE_ANTIGA = "O edital não diz por escrito que o curso é gratuito (só nomeia o Programa Senac de Gratuidade)."

SISTEMA = """Extrais dados de um edital oficial do Senac Maranhão (Programa Senac de Gratuidade) para uma base \
de dados pública. Cada valor que devolves vai ser conferido por código no texto do edital: só conta se vier \
acompanhado da frase EXATA do documento (copiada letra a letra, sem corrigir erros, até 40 palavras).

Regras:
- Nunca deduzas. Se o edital não diz, devolve null.
- O período de inscrição é o do processo seletivo (item "DA INSCRIÇÃO"), não as datas das aulas.
- Datas no formato AAAA-MM-DD. Se o documento tiver um erro evidente numa data (ex.: "10/02/20227"), devolve \
null nesse campo.
- "modo": "presencial" se a inscrição é feita num local físico, "online" se é pela internet, "ambos" se o \
edital disser as duas, null se não disser.
- Em "turmas", uma entrada por curso e turno do Anexo I (ou do anexo com a tabela dos cursos) ("PROGRAMAÇÃO DOS CURSOS E TURNOS"; a tabela pode \
aparecer com as células separadas por " | " numa só linha: copia a linha com os " | "). Se o edital tem \
cursos, "turmas" nunca vem vazio. "frase" é o texto da linha do Anexo I desse curso, \
copiado tal como aparece no texto que recebes (começa no nome do curso e inclui a data de início das aulas).
- "cidade": o município onde o curso decorre, como está escrito no edital.
- "gratuidade": a frase exata do edital que diz que o curso é gratuito ou sem custo para quem estuda (ex.: \
"gratuito", "sem custo", "bolsas gratuitas"). O nome do programa sozinho não serve; "bolsa integral" ou "bolsa de \
estudo" sozinhas também não (decisão do responsável, 24/11/2026: bolsa pressupõe concorrência); se não houver, null.
- "selecao": a frase exata que diz como as vagas são preenchidas, se for por ordem de inscrição (ou de chegada) \
ou por sorteio; senão null.
- "renda": a frase exata com o critério de renda, se existir.
- "reserva": a frase exata que reserva vagas ou dá prioridade a um grupo de pessoas (ex.: pessoas com deficiência, \
mulheres, pessoas negras, quilombolas), se existir; senão null.
- "acessibilidade": a frase exata que diz que o curso oferece um recurso de acessibilidade para pessoas com \
deficiência (intérprete de Libras, local acessível, material em braile, audiodescrição, tecnologia assistiva), se \
existir; senão null. Atendimento especial só para fazer a prova de seleção não conta.

Devolve só JSON entre <json></json>:
{"inscricao": {"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD", "frase": "..."} ou null,
 "modo": "presencial|online|ambos" ou null, "local_inscricao": "..." ou null, "frase_local": "..." ou null,
 "gratuidade": "..." ou null, "renda": "..." ou null, "reserva": "..." ou null, "acessibilidade": "..." ou null,
 "selecao": "..." ou null,
 "turmas": [{"curso": "...", "cidade": "...", "inicio_aulas": "AAAA-MM-DD" ou null, "fim_aulas": "AAAA-MM-DD" ou null,
   "horario": "..." ou null, "dias": "..." ou null, "vagas": "..." ou null, "carga_horaria": "..." ou null,
   "local_curso": "..." ou null, "frase": "...",
   "inscricao_inicio": "AAAA-MM-DD" ou null, "inscricao_fim": "AAAA-MM-DD" ou null, "frase_inscricao": "..." ou null,
   "local_inscricao": "..." ou null, "frase_local_inscricao": "..." ou null}]}
Os três últimos campos de cada turma só se usam quando o edital tem um período de inscrição DIFERENTE para cada \
curso ou anexo (senão null): "frase_inscricao" é o texto exato onde está esse período (ex.: "04/01/2027 a \
18/01/2027", que pode estar partido em duas linhas). Do mesmo modo, se cada anexo tem o seu LOCAL de \
inscrição, "local_inscricao" e "frase_local_inscricao" (o texto exato onde o local está escrito) de cada turma."""


# ------------------------------------------------------------------ documento

MARCA_OCR = "[texto lido por OCR de um PDF digitalizado]"


def parecido_na_frase(curso, frase, minimo=0.9):
    """O nome do curso (como devia ser) é quase igual a algum trecho da frase lida por OCR?"""
    import difflib
    c, f = chave(curso), chave(frase)
    if len(c) < 8:
        return False
    melhor = 0.0
    for i in range(0, max(1, len(f) - len(c) + 3)):
        for n in (len(c) - 2, len(c) - 1, len(c), len(c) + 1):
            melhor = max(melhor, difflib.SequenceMatcher(None, c, f[i:i + n]).ratio())
    return melhor >= minimo


def texto_por_ocr(dados, max_paginas=12):
    """Texto de um PDF digitalizado, com o Tesseract (português). Devolve "" se o Tesseract não estiver instalado.
    O texto lido assim pode ter letras trocadas: as fontes que o usam têm de ter uma segunda prova do período de
    inscrição (ex.: o mesmo período escrito na página oficial, em «periodo_lista»)."""
    with tempfile.TemporaryDirectory() as pasta:
        origem = os.path.join(pasta, "e.pdf")
        with open(origem, "wb") as f:
            f.write(dados)
        try:
            subprocess.run(["pdftoppm", "-r", "300", "-png", "-l", str(max_paginas), origem, os.path.join(pasta, "p")],
                           capture_output=True, timeout=180, check=True)
            partes = []
            for img in sorted(x for x in os.listdir(pasta) if x.endswith(".png")):
                r = subprocess.run(["tesseract", os.path.join(pasta, img), "-", "-l", "por", "--psm", "4"],
                                   capture_output=True, timeout=120)
                partes.append(r.stdout.decode("utf-8", "replace"))
            texto = "\n".join(partes)
            return (MARCA_OCR + "\n" + texto) if texto.strip() else ""
        except (OSError, subprocess.SubprocessError):
            return ""


def texto_do_documento(dados, tipo, layout=False):
    """Texto de um PDF, Word antigo (.doc) ou Word novo (.docx). Com layout=True, o PDF é lido mantendo as colunas
    (cada linha da tabela fica numa linha do texto; usado no Senac AL, onde a leitura normal parte as linhas)."""
    if "pdf" in tipo or dados[:4] == b"%PDF":
        from pypdf import PdfReader
        if layout == "pdftotext-layout":
            # tabelas em PDFs que o pypdf não lê em modo layout (TOTVS/PDFTron, SENAI AP): o pdftotext -layout mantém
            # cada linha da tabela numa linha; as separações longas viram « | », como no modo layout
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
                    f.write(dados)
                    f.flush()
                    t = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True,
                                       timeout=120).stdout.decode("utf-8", "replace")
                linhas = [re.sub(r" {3,}", " | ", l).strip(" |") for l in t.splitlines()]
                t = "\n".join(l for l in linhas if l)
                if len(t.strip()) > 300:
                    return t
            except (OSError, subprocess.SubprocessError):
                pass
            layout = False
        if layout == "pdftotext":
            # alguns PDFs (Senac RO) saem do pypdf com espaços a meio das palavras («F armácia»); o pdftotext não
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
                    f.write(dados)
                    f.flush()
                    t = subprocess.run(["pdftotext", f.name, "-"], capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
                if len(t.strip()) > 300:
                    return t
            except (OSError, subprocess.SubprocessError):
                pass
            layout = False
        if layout:
            # as colunas vêm separadas por muitos espaços: cada separação longa vira « | » (texto mais curto e as
            # colunas continuam distinguíveis); as linhas em branco saem
            texto = "\n".join((p.extract_text(extraction_mode="layout") or "") for p in PdfReader(io.BytesIO(dados)).pages)
            linhas = [re.sub(r" {3,}", " | ", l).strip(" |") for l in texto.splitlines()]
            return "\n".join(l for l in linhas if l)
        texto = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(dados)).pages)
        if len(texto.strip()) < 300:
            texto = texto_por_ocr(dados) or texto  # PDF digitalizado (imagens): lido por OCR (SENAI AL, 23/11/2026)
        return texto
    if dados[:4] == b"PK\x03\x04":  # .docx
        return texto_docx(dados)
    # Word antigo (.doc): o LibreOffice converte para .docx sem perder as linhas das tabelas (o antiword perde
    # as linhas do Anexo I quando a tabela tem um título em células unidas); o antiword fica como recurso
    with tempfile.TemporaryDirectory() as pasta:
        origem = os.path.join(pasta, "edital.doc")
        with open(origem, "wb") as f:
            f.write(dados)
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "docx", "--outdir", pasta, origem],
                           capture_output=True, timeout=120)
            with open(os.path.join(pasta, "edital.docx"), "rb") as f:
                return texto_docx(f.read())
        except (OSError, subprocess.SubprocessError):
            return subprocess.run(["antiword", "-w", "0", origem], capture_output=True, text=True,
                                  timeout=60).stdout


def texto_docx(dados):
    """Texto de um .docx com cada linha de tabela numa só linha (células separadas por " | ")."""
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")

    def linha(m):
        celulas = re.findall(r"<w:tc\b.*?</w:tc>", m.group(0), flags=re.S)
        return " | ".join(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"</w:p>", " ", c))).strip()
                          for c in celulas) + "\n"
    xml = re.sub(r"<w:tr\b.*?</w:tr>", linha, xml, flags=re.S)
    xml = re.sub(r"<w:tab/>", " ", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    texto = re.sub(r"<[^>]+>", "", xml)
    return _html.unescape(texto)


def recortar(texto, anexo_regex=r"ANEXO\s+I\b", maximo=MAX_CARACTERES):
    """Os editais longos são cortados no meio, nunca no fim: o anexo com a tabela dos cursos fica no fim."""
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n\s*\n+", "\n", texto)
    if len(texto) <= maximo:
        return texto
    anexo = [m.start() for m in re.finditer(anexo_regex, texto)]
    inicio_anexo = anexo[-1] if anexo else len(texto) - maximo // 2
    cauda = texto[inicio_anexo:inicio_anexo + maximo // 2]
    return texto[:maximo - len(cauda)] + "\n[...]\n" + cauda


def data_br(iso):
    try:
        return datetime.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return ""


def data_valida(iso):
    try:
        datetime.date.fromisoformat(str(iso))
        return str(iso)
    except (TypeError, ValueError):
        return ""


def data_na_frase(iso, frase):
    """A data está escrita na frase? Aceita «07/09/2026», «07/09» e «07 de setembro de 2026»."""
    try:
        d = datetime.date.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return False
    compacta = re.sub(r"\s", "", frase)
    if re.search(rf"(?<!\d)0?{d.day}/0?{d.month}(?!\d)", compacta):
        return True
    mes = [m for m, i in MESES.items() if i == d.month][0]
    return bool(re.search(rf"\b0?{d.day}\s*(?:º|°)?\s+de\s+{mes}", frase.lower()))


def horario_curto(h):
    m = re.findall(r"(\d{1,2})\s*(?:[:hH]\s*(\d{2}))?", h or "")
    horas = [(int(a), int(b or 0)) for a, b in m if a and int(a) <= 23][:2]
    return f"{horas[0][0]:02d}:{horas[0][1]:02d} - {horas[1][0]:02d}:{horas[1][1]:02d}" if len(horas) == 2 else ""


MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}


def nome_cidade(c):
    """'SÃO DOMINGOS DO MARANHÃO/MA' → 'São Domingos do Maranhão' (o edital escreve a cidade de várias formas)."""
    c = re.sub(r"\s*(?:[/,–-]\s*|\()(MA|AC|PI|PE|AL|PB|BA|RN|SE|PA|AM|RO|RR|AP|TO|Maranh[ãa]o|Acre|Piau[íi]|Pernambuco|Alagoas|Para[íi]ba|Bahia|Rio Grande do Norte|Sergipe|Par[áa]|Amazonas|Rond[ôo]nia|Roraima|Amap[áa]|Tocantins)\)?\s*$", "", re.sub(r"\s+", " ", c or "").strip(),
               flags=re.I).strip(" -–/")
    if c.isupper() or c.islower():
        c = " ".join(p.lower() if i and p.lower() in MINUSCULAS else p.capitalize()
                     for i, p in enumerate(c.split(" ")))
    return c


def horario_confirmado(h, frase):
    """Horário normalizado, só se as horas aparecerem na frase do Anexo I."""
    curto = horario_curto(h)
    if not curto:
        return ""
    horas = {int(x) for x in re.findall(r"\d{1,2}", re.sub(r"\d{1,2}/\d{1,2}/\d{2,5}", " ", frase))}
    return curto if int(curto[:2]) in horas and int(curto[8:10]) in horas else ""


# ------------------------------------------------------------------ prova e auditoria

def palavras_em_ordem(nome, frase):
    """Todas as palavras do nome aparecem na frase, pela mesma ordem (tabela com o nome do curso partido em várias
    linhas, entre outras colunas)."""
    pos = 0
    alvo = chave(frase)
    for p in chave(nome).split():
        i = alvo.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def provar(res, texto, publicado, continua=False, tabela_partida=False, janela=60):
    # texto lido em colunas (Senac AL): as colunas estão separadas por « | »; as frases copiadas podem trazer ou não
    # essas barras, por isso compara-se sem elas (o resto da frase tem de estar igual)
    def _cv(frase, tx):
        if tabela_partida:
            return citacao_valida(str(frase).replace("|", " "), str(tx).replace("|", " "))
        return citacao_valida(frase, tx)
    """Fica só o que está escrito no documento. Devolve (dados limpos, problemas do edital).
    continua=True: o edital pode dizer «a partir do dia X até o limite de vagas» (sem dia de fim); então a
    inscrição de cada turma vale até à véspera do início das aulas, e a frase tem de dizer «limite de vagas»."""
    problemas = []
    insc = res.get("inscricao") if isinstance(res.get("inscricao"), dict) else {}
    ini, fim, frase_insc = data_valida(insc.get("inicio")), data_valida(insc.get("fim")), str(insc.get("frase") or "")
    ate_vagas = bool(continua and not fim and ini and _cv(frase_insc, texto)
                     and re.search(r"limite\s+de\s+vagas", frase_insc, flags=re.I) and data_na_frase(ini, frase_insc))
    if ate_vagas:
        pass
    elif not (ini and fim and _cv(frase_insc, texto) and data_br(fim)[:5] in frase_insc.replace(" ", "")):
        problemas.append("o período de inscrição não foi confirmado no documento")
        ini = fim = ""
    elif ini > fim:
        problemas.append(f"o fim da inscrição ({fim}) é anterior ao início ({ini})")
    elif publicado and not (publicado[:10] <= fim <= (datetime.date.fromisoformat(publicado[:10])
                                                         + datetime.timedelta(days=janela)).isoformat()):
        problemas.append(f"o fim da inscrição ({fim}) não está perto da data do edital ({publicado[:10]})")
    local = str(res.get("local_inscricao") or "") if _cv(str(res.get("frase_local") or ""), texto) else ""
    modo = res.get("modo") if res.get("modo") in ("presencial", "online", "ambos") else ""
    if modo in ("presencial", "ambos") and not local:
        modo = ""  # inscrição presencial sem local comprovado não serve a ninguém
    # gratuidade: só uma frase que diga que não há custo; o nome do programa não chega (regra de 20/11/2026)
    gratuito = _cv(str(res.get("gratuidade") or ""), texto) and gratuidade_explicita(str(res.get("gratuidade")))
    if not gratuito:
        frase = frase_de_gratuidade(texto)
        if frase:
            gratuito, res["gratuidade"] = True, frase
    # o nome do programa no edital (não prova a gratuidade; serve para publicar com «Gratuidade por confirmar»)
    m = re.search(r"[^.\n]{0,80}(?:programa\s+senac\s+de\s+gratuidade|gratuidade\s+regimental)[^.\n]{0,80}",
                  texto, flags=re.I)
    res["programa"] = re.sub(r"\s+", " ", m.group(0)).strip() if m else ""
    renda = str(res.get("renda") or "") if _cv(str(res.get("renda") or ""), texto) else ""
    reserva = str(res.get("reserva") or "") if _cv(str(res.get("reserva") or ""), texto) else ""
    if (not perfis_da_frase(reserva) or "( )" in reserva
            or not re.search(r"reserv|\bcotas?\b|priorid|prefer[êe]nc|exclusiv|destinad|somente|apenas", reserva, flags=re.I)):
        # a frase tem de nomear um grupo que conhecemos e dizer que há vagas para ele (a pergunta da ficha de
        # inscrição «Você é pessoa com deficiência? ( ) sim ( ) não» não é uma reserva de vagas)
        reserva = ""
    # como se distribuem as vagas (24/11/2026): a frase tem de estar no documento e falar de sorteio ou ordem
    selecao = str(res.get("selecao") or "")
    sel_limpa = re.sub(r"\s+", " ", selecao.replace("|", " "))  # texto em colunas: « | » no meio da frase
    if not (_cv(selecao, texto) and re.search(r"sorte|ordem (?:de|das) (?:data e hor[áa]rio d[ae] )?inscri|ordem de chegada|ordem cronol", sel_limpa, re.I)):
        selecao = ""
    elif tabela_partida:
        selecao = sel_limpa  # guarda-se sem as barras das colunas (o site procura «ordem de … inscrição»)
    acess = str(res.get("acessibilidade") or "")
    if not (_cv(acess, texto) and etiquetas_acessibilidade(acess)):
        acess = ""  # a frase tem de estar no documento e nomear um recurso concreto
    turmas = []
    for t in res.get("turmas") or []:
        if not isinstance(t, dict):
            continue
        frase, curso = str(t.get("frase") or ""), str(t.get("curso") or "").strip()
        inicio = data_valida(t.get("inicio_aulas"))
        if not curso or not _cv(frase, texto):
            continue
        nome_ocr = False
        if chave(curso) not in chave(frase) and not (tabela_partida and palavras_em_ordem(curso, frase)):
            # texto de OCR: o nome pode vir com uma ou duas letras trocadas ou cortadas (ex.: «ISISTENTE» por
            # «ASSISTENTE»); aceita-se só se o nome escrito for quase igual ao trecho da frase (90% ou mais)
            if not (texto.startswith(MARCA_OCR) and parecido_na_frase(curso, frase)):
                continue
            nome_ocr = True
        if inicio and not data_na_frase(inicio, frase):
            inicio = ""
        cidade = str(t.get("cidade") or "").strip()
        cidade = nome_cidade(cidade) if cidade and chave(cidade) in chave(texto) else ""
        # link de inscrição da turma (SENAI PE): só conta se estiver escrito no documento, letra a letra
        # (o PDF pode partir o endereço em duas linhas: compara-se sem espaços)
        link_insc = re.sub(r"\s+", "", str(t.get("link_inscricao") or ""))
        if not (link_insc.startswith("https://") and link_insc in re.sub(r"\s+", "", texto)):
            link_insc = ""
        t["link_inscricao"] = link_insc
        # período de inscrição próprio da turma (editais com um período por anexo, ex.: Senac AL): só com a frase
        ti, tf = data_valida(t.get("inscricao_inicio")), data_valida(t.get("inscricao_fim"))
        tfr = str(t.get("frase_inscricao") or "")
        propria = None
        if tf and _cv(tfr, texto) and data_na_frase(tf, tfr) and (not ti or (data_na_frase(ti, tfr) and ti <= tf)):
            propria = {"ini": ti, "fim": tf, "frase": tfr}
        # local de inscrição próprio da turma (um por anexo): só com a frase onde está escrito
        tl, tlf = str(t.get("local_inscricao") or "").strip(), str(t.get("frase_local_inscricao") or "")
        local_t = tl if (tl and _cv(tlf, texto) and chave(tl)[:20] in chave(tlf)) else ""
        turmas.append({**t, "insc_propria": propria, "local_proprio": local_t, "curso": curso, "inicio_aulas": inicio, "cidade": cidade,
                       "fim_aulas": data_valida(t.get("fim_aulas")),
                       "horario": horario_confirmado(t.get("horario"), frase),
                       **({"nome_ocr": True} if nome_ocr else {})})
    return {"ini": ini, "fim": fim, "ate_vagas": ate_vagas, "frase_insc": frase_insc if (fim or ate_vagas) else "",
            "local": local, "modo": modo,
            "gratuito": gratuito, "renda": renda, "reserva": reserva, "acessibilidade": acess, "selecao": selecao,
            "turmas": turmas}, problemas


def auditar(t, edital, problemas_edital, inicio_opcional=False):
    propria = t.get("insc_propria")
    if propria:
        # a turma tem o seu próprio período, provado: os problemas do período geral do edital não se aplicam
        problemas_edital = [x for x in problemas_edital if "inscrição" not in x]
        edital = {**edital, "ini": propria["ini"], "fim": propria["fim"]}
    if t.get("local_proprio") and not edital["modo"]:
        edital = {**edital, "modo": "presencial", "local": t["local_proprio"]}
    p = list(problemas_edital)
    if not edital["fim"] and not edital.get("ate_vagas"):
        p.append("sem período de inscrição comprovado")
    if not t["inicio_aulas"]:
        if not inicio_opcional:
            p.append("sem data de início das aulas comprovada")
    elif edital["ini"] and t["inicio_aulas"] < edital["ini"]:
        p.append(f"as aulas começam ({t['inicio_aulas']}) antes de abrir a inscrição ({edital['ini']})")
    if t.get("fim_aulas") and t["inicio_aulas"] and t["fim_aulas"] < t["inicio_aulas"]:
        p.append(f"o fim das aulas ({t['fim_aulas']}) é anterior ao início ({t['inicio_aulas']})")
    if not t["cidade"]:
        p.append("a cidade do curso não foi confirmada no documento")
    if not edital["modo"]:
        p.append("o documento não confirma como e onde se faz a inscrição")
    h = re.match(r"(\d{2}):(\d{2}) - (\d{2}):(\d{2})", t.get("horario") or "")
    if h and (int(h.group(1)) < 5 or h.group(1) + h.group(2) >= h.group(3) + h.group(4)):
        p.append(f"o horário ({t['horario']}) não faz sentido")
    return p


# ------------------------------------------------------------------ principal

def listar_ma(fonte):
    dados = json.loads(baixar(fonte["api"], timeout=40).decode("utf-8"))["data"]
    for e in dados:
        n = numero_alterado(e.get("number"))
        e["pagina"] = fonte["site"] + (e.get("path") or "")
        e["padrao"] = rf"edital-psg-n[ºo°]?-?{n}-"
        e["aditivo"] = "TERMO" in str(e.get("number", "")).upper() or any(
            d.get("type") == "aditivo" for d in e.get("documents") or [])
        for d in e.get("documents") or []:
            d["url"] = fonte["site"] + d["url"] if d.get("url", "").startswith("/") else d.get("url", "")
    return dados


def listar_ac(fonte):
    """Senac Acre: a página lista, no separador «Aberto», os editais do ano com o PDF e os avisos (prorrogação,
    alteração de vagas). Não tem datas: o período de inscrição vem sempre do próprio PDF."""
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    inicio = html.find('id="abertos"')
    fim = html.find('id="emAndamento"', inicio)
    if inicio < 0:
        raise ValueError("separador «Aberto» não encontrado")
    ano = hoje_ceara()[:4]
    por_numero = {}
    for card in html[inicio:fim if fim > 0 else None].split('<div class="card">')[1:]:
        titulo = re.search(r'card-header.*?</i>(.*?)</div>', card, flags=re.S)
        titulo = _html.unescape(re.sub(r"\s+", " ", titulo.group(1))).strip() if titulo else ""
        for href in re.findall(r'href="([^"]+\.pdf)"', card, flags=re.I):
            url = href if href.startswith("http") else "https://portal.ac.senac.br" + href
            url = urllib.parse.quote(_html.unescape(url), safe=":/%")  # os nomes têm espaços e acentos
            m = re.search(r"Edital_PSG_(\d{2,3})_(\d{4})", url, flags=re.I)
            if not m or m.group(2) != ano or re.search(r"lista|matriculad|classifica|resultado", url, flags=re.I):
                continue
            g = por_numero.setdefault(int(m.group(1)), {"edital": "", "avisos": [], "titulo": titulo})
            if re.search(r"aviso|retifica|prorroga|altera|errata", url, flags=re.I):
                g["avisos"].append(url)
            elif not g["edital"]:
                g["edital"] = url
    editais = []
    for n in sorted(por_numero, reverse=True)[:MAX_RECENTES_SEM_DATA]:
        g = por_numero[n]
        padrao = rf"Edital_PSG_0*{n}_{ano}"
        if g["edital"]:
            editais.append({"id": f"ac-{ano}-{n}", "updated_at": g["edital"].rsplit("/", 1)[-1], "number": f"{n:03d}",
                            "published_at": "", "title": g["titulo"] or f"Edital PSG nº {n:03d}/{ano} do Senac Acre",
                            "pagina": g["edital"], "padrao": padrao, "aditivo": False, "tem_aviso": bool(g["avisos"]),
                            "documents": [{"type": "edital", "mime_type": "application/pdf", "url": g["edital"]}]})
        for a in g["avisos"]:
            editais.append({"id": f"ac-{ano}-{n}", "updated_at": a.rsplit("/", 1)[-1], "number": f"{n:03d}-AVISO",
                            "published_at": "", "title": "Aviso", "pagina": a, "padrao": padrao, "aditivo": True,
                            "documents": [{"type": "aditivo", "mime_type": "application/pdf", "url": a}]})
    return editais


def data_por_extenso(t):
    """'5 de outubro de 2026' → '2026-10-05'."""
    m = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})", (t or "").lower())
    return f"{m.group(3)}-{MESES[m.group(2)]:02d}-{int(m.group(1)):02d}" if m and m.group(2) in MESES else ""


def listar_senai_ma(fonte):
    """Senai Maranhão: a lista «Processos Seletivos – Alunos» (fiema.org.br) dá o código, a data de publicação e o
    período de inscrição de cada edital. Só entram os do Programa SENAI de Gratuidade Regimental com inscrição ainda
    aberta; o documento (PDF) está na página de cada edital."""
    html = baixar(fonte["lista"] + "?page=1&per-page=30", timeout=60).decode("utf-8", "replace")
    hoje = hoje_ceara()
    editais = []
    padrao = (r'<a href="(/edital/(\d+)/[^"]+)" title="([^"]+)">.*?C[óo]digo:</strong>\s*([^<]+)<br.*?'
              r'Data de Publica[çc][ãa]o: </strong>\s*([^<]+)<br.*?Data de In[íi]cio: </strong>\s*([^<]+?)\s*<br.*?'
              r'Data Fim: </strong>\s*([^<]+?)\s*<br')
    for caminho, num, titulo, codigo, pub, ini, fim in re.findall(padrao, html, flags=re.S):
        titulo = _html.unescape(titulo)
        ini, fim, pub = data_por_extenso(ini), data_por_extenso(fim), data_por_extenso(pub)
        if "GRATUIDADE" not in titulo.upper() or not fim or fim < hoje:
            continue
        pagina = "https://www.fiema.org.br" + caminho
        detalhe = baixar(pagina, timeout=60).decode("utf-8", "replace")
        pdfs = re.findall(r'href="(/uploads/edital/\d+/[^"]+\.pdf)"', detalhe, flags=re.I)
        if not pdfs:
            continue
        editais.append({"id": f"senai-ma-{num}", "updated_at": pdfs[0].rsplit("/", 1)[-1],
                        "number": _html.unescape(codigo).strip(), "published_at": pub, "title": titulo,
                        "pagina": pagina, "padrao": re.escape(f"/edital/{num}/"), "aditivo": False,
                        "periodo_lista": (ini, fim),
                        "documents": [{"type": "edital", "mime_type": "application/pdf",
                                       "url": "https://www.fiema.org.br" + pdfs[0]}]})
    return editais


def listar_senac_pi(fonte):
    """Senac Piauí: a página «Consulta de vagas» (psg.pi.senac.br/vagas/) tem um cartão por documento: editais do
    Programa Senac de Gratuidade e comunicados de alteração ou de cancelamento de um edital. Não tem datas.
    O edital é lido com os seus comunicados (que mudam datas de cursos); um edital cancelado não é lido e as suas
    turmas passam a Rever. Os editais do Programa Senac Aprendiz ficam de fora (as vagas são das empresas)."""
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    cartoes = re.findall(r'<h5 class="card-title">(.*?)</h5>.*?href="([^"]+)"', html, flags=re.S)
    if not cartoes:
        raise ValueError("nenhum cartão de edital na página")
    ano = hoje_ceara()[:4]
    grupos = {}
    for titulo, href in cartoes:
        titulo = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", titulo))).strip()
        if re.search(r"aprendiz", titulo, flags=re.I):
            continue
        m = re.search(r"EDITAL\D*?N\s*[ºo°]\s*0*(\d+)[\s\-/.]+(\d{4})", titulo, flags=re.I)
        if not m or m.group(2) != ano:
            continue
        url = href if href.startswith("http") else "https://psg.pi.senac.br" + href
        g = grupos.setdefault(int(m.group(1)), {"edital": "", "titulo": "", "avisos": [], "cancelado": False})
        if re.match(r"\s*COMUNICADO", titulo, flags=re.I):
            g["avisos"].append(url)
            g["cancelado"] = g["cancelado"] or bool(re.search(r"cancelamento", titulo, flags=re.I))
        elif not g["edital"]:
            g["edital"], g["titulo"] = url, titulo
    editais = []
    for n, g in sorted(grupos.items(), reverse=True):
        if not g["edital"]:
            continue
        editais.append({"id": f"senac-pi-{ano}-{n}", "number": f"{n:03d}", "published_at": "",
                        "updated_at": g["edital"].rsplit("/", 1)[-1] + f"|{len(g['avisos'])}",
                        "title": g["titulo"], "pagina": g["edital"], "padrao": re.escape(g["edital"]),
                        "aditivo": False, "cancelado": g["cancelado"], "avisos": sorted(g["avisos"]),
                        "documents": [{"type": "edital", "mime_type": "application/pdf", "url": g["edital"]}]})
    return editais


def datas_do_texto(t, ano_padrao):
    """Todas as datas escritas num texto: «23/03/2026» e «13 de Novembro de 2026» (sem ano: o ano seguinte escrito)."""
    datas = set()
    for d, m, a in re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", t):
        try:
            datas.add(datetime.date(int(a), int(m), int(d)).isoformat())
        except ValueError:
            pass
    for d, mes, a in re.findall(r"(\d{1,2})\s+de\s+([a-zçA-ZÇ]+)(?:\s+de\s+(\d{4}))?", t):
        mes = mes.lower()
        if mes in MESES:
            try:
                datas.add(datetime.date(int(a or ano_padrao), MESES[mes], int(d)).isoformat())
            except ValueError:
                pass
    return datas


def listar_senai_pi(fonte):
    """SENAI Piauí: a página dos cursos técnicos de gratuidade (fiepi.com.br) tem um bloco por processo seletivo,
    separado por uma linha, com o período de inscrição escrito no bloco, o edital, as retificações e as listas de
    aprovados. Só entram os blocos com alguma data de hoje em diante; o período vem sempre do próprio edital e tem
    de coincidir com uma data escrita no bloco (segunda prova)."""
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    inicio = html.find('id="id_div_content"')
    if inicio < 0:
        raise ValueError("conteúdo da página não encontrado")
    inicio = html.find(">", inicio) + 1
    fim = html.find("</main>", inicio)
    hoje = hoje_ceara()
    editais = []
    for bloco in re.split(r"<hr\s*/?>", re.sub(r"<h2.*?</h2>", " ", html[inicio:fim if fim > 0 else None], flags=re.S)):
        texto = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", bloco))).strip()
        datas = datas_do_texto(texto, hoje[:4])
        if not datas or max(datas) < hoje:
            continue
        docs = [("https://fiepi.com.br" + h if h.startswith("/") else h,
                 _html.unescape(re.sub(r"<[^>]+>", "", r)).strip())
                for h, r in re.findall(r'<a href="([^"]+\.pdf)"[^>]*>(.*?)</a>', bloco, flags=re.S | re.I)]
        edital = next((u for u, r in docs if re.search(r"edital", r, flags=re.I)
                       and not re.search(r"retific|lista|aprovad|cancel|resultado", r, flags=re.I)), "")
        if not edital:
            continue
        avisos = [u for u, r in docs if re.search(r"retific|errata|aditivo|cancel|prorroga", r, flags=re.I)]
        m_titulo = re.match(r"(.{10,150}?)\s+O\s+(?:SERVI|DIRETOR|SENAI)", texto, flags=re.I)
        titulo = (m_titulo.group(1) if m_titulo else texto[:150]).strip()
        num = re.sub(r"[^a-z0-9]+", "-", edital.rsplit("/", 1)[-1].lower())[:60]
        editais.append({"id": f"senai-pi-{num}", "number": num, "published_at": "",
                        "updated_at": edital.rsplit("/", 1)[-1] + f"|{len(avisos)}",
                        "title": titulo, "pagina": edital, "padrao": re.escape(edital), "aditivo": False,
                        "avisos": avisos, "datas_pagina": sorted(datas),
                        "documents": [{"type": "edital", "mime_type": "application/pdf", "url": edital}]})
    return editais


def listar_senac_al(fonte):
    """Senac Alagoas: a página «Editais» (psg.al.senac.br/editais) tem um cartão por edital (article.editais-item)
    com o título, o selo «EDITAL ABERTO»/«EDITAL ENCERRADO», o tipo (Qualificação, Técnico, Aprendizagem) e a
    cidade. Entram só os abertos que não são de Aprendizagem (essas vagas são para empresas). A página de cada
    edital lista o PDF do edital e os comunicados (lidos juntos, no fim do texto). O período de inscrição vem
    sempre do próprio PDF; o selo «aberto» da lista não é usado para decidir a situação."""
    base_site = "https://psg.al.senac.br"
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    cartoes = re.findall(r'<article class="editais-item">(.*?)</article>', html, flags=re.S)
    if not cartoes:
        raise ValueError("cartões de editais não encontrados na página")
    mes_atual = hoje_ceara()[:7]
    mes_anterior = (datetime.date.fromisoformat(mes_atual + "-01") - datetime.timedelta(days=1)).isoformat()[:7]
    editais = []
    for c in cartoes:
        titulo = _html.unescape(re.sub(r"<[^>]+>", "", (re.search(r"<h3>(.*?)</h3>", c, flags=re.S) or [None, ""])[1])).strip()
        if "status-open" not in c:
            continue
        etiquetas = [_html.unescape(x).strip() for x in re.findall(r'<span class="yellow">(.*?)</span>', c, flags=re.S)]
        if any(re.match(r"aprendizagem", x, flags=re.I) for x in etiquetas):
            continue
        m = re.search(r'href="([^"]+)"', c)
        if not m:
            continue
        pagina_edital = m.group(1) if m.group(1).startswith("http") else base_site + m.group(1)
        ph = baixar(pagina_edital, timeout=60).decode("utf-8", "replace")
        docs = [(h if h.startswith("http") else base_site + h, _html.unescape(re.sub(r"<[^>]+>", " ", r)).strip())
                for h, r in re.findall(r'<a href="([^"]+\.pdf)"[^>]*>(.*?)</a>', ph, flags=re.S | re.I)]
        if not docs:
            continue
        edital = next((u for u, r in docs if not re.search(r"comunicado|retifica|errata|aditivo|resultado|lista", r, flags=re.I)), docs[0][0])
        avisos = [u for u, r in docs if u != edital and re.search(r"comunicado|retifica|errata|aditivo|prorroga|cancel", r, flags=re.I)]
        mm = re.search(r"/uploads/(20\d{2})/(\d{2})/", edital)
        pub = "" if mm and f"{mm.group(1)}-{mm.group(2)}" in (mes_atual, mes_anterior) else (
            f"{mm.group(1)}-{mm.group(2)}-01" if mm else "")
        num = re.sub(r"[^a-z0-9]+", "-", edital.rsplit("/", 1)[-1].lower())[:70]
        editais.append({"id": f"senac-al-{num}", "number": num, "published_at": pub,
                        "updated_at": "|".join(u.rsplit("/", 1)[-1] for u, _ in docs),
                        "title": f"{titulo} | {' | '.join(etiquetas)}", "pagina": edital,
                        "padrao": re.escape(edital), "aditivo": False, "avisos": avisos,
                        "documents": [{"type": "edital", "mime_type": "application/pdf", "url": edital}]})
    return editais


EDITAL_GERAL_AM = ("https://am.senac.br/wp-content/uploads/2026/01/"
                   "EDITAL-001_2026_Programa-Senac-de-Gratuidade_PSG_Senac-Amazonas.doc.pdf")
TRECHOS_AM = [
    "As vagas gratuitas descritas no anexo II deste Edital, e conforme publicação de abertura de vagas no decorrer do "
    "ano de 2026, são destinadas a pessoas de baixa renda",
    "Possuir renda familiar per capita de até 2,0 salários mínimos da federação",
    "As vagas destinadas ao Programa Senac de Gratuidade - PSG, divulgadas nas aberturas publicadas no site, serão "
    "preenchidas por ordem de inscrição",
]


def listar_senac_am(fonte):
    """Senac Amazonas: a «Consulta de Vagas» (filtro «Aberto») lista as aberturas de vagas com a data de publicação;
    a página de cada uma tem o PDF da abertura e, à parte, «Comunicados» e «Erratas» (lidos juntos, no fim do texto).
    A gratuidade, a renda e a ordem de inscrição estão no edital geral do PSG 2026: os três trechos são conferidos
    por código nesse edital a cada leitura e juntados ao texto de cada abertura; se algum faltar, não se junta."""
    trechos = []
    try:
        texto_geral = re.sub(r"\s+", " ", texto_do_documento(baixar(EDITAL_GERAL_AM, timeout=90), "application/pdf"))
        conferidos = [t for t in TRECHOS_AM if citacao_valida(t, texto_geral)]
        if len(conferidos) == len(TRECHOS_AM):
            trechos = [(f"TRECHOS DO EDITAL GERAL DO PSG 2026 DO SENAC AMAZONAS ({EDITAL_GERAL_AM}), conferidos por "
                        "código", "\n".join(f"«{t}»" for t in conferidos))]
        else:
            print(f"  ! Senac AM: só {len(conferidos)} de {len(TRECHOS_AM)} trechos encontrados no edital geral")
    except Exception as ex:  # noqa: BLE001
        print(f"  ! Senac AM: edital geral ilegível ({type(ex).__name__})")
    editais = []
    for pag in range(1, 6):
        url = fonte["lista"] + (f"page/{pag}/" if pag > 1 else "") + "?ordem_ano=desc&situacao=aberto"
        try:
            html = baixar(url, timeout=60).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            break
        itens = re.findall(r'href="(https://am\.senac\.br/consulta-de-vaga/[^"]+)"', html)
        datas = re.findall(r"(20\d{2}-\d{2}-\d{2})", html)
        if not itens:
            break
        vistos_pag = []
        for i in itens:
            if i not in vistos_pag:
                vistos_pag.append(i)
        for pagina in vistos_pag:
            if not re.search(r"inscricoes-abertas", pagina):
                continue
            try:
                ph = baixar(pagina, timeout=60).decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                continue
            pub = (re.search(r"(20\d{2}-\d{2}-\d{2})", ph) or [None, ""])[1]
            partes = re.split(r"<span>\s*(Aprovados|Comunicados|Erratas)\s*</span>", ph)
            pdfs = lambda t: [_html.unescape(u) for u in re.findall(r'href="([^"]+\.pdf)"', t, flags=re.I)]
            principal = pdfs(partes[0])
            if not principal:
                continue
            edital = principal[-1]
            avisos = []
            for rotulo, bloco in zip(partes[1::2], partes[2::2]):
                if rotulo in ("Comunicados", "Erratas"):
                    avisos += [u for u in pdfs(bloco.split("</div>")[0]) if u != edital]
            titulo = _html.unescape(re.sub(r"<[^>]+>", "", (re.search(r"<title>(.*?)</title>", ph, flags=re.S) or [None, ""])[1])).split("|")[0].strip()
            num = re.sub(r"[^a-z0-9]+", "-", pagina.rstrip("/").rsplit("/", 1)[-1])[:70]
            editais.append({"id": f"senac-am-{num}", "number": num, "published_at": pub,
                            "updated_at": "|".join(u.rsplit("/", 1)[-1] for u in [edital] + avisos),
                            "title": titulo, "pagina": edital, "padrao": re.escape(edital), "aditivo": False,
                            "avisos": avisos, "trechos": trechos,
                            "documents": [{"type": "edital", "mime_type": "application/pdf", "url": edital}]})
        if "situacao=aberto" not in html or f"page/{pag + 1}/" not in html:
            break
    return editais


def listar_senac_ro(fonte):
    """Senac Rondônia: os editais do PSG e as retificações são PDFs no WordPress do site; a API pública de média
    (wp-json/wp/v2/media?search=Edital-PSG) lista-os com a data de publicação. Agrupa-se por número (NN.AAAA): o
    edital é a versão mais recente do «Edital-PSG-NN.AAAA…» e as «Retificação» vão como avisos (lidas no fim)."""
    dados = json.loads(baixar(fonte["api"], timeout=60).decode("utf-8"))
    grupos = {}
    for d in dados:
        url, data = d.get("source_url", ""), (d.get("date") or "")[:10]
        nome = urllib.parse.unquote(url.rsplit("/", 1)[-1])
        m = re.search(r"PSG[-_ ](\d{1,2})\.(\d{4})", nome)
        if not m or not url.lower().endswith(".pdf"):
            continue
        g = grupos.setdefault(f"{int(m.group(1)):02d}/{m.group(2)}", {"edital": "", "data": "", "avisos": [], "pub": ""})
        if re.search(r"retifica", nome, re.I):
            g["avisos"].append((data, url))
        elif re.match(r"Edital[-_ ]PSG", nome, re.I) and data >= g["data"]:
            g.update({"edital": url, "data": data, "pub": g["pub"] or data})
        if re.match(r"Edital[-_ ]PSG", nome, re.I):
            g["pub"] = min(x for x in [g["pub"], data] if x)
    editais = []
    for num, g in grupos.items():
        if not g["edital"]:
            continue
        avisos = [u for _, u in sorted(g["avisos"])]
        editais.append({"id": f"senac-ro-{num.replace('/', '-')}", "number": num, "published_at": g["pub"],
                        "updated_at": "|".join(u.rsplit("/", 1)[-1] for u in [g["edital"]] + avisos),
                        "title": f"Edital PSG nº {num} – Senac Rondônia", "pagina": g["edital"],
                        "padrao": re.escape(g["edital"]), "aditivo": False, "avisos": avisos,
                        "documents": [{"type": "edital", "mime_type": "application/pdf", "url": g["edital"]}]})
    return editais


def listar_senac_ap(fonte):
    """Senac Amapá: a página do PSG (ap.senac.br/psg) lê a lista pública cms.ap.senac.br/api/v1/selection-processes
    e, para cada processo, /selection-processes/{id} traz os documentos (edital e erratas, PDFs em
    cms.ap.senac.br/storage/). ATENÇÃO (25/11/2026): estas respostas trazem também dados pessoais de funcionários do
    Senac AP (campo «people»: nome, CPF, nascimento, telefone, morada). Só se leem número, nome, datas e a lista de
    documentos (título e ficheiro); nada mais é lido, impresso ou guardado."""
    lista = json.loads(baixar(fonte["api"], timeout=60).decode("utf-8"))
    lista = lista.get("data", lista) if isinstance(lista, dict) else lista
    corte = (datetime.date.fromisoformat(hoje_ceara()) - datetime.timedelta(days=DIAS_RECENTES)).isoformat()
    editais = []
    for p in lista:
        criado = str(p.get("created_at") or "")[:10]
        mexido = str(p.get("updated_at") or "")[:10]
        if max(criado, mexido) < corte or str(p.get("type") or "") != "G":
            continue
        try:
            det = json.loads(baixar(f"{fonte['api']}/{int(p['id'])}", timeout=60).decode("utf-8"))
        except Exception:  # noqa: BLE001
            continue
        det = det.get("data", det) if isinstance(det, dict) and "documents" not in det else det
        docs = [(str(d.get("title") or ""), "https://cms.ap.senac.br/storage/" + str(d.get("filename") or ""),
                 str(d.get("published_at") or "")[:10])
                for d in (det.get("documents") or []) if str(d.get("filename") or "").lower().endswith(".pdf")]
        # a data que conta é a do documento mais recente (uma errata pode prorrogar a inscrição)
        criado = max([criado] + [dt for _, _, dt in docs if dt])
        docs = [(t, u) for t, u, _ in docs]
        principal = [u for t, u in docs if re.match(r"\s*EDITAL", t, re.I)] or [u for t, u in docs]
        if not principal:
            continue
        edital = principal[0]
        avisos = [u for t, u in docs if u != edital and re.search(r"errata|retifica|aditivo|prorroga|comunicado", t, re.I)]
        num = re.sub(r"\s*-\s*PSG\s*$", "", str(p.get("number") or "")).strip()
        editais.append({"id": f"senac-ap-{int(p['id'])}", "number": num, "published_at": criado,
                        "updated_at": "|".join(u.rsplit("/", 1)[-1] for u in [edital] + avisos),
                        "title": re.sub(r"\s+", " ", str(p.get("name") or ""))[:200], "pagina": edital,
                        "padrao": re.escape(edital), "aditivo": False, "avisos": avisos,
                        "documents": [{"type": "edital", "mime_type": "application/pdf", "url": edital}]})
    return editais


def listar_senai_ap(fonte):
    """SENAI Amapá: a página «Oferta de cursos» (Joomla) lista os editais de cursos gratuitos, do mais novo para o
    mais antigo: um título <h3> «Edital de Cursos Gratuitos nº NNN/AAAA» e, por baixo, uma linha por documento
    («Oferta de curso – …», «RETIFICAÇÃO – …», «Resultado …») com um link «Confira aqui!». Cada linha tem também um
    link vazio copiado por engano (aponta sempre para o mesmo PDF): só contam os links com texto. A data vem do nome
    do ficheiro (…_AAAAMMDDhhmm…pdf) quando existe; editais de anos anteriores ficam de fora."""
    pagina_html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    ano_atual = hoje_ceara()[:4]
    editais = []
    partes = re.split(r"<h3[^>]*>", pagina_html)
    for bloco in partes[1:]:
        titulo_h3 = re.sub(r"<[^>]+>", " ", bloco.split("</h3>", 1)[0])
        titulo_h3 = re.sub(r"\s+", " ", _html.unescape(titulo_h3)).strip()
        m = re.search(r"Cursos Gratuitos\s+n[º°o]\.?\s*(\d{1,3})/(\d{4})", titulo_h3, re.I)
        if not m or m.group(2) < str(int(ano_atual) - 1):
            continue
        num = f"{int(m.group(1)):02d}/{m.group(2)}"
        corpo = bloco.split("</h3>", 1)[1] if "</h3>" in bloco else ""
        principal, avisos, rotulo_principal = "", [], ""
        for p_html in re.findall(r"<p[^>]*>(.*?)</p>", corpo, flags=re.S):
            texto_p = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", p_html))).strip()
            links = [(re.sub(r"<[^>]+>", "", t).strip(), u) for u, t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', p_html, flags=re.S)]
            links = [urllib.parse.urljoin(fonte["lista"], _html.unescape(u)) for t, u in links if t]
            if not links:
                continue
            if re.match(r"(Oferta de curso|Edital de abertura)", texto_p, re.I) and not principal:
                principal, rotulo_principal = links[-1], texto_p
            elif re.search(r"retifica|errata|aditivo|prorroga", texto_p, re.I):
                avisos.append(links[-1])
        if not principal:
            continue
        datas = []
        for u in [principal] + avisos:
            md = re.search(r"_(20\d{2})(\d{2})(\d{2})\d{4,}", urllib.parse.unquote(u))
            if md:
                datas.append(f"{md.group(1)}-{md.group(2)}-{md.group(3)}")
        pub = max(datas) if datas else ""
        if not pub and m.group(2) != ano_atual:
            continue
        editais.append({"id": f"senai-ap-{num.replace('/', '-')}", "number": num, "published_at": pub,
                        "updated_at": "|".join(u.rsplit("/", 1)[-1] for u in [principal] + avisos),
                        "title": f"{titulo_h3} – {rotulo_principal[:150]}", "pagina": principal,
                        "padrao": re.escape(principal), "aditivo": False, "avisos": avisos,
                        "documents": [{"type": "edital", "mime_type": "application/pdf", "url": principal}]})
        if len(editais) >= 8:
            break
    return editais


FIEAM = "https://fieam.org.br/senai/wp-content/uploads/sites/16/"
ESTADO_CHAMADAS_AM = "estado/senai_am_chamadas.json"
FRASE_GRATUIDADE_SENAI_AM = "Os cursos ofertados serão 100% gratuitos"


def _pdf_existe(url):
    """Os PDFs da FIEAM abrem a partir do GitHub (as páginas não: desafio da Cloudflare); um nome que não existe
    devolve 404."""
    try:
        dados = baixar(url, timeout=40)
    except Exception:  # noqa: BLE001
        return None
    return dados if dados[:5] == b"%PDF-" else None


def listar_senai_am(fonte):
    """SENAI Amazonas: abre 2 ou 3 «Chamadas Públicas» de gratuidade por ano (Manaus; inscrição de 2 dias por
    formulário, por ordem de inscrição). As páginas do site da FIEAM estão atrás de um desafio da Cloudflare e não
    abrem a partir do GitHub, mas os PDFs abrem. Por isso procuram-se os PDFs da chamada seguinte pelos nomes que o
    SENAI AM usa (ex.: 2026/08/Chamada-Publica-GEP-03-2026-Cursos-Gratuitos-SENAI-Manaus.pdf) nas pastas do mês
    anterior, do atual e do seguinte, e a «Programação de cursos» pelos nomes já vistos (Programacao-da-Gratuidade-
    SENAI-AM-1-2026, Programacao-Gratuidade-SENAI-AM-2-2026-1, Programacao_Gratuidade_SENAI-AM-3-2026-2). Se a
    chamada aparecer e a programação não, abre-se uma pendência (o Claude encontra o PDF pelo navegador e junta-o
    em «programacoes» do estado). O vigia (vigiar.py) avisa também se houver notícias da chamada sem PDF achado."""
    est = ler_json(ESTADO_CHAMADAS_AM, {"ultima": [2026, 3], "chamadas": {}, "programacoes": {}})
    hoje_d = datetime.date.fromisoformat(hoje_ceara())
    pastas = []
    for dm in (-1, 0, 1):
        m = hoje_d.month + dm
        a = hoje_d.year + (m - 1) // 12
        pastas.append(f"{a}/{(m - 1) % 12 + 1:02d}")
    ano, n = est["ultima"]
    candidatos = [(ano, n)] + ([(ano, n + 1)] if n < 4 else []) + [(ano + 1, 1)]
    editais = []
    for a, k in candidatos:
        chave_ch = f"{k:02d}-{a}"
        url_ch = est["chamadas"].get(chave_ch)
        if not url_ch:
            for pasta in pastas:
                for suf in ("", "-1", "-2"):
                    u = f"{FIEAM}{pasta}/Chamada-Publica-GEP-{k:02d}-{a}-Cursos-Gratuitos-SENAI-Manaus{suf}.pdf"
                    if _pdf_existe(u):
                        url_ch = u
                        break
                if url_ch:
                    break
            if not url_ch:
                continue
            est["chamadas"][chave_ch] = url_ch
            est["vista_em"] = hoje_d.isoformat()
            if [a, k] > list(est["ultima"]):
                est["ultima"] = [a, k]
            print(f"  · SENAI AM: Chamada Pública {k:02d}/{a} encontrada: {url_ch}")
        if chave_ch in est.get("encerradas", []) and not os.environ.get("SECO"):
            continue  # chamada já fechada quando o leitor nasceu (só serve de ensaio)
        url_pg = est["programacoes"].get(chave_ch)
        if not url_pg:
            pasta_ch = url_ch[len(FIEAM):len(FIEAM) + 7]
            for pasta in [pasta_ch] + [p for p in pastas if p != pasta_ch]:
                for sep in ("-", "_"):
                    for da in ("", f"da{sep}"):
                        for suf in ("", "-1", "-2", "-3"):
                            u = f"{FIEAM}{pasta}/Programacao{sep}{da}Gratuidade{sep}SENAI-AM-{k}-{a}{suf}.pdf"
                            if _pdf_existe(u):
                                url_pg = u
                                break
                        if url_pg:
                            break
                    if url_pg:
                        break
                if url_pg:
                    break
            if url_pg:
                est["programacoes"][chave_ch] = url_pg
            else:
                print(f"  ! SENAI AM: a programação da Chamada {k:02d}/{a} não foi encontrada pelos nomes conhecidos")
                try:
                    b = Base()
                    registar_pendencia(b, f"SENAI Amazonas: saiu a Chamada Pública {k:02d}/{a}, mas o PDF da "
                                          "«Programação de cursos» tem um nome novo e a rotina não o encontrou.",
                                       "Peça ao Claude para abrir fieam.org.br/senai/chamada-publica/ no navegador e "
                                       "juntar o link da programação ao estado (estado/senai_am_chamadas.json).",
                                       url_ch, origem="senac_ma.py")
                    b.guardar()
                except Exception:  # noqa: BLE001
                    pass
                continue
        partes = fonte.get("partes", 1)
        for parte in range(1, partes + 1):
            editais.append({"id": f"senai-am-{chave_ch}-p{parte}", "number": f"{k:02d}/{a} (parte {parte})",
                            "published_at": "",
                            "updated_at": url_ch.rsplit("/", 1)[-1] + "|" + url_pg.rsplit("/", 1)[-1],
                            "title": f"Chamada Pública nº {k:02d}/{a} - Vagas gratuitas nos Cursos de Qualificação "
                                     "Profissional e Aperfeiçoamento Profissional (SENAI Amazonas, Manaus)",
                            "pagina": url_ch, "padrao": re.escape(url_ch), "aditivo": False,
                            "extras": [("Programação de cursos", url_pg, (parte, partes))],
                            "documents": [{"type": "edital", "mime_type": "application/pdf", "url": url_ch}]})
    if not os.environ.get("SECO"):
        gravar_json(ESTADO_CHAMADAS_AM, est)
    return editais


def listar_senai_al(fonte):
    """SENAI Alagoas: a página «Edital Gratuidade» (al.senai.br/edital-gratuidade/) tem um bloco por edital
    (<section class="list-editais">), do mais novo para o mais antigo, com «Período de inscrição», «Local para
    inscrição» (muitas vezes um formulário Google), «Público-alvo», «Início das aulas» e os PDFs (edital,
    comunicados, listas de aprovados). Entram os editais cujo período de inscrição ainda não acabou (ou, sem
    período legível, os publicados neste mês ou no anterior). O texto do bloco da página vai junto com o PDF, no
    fim, para as frases poderem ser conferidas também ali."""
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    blocos = re.split(r'<section class="list-editais', html)[1:]
    if not blocos:
        raise ValueError("blocos de editais não encontrados na página")
    hoje = hoje_ceara()
    mes_atual = hoje[:7]
    mes_anterior = (datetime.date.fromisoformat(mes_atual + "-01") - datetime.timedelta(days=1)).isoformat()[:7]
    editais = []
    for b in blocos[:15]:
        titulo = _html.unescape(re.sub(r"<[^>]+>", "", (re.search(r"<h2[^>]*>(.*?)</h2>", b, flags=re.S) or [None, ""])[1])).strip()
        texto = _html.unescape(re.sub(r"[ \t\xa0]+", " ", re.sub(r"<(?:/p|br|/li|/h\d)[^>]*>", "\n", b)))
        texto = re.sub(r"<[^>]+>", " ", texto)
        texto = "\n".join(l.strip() for l in texto.splitlines() if l.strip() and not l.strip().endswith('">'))
        segunda = [x.start() for x in re.finditer(r"EDITAL DE GRATUIDADE", texto)]
        if len(segunda) > 1:
            texto = texto[:segunda[1]]  # o bloco repete o texto (versão para telemóvel)
        docs = [(h, _html.unescape(re.sub(r"<[^>]+>", " ", r)).strip())
                for h, r in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', b, flags=re.S | re.I)]
        if not docs:
            continue
        m = re.search(r"Per[ií]odo de inscri[çc][ãa]o:?\s*(\d{2}/\d{2}/\d{4})(?:\s*[aàá]\s*(\d{2}/\d{2}/\d{4}))?", texto, flags=re.I)
        fim = ini_p = ""
        if m:
            d, mm_, a = (m.group(2) or m.group(1)).split("/")
            fim = f"{a}-{mm_}-{d}"
            d, mm_, a = m.group(1).split("/")
            ini_p = f"{a}-{mm_}-{d}"
        edital = next((u for u, _ in docs if not re.search(r"lista|aprovad|resultado|classifica|comunicado|retifica|errata|aditivo",
                                                            u.rsplit("/", 1)[-1], flags=re.I)), docs[0][0])
        mm = re.search(r"/uploads/(20\d{2})/(\d{2})/", edital)
        recente = bool(mm) and f"{mm.group(1)}-{mm.group(2)}" in (mes_atual, mes_anterior)
        if (fim and fim < hoje) or (not fim and not recente):
            continue
        avisos = [u for u, _ in docs if u != edital and re.search(r"comunicado|retifica|errata|aditivo|prorroga|cancel",
                                                                   u.rsplit("/", 1)[-1], flags=re.I)]
        num = re.sub(r"[^a-z0-9]+", "-", titulo.lower()).strip("-")[:40] or re.sub(r"[^a-z0-9]+", "-", edital.rsplit("/", 1)[-1].lower())[:60]
        editais.append({"id": f"senai-al-{num}", "number": titulo, "published_at": "" if recente else (
                            f"{mm.group(1)}-{mm.group(2)}-01" if mm else ""),
                        "updated_at": "|".join(u.rsplit("/", 1)[-1] for u, _ in docs) + f"|{fim}",
                        "title": titulo, "pagina": fonte["lista"], "padrao": re.escape(edital), "aditivo": False,
                        "avisos": avisos, "texto_pagina": texto[:2500],
                        **({"periodo_lista": (ini_p, fim)} if m and m.group(2) else {}),
                        "documents": [{"type": "edital", "mime_type": "application/pdf", "url": edital}]})
    return editais


# SENAI BA (23/11/2026): a fonte foi testada e retirada de FONTES: a tabela do edital, extraída do PDF, perde a ligação
# entre município, curso e turno (células unidas), por isso as turmas não podem ser provadas linha a linha. O processo
# seletivo entrou como um curso único (C-1baeee72) e vigiar.py avisa quando houver edital novo. A função fica para uma
# leitura futura (ex.: se o SENAI BA publicar a tabela noutro formato).
def listar_senai_ba(fonte):
    """SENAI Bahia: a página «Informações gerais» do site dos cursos técnicos (tecnico.senaibahia.com.br) tem o Edital
    Oficial do processo seletivo do semestre, os aditivos (retificações) e o Regulamento do Programa de Bolsas. O edital
    é lido com os aditivos no fim (prevalecem) e o regulamento como documento ligado (é onde está a frase das bolsas
    integrais). Um único edital por semestre; os aditivos novos fazem-no reler."""
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    docs = [(h, _html.unescape(re.sub(r"<[^>]+>", " ", r)).strip())
            for h, r in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', html, flags=re.S | re.I)]
    edital = next((u for u, r in docs if re.search(r"edital oficial", r, re.I)), "")
    if not edital:
        raise ValueError("link do edital oficial não encontrado na página")
    avisos = [u for u, r in docs if re.search(r"aditivo|retifica", r, re.I)]
    regulamento = next((u for u, r in docs if re.search(r"regulamento", r, re.I)), "")
    nome = edital.rsplit("/", 1)[-1]
    return [{"id": "senai-ba-" + re.sub(r"[^a-z0-9]+", "-", nome.lower())[:60], "number": nome, "published_at": "",
             "updated_at": "|".join(u.rsplit("/", 1)[-1] for u in [edital] + avisos), "title": "Processo Seletivo Cursos Técnicos SENAI Bahia",
             "pagina": fonte["lista"], "padrao": re.escape(edital), "aditivo": False, "avisos": avisos,
             "extras": [("Regulamento do Programa de Bolsas", regulamento)] if regulamento else [],
             "documents": [{"type": "edital", "mime_type": "application/pdf", "url": edital}]}]


def listar_senai_pe(fonte):
    """SENAI Pernambuco: a página «Editais» (pe.senai.br) tem blocos «GRATUIDADE | QUALIFICAÇÃO - Em andamento» e
    «GRATUIDADE | APERFEIÇOAMENTO - Em andamento»; dentro de cada bloco, o nome da unidade (em negrito) e, por baixo,
    os PDFs: «Edital de Abertura – …», erratas, notas de cancelamento e listas de classificados. A data de publicação
    vem do nome do ficheiro (…_AAAAMMDDhhmmss….pdf) ou, se não tiver, do mês da pasta de upload. Erratas e notas da
    mesma unidade são lidas junto com o edital a que se referem (pelo nome do curso); se não disserem qual, com
    todos os editais dessa unidade publicados até 30 dias antes (o leitor manda essas turmas para Rever)."""
    html = baixar(fonte["lista"], timeout=60).decode("utf-8", "replace")
    blocos = re.findall(r'<h2 class="info__description__title">(.*?)</h2>\s*<div class="info__description__text">(.*?)</div>',
                        html, flags=re.S)
    if not blocos:
        raise ValueError("blocos de editais não encontrados na página")
    editais = []
    for titulo_bloco, corpo in blocos:
        titulo_bloco = _html.unescape(re.sub(r"<[^>]+>", "", titulo_bloco)).strip()
        if not re.match(r"GRATUIDADE\b.*Em andamento", titulo_bloco, flags=re.I):
            continue
        unidade, docs = "", []
        for par in re.findall(r"<p[^>]*>(.*?)</p>", corpo, flags=re.S):
            a = re.search(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', par, flags=re.S | re.I)
            texto = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", par))).strip()
            if not a:
                if texto:
                    unidade = texto
                continue
            url = a.group(1)
            rotulo = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", a.group(2)))).strip()
            m = re.search(r"_(20\d{2})(\d{2})(\d{2})\d*(?:-\d+)?\.pdf$", url)
            if m:
                pub = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            else:
                # sem data no nome: só o mês da pasta de upload. Do mês atual ou do anterior fica sem data (é lido e a
                # data de inscrição vem do próprio PDF); mais antigo, fica com o dia 1 e sai pelo corte dos recentes
                m = re.search(r"/uploads/(20\d{2})/(\d{2})/", url)
                mes_atual = hoje_ceara()[:7]
                mes_anterior = (datetime.date.fromisoformat(mes_atual + "-01") - datetime.timedelta(days=1)).isoformat()[:7]
                pub = "" if m and f"{m.group(1)}-{m.group(2)}" in (mes_atual, mes_anterior) else (
                    f"{m.group(1)}-{m.group(2)}-01" if m else "")
            docs.append({"url": url, "rotulo": rotulo, "pub": pub, "unidade": unidade})
        def assunto(r):
            return chave(re.split(r"\s+[–-]\s+", r, maxsplit=1)[-1]) if re.search(r"\s[–-]\s", r) else ""
        abertura = [d for d in docs if re.match(r"edital\s+de\s+abertura", d["rotulo"], flags=re.I)]
        avisos = [d for d in docs if re.search(r"errata|retifica|aditivo|cancel|prorroga", d["rotulo"], flags=re.I)]
        for d in abertura:
            meus = []
            for av in avisos:
                if av["unidade"] != d["unidade"] or (av["pub"] and d["pub"] and av["pub"] < d["pub"]):
                    continue
                sa, sd = assunto(av["rotulo"]), assunto(d["rotulo"])
                if sa and sd and (sa in sd or sd in sa):
                    meus.append(av["url"])
                elif not sa or not any(assunto(x["rotulo"]) and (assunto(av["rotulo"]) in assunto(x["rotulo"])
                                                             or assunto(x["rotulo"]) in assunto(av["rotulo"]))
                                       for x in abertura if x["unidade"] == av["unidade"]):
                    # aviso que não diz o curso (ex.: «Nota de cancelamento», «Errata – 200 vagas»): vale para os
                    # editais da unidade publicados até 30 dias antes
                    if not (d["pub"] and av["pub"]) or (datetime.date.fromisoformat(av["pub"])
                                                        - datetime.date.fromisoformat(d["pub"])).days <= 30:
                        meus.append(av["url"])
            num = re.sub(r"[^a-z0-9]+", "-", d["url"].rsplit("/", 1)[-1].lower())[:70]
            editais.append({"id": f"senai-pe-{num}", "number": num, "published_at": d["pub"],
                            "updated_at": d["url"].rsplit("/", 1)[-1] + f"|{len(meus)}",
                            "title": f"{titulo_bloco} | {d['unidade']} | {d['rotulo']}", "pagina": d["url"],
                            "padrao": re.escape(d["url"]), "aditivo": False, "avisos": meus,
                            "documents": [{"type": "edital", "mime_type": "application/pdf", "url": d["url"]}]})
    return editais


def numero_alterado(n):
    m = re.match(r"(\d+)", str(n or ""))
    return m.group(1) if m else ""


def main():
    so = os.environ.get("SO_FONTE")  # ex.: SO_FONTE="Senai AM" (ensaios)
    for fonte in FONTES:
        if not so or fonte["nome"] == so:
            correr(fonte)
    return 0


def correr(fonte):
    base = Base()
    cfg = carregar_config(base)
    garantir_aba(base)
    hoje = (os.environ.get("HOJE_ENSAIO") if os.environ.get("SECO") else "") or hoje_ceara()  # ensaio: data simulada
    modelo = cfg.get("modelo_cursos") or "claude-haiku-5-5"
    estado = ler_json(fonte["estado"], {"tratados": {}})
    try:
        editais = {"senai_ma": listar_senai_ma, "senac_pi": listar_senac_pi, "senai_pi": listar_senai_pi, "senai_pe": listar_senai_pe, "senac_al": listar_senac_al, "senai_al": listar_senai_al, "senai_ba": listar_senai_ba, "senac_am": listar_senac_am, "senai_am": listar_senai_am, "senac_ro": listar_senac_ro, "senac_ap": listar_senac_ap, "senai_ap": listar_senai_ap}.get(fonte.get("listar"), listar_ma if fonte.get("api") else listar_ac)(fonte)
    except Exception as e:  # noqa: BLE001
        print(f"{fonte['nome']}: a lista de editais não abriu ({type(e).__name__}: {e}). Nada alterado.")
        editais = []
        registar_pendencia(base, f"{fonte['nome']}: a lista oficial de editais não abriu ({type(e).__name__}).",
                           "Se a página abre no seu navegador e se os editais mudaram de endereço.", fonte["lista"],
                           origem="senac_ma.py")
    corte = (datetime.date.fromisoformat(hoje) - datetime.timedelta(days=DIAS_RECENTES)).isoformat()

    linhas_cursos = [r for r in base.tabela("Cursos") if r.get("ID") and (r.get("Link") or "").startswith(fonte["lista"])]
    cursos, ocultos = {}, set()
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto":
            ocultos.add(chave(r.get("Título", "")))
        else:
            cursos.setdefault(chave(r.get("Título", "")), r["ID"].strip())
    existentes = {t["Link da turma"].strip(): t for t in base.tabela(ABA)
                  if (t.get("Link da turma") or "").startswith(fonte["prefixo_turma"])}

    novas, alteracoes, cursos_novos, historico, custo = [], [], [], [], 0.0
    gratuidade_provada, acessibilidade_provada = {}, {}
    lidos = 0
    for e in editais:
        chave_estado = f"{e.get('id')}|{e.get('updated_at')}"
        feito = estado["tratados"].get(chave_estado)
        # RELER_ABERTOS=1 (usado uma vez, 24/11/2026): volta a ler os editais com inscrições ainda abertas, para guardar
        # campos novos (ex.: a frase de sorteio/ordem de inscrição). CUIDADO: a releitura volta aos dados do edital
        # original e desfaz correções feitas à mão pelos avisos (aconteceu com o Senac AC 135/2026, linhas 93-95 de
        # Turmas, repostas à mão). Por isso já não está no workflow manual.
        if (os.environ.get("RELER_ABERTOS") and isinstance(feito, dict) and feito.get("cursos")
                and (feito.get("inscricao_ate") or "") >= hoje):
            feito = None
        if (e.get("published_at") and e["published_at"][:10] < corte) or (feito and (not isinstance(feito, dict)
                                                                       or feito.get("tentativas", 0) >= MAX_TENTATIVAS
                                                                       or feito.get("cursos"))):
            continue
        docs = e.get("documents") or []
        pagina = e["pagina"]
        # termo aditivo ou aviso de alteração: as turmas do edital alterado vão para Rever
        if e.get("aditivo"):
            n = numero_alterado(e.get("number"))
            nota = f"{hoje}: saiu um termo aditivo ou aviso ao edital nº {n} ({pagina}); confirmar prazos e turmas antes de publicar."
            for link, t in existentes.items():
                if re.search(e["padrao"], link, flags=re.I) and t.get("Estado") == "Publicado":
                    alteracoes.append((t["_linha"], {"Estado": "Rever", "Notas": nota}))
                    historico.append(registo(t, fonte["nome"], "Rever", nota))
            estado["tratados"][chave_estado] = hoje
            continue
        # edital cancelado por comunicado: não se lê, e as turmas que já existiam vão para Rever
        if e.get("cancelado"):
            nota = f"{hoje}: saiu um comunicado de cancelamento do edital nº {e.get('number')}; confirmar antes de publicar."
            for link, t in existentes.items():
                if re.search(e["padrao"], link, flags=re.I) and t.get("Estado") == "Publicado":
                    alteracoes.append((t["_linha"], {"Estado": "Rever", "Notas": nota}))
                    historico.append(registo(t, fonte["nome"], "Rever", nota))
            estado["tratados"][chave_estado] = hoje
            print(f"  · edital nº {e.get('number')}: cancelado por comunicado, não foi lido")
            continue
        if not docs or lidos >= fonte.get("max_por_execucao", MAX_POR_EXECUCAO):
            continue
        doc = docs[0]
        try:
            dados = baixar(doc["url"], timeout=60)
            bruto = texto_do_documento(dados, doc.get("mime_type", ""), fonte.get("extrator") or fonte.get("layout", False))
            if fonte.get("limpar"):
                bruto = re.sub(fonte["limpar"], " ", bruto)  # marcas d'água repetidas em todas as páginas
            texto = recortar(bruto,
                             fonte.get("anexo", r"ANEXO\s+I\b"),
                             fonte.get("max_caracteres", MAX_CARACTERES))
            # comunicados e retificações publicados depois do edital: lidos juntos, no fim do texto
            texto_avisos = ""
            for url in e.get("avisos") or []:
                t_aviso = re.sub(r"[ \t]+", " ", texto_do_documento(baixar(url, timeout=60), "application/pdf", fonte.get("extrator") or False))
                texto_avisos += f"\n\n=== COMUNICADO OU RETIFICAÇÃO PUBLICADO DEPOIS DO EDITAL (prevalece) ===\n{t_aviso.strip()}"
            texto += texto_avisos
            for item in e.get("extras") or []:
                rotulo, url = item[0], item[1]
                t_extra = re.sub(r"[ \t]+", " ", texto_do_documento(baixar(url, timeout=60), "application/pdf",
                                                                   fonte.get("layout", False)))
                if len(item) > 2:
                    # documento longo lido em partes (parte, total), com 6 linhas sobrepostas em cada fronteira, para
                    # a resposta do modelo não ser cortada (SENAI AM: ~95 turmas numa planilha de 7 páginas)
                    parte, total = item[2]
                    ls = t_extra.split("\n")
                    tam = -(-len(ls) // total)
                    t_extra = "\n".join(ls[max(0, (parte - 1) * tam - 6):parte * tam + 6])
                    rotulo += f" (parte {parte} de {total})"
                texto += (f"\n\n=== DOCUMENTO OFICIAL LIGADO AO EDITAL: {rotulo} ===\n"
                          f"{t_extra.strip()[:fonte.get('max_extra', 20000)]}")
            for rotulo, txt in e.get("trechos") or []:
                # trechos de um documento oficial geral, já conferidos por código nesse documento (ex.: o edital
                # geral do PSG 2026 do Senac Amazonas, com a gratuidade e a renda que as aberturas não repetem)
                texto += f"\n\n=== {rotulo} ===\n{txt}"
            if e.get("texto_pagina"):
                texto += f"\n\n=== INFORMAÇÕES DESTE EDITAL NA PÁGINA OFICIAL ({e.get('pagina')}) ===\n{e['texto_pagina']}"
        except Exception as ex:  # noqa: BLE001
            print(f"  ✗ edital {e.get('number')}: documento ilegível ({type(ex).__name__})")
            continue
        if len(texto.strip()) < 500:
            print(f"  ✗ edital {e.get('number')}: o documento não tem texto legível (pode ser digitalizado)")
            estado["tratados"][chave_estado] = hoje
            continue
        try:
            sistema = SISTEMA.replace("Senac Maranhão (Programa Senac de Gratuidade)", fonte["entidade"]).replace(
                "Programa Senac de Gratuidade", fonte.get("programa", "Programa Senac de Gratuidade"))
            if fonte.get("nota"):
                sistema = sistema.replace("\n\nDevolve só JSON", f"\n- {fonte['nota']}\n\nDevolve só JSON")
            m_fonte = fonte.get("modelo", modelo)  # editais com tabelas enormes (SENAI BA) usam outro modelo
            pensar = False if fonte.get("sem_raciocinio") else None
            resposta, uso = claude(m_fonte, sistema, f"Título do edital: {e.get('title')}\n\nTexto do edital:\n{texto}",
                                   max_tokens=fonte.get("max_tokens", 6000), pensar=pensar)
        except ErroClaude as ex:
            print(f"  ERRO no Claude (edital {e.get('number')}): {ex}")
            continue
        lidos += 1
        custo += custo_estimado(uso, m_fonte)
        res = extrair_json(resposta)
        if not isinstance(res, dict) and "</json>" not in resposta:
            # edital com muitos cursos: a resposta foi cortada a meio; lê-se outra vez com mais espaço
            try:
                resposta, uso = claude(m_fonte, sistema, f"Título do edital: {e.get('title')}\n\nTexto do edital:\n{texto}",
                                       max_tokens=max(16000, fonte.get("max_tokens", 0)), pensar=pensar)
                custo += custo_estimado(uso, m_fonte)
                res = extrair_json(resposta)
            except ErroClaude as ex:
                print(f"  ERRO no Claude (edital {e.get('number')}, segunda leitura): {ex}")
        if not isinstance(res, dict):
            tentativas = (feito.get("tentativas", 0) if isinstance(feito, dict) else 0) + 1
            estado["tratados"][chave_estado] = {"data": hoje, "inscricao_ate": "", "cursos": 0, "tentativas": tentativas}
            print(f"  ? edital {e.get('number')}: resposta ilegível (tentativa {tentativas} de {MAX_TENTATIVAS}; "
                  f"{len(resposta)} caracteres, fim: {re.sub(chr(10), ' ', resposta[-200:])})")
            continue
        # requisito fixo da fonte (ex.: nota do ENEM no SENAI BA): só se a frase estiver no documento
        req = fonte.get("requisito") or {}
        requisito_fixo = req.get("texto", "") if req and citacao_valida(req.get("frase", ""), texto) else ""
        if fonte.get("codigo_turma"):
            # tabela com o nome do curso partido em várias linhas à volta do código da turma (SENAI AM): o modelo
            # junta o nome e a frase deixa de ser literal. A prova passa a ser o próprio texto do PDF: a única linha
            # com o código da turma e as duas linhas antes e depois, onde têm de estar, pela ordem, as palavras do
            # nome; as datas são conferidas depois nessa janela, como em qualquer frase.
            linhas = texto.split("\n")
            for t in res.get("turmas") or []:
                cod = str(t.get("codigo") or "").strip()
                if not re.fullmatch(fonte["codigo_turma"], cod):
                    continue
                idx = [i for i, l in enumerate(linhas) if re.search(rf"(?<![\w.]){re.escape(cod)}(?![\w.])", l)]
                if len(idx) != 1:
                    continue
                janela = "\n".join(linhas[max(0, idx[0] - 2):idx[0] + 3])
                if palavras_em_ordem(str(t.get("curso") or ""), janela.replace("|", " ")):
                    t["frase"] = janela
            # link do formulário de inscrição, igual para todas as turmas (item 1.4 da chamada)
            m_link = re.search(fonte["link_inscricao_regex"], texto) if fonte.get("link_inscricao_regex") else None
            for t in res.get("turmas") or []:
                if m_link and not t.get("link_inscricao"):
                    t["link_inscricao"] = m_link.group(1)
        if fonte.get("prova_janela") and isinstance(res, dict):
            # tabela com o nome do curso, a data e o turno partidos em colunas à volta da linha da carga horária
            # (SENAI AP): a prova é a única janela de linhas do PDF, à volta de uma linha com essa carga horária, que
            # tem as palavras do nome (pela ordem) e a data de início
            linhas_j = texto.split("\n")
            raio = fonte["prova_janela"]
            for t in res.get("turmas") or []:
                ch = re.sub(r"\s", "", str(t.get("carga_horaria") or "")).lower()
                m_ch = re.fullmatch(r"(\d{1,4}(?:\.\d{3})?)h(?:oras)?", ch)
                if not (m_ch and t.get("inicio_aulas") and t.get("curso")):
                    continue
                cands = set()
                for i, l in enumerate(linhas_j):
                    if re.search(rf"(?<![\d.]){re.escape(m_ch.group(1))}\s?h\b", l):
                        jan = "\n".join(linhas_j[max(0, i - raio):i + raio + 1])
                        if palavras_em_ordem(str(t["curso"]), jan.replace("|", " ")) and data_na_frase(t["inicio_aulas"], jan):
                            cands.add(jan)
                if len(cands) == 1:
                    t["frase"] = cands.pop()
        edital, problemas = provar(res, texto, e.get("published_at") or "", fonte.get("inscricao_continua", False),
                                    fonte.get("layout", False), fonte.get("janela_inscricao", 60))
        if e.get("datas_pagina") and edital["fim"] and edital["fim"] not in e["datas_pagina"]:
            # segunda prova: a página oficial também escreve o período de inscrição
            problemas.append(f"o fim da inscrição no documento ({edital['fim']}) não aparece na página oficial")
        if e.get("periodo_lista") and edital["fim"] and edital["fim"] != e["periodo_lista"][1]:
            # segunda prova: a lista oficial também diz até quando há inscrição; têm de coincidir
            problemas.append(f"o fim da inscrição no documento ({edital['fim']}) não coincide com a lista oficial "
                             f"({e['periodo_lista'][1]})")
        if DIAGNOSTICO:
            os.makedirs(DIAGNOSTICO, exist_ok=True)
            with open(os.path.join(DIAGNOSTICO, f"{e.get('id')}.json"), "w", encoding="utf-8") as f:
                json.dump({"edital": e, "texto": texto, "resposta": resposta}, f, ensure_ascii=False, indent=1)
        propostas = len(res.get("turmas") or [])
        if not edital["turmas"]:  # para se perceber no registo da execução porque não ficou nenhum curso
            m = list(re.finditer(r"ANEXO\s+I\b", texto.upper()))
            pos = m[-1].start() if m else -1
            print(f"    texto com {len(texto)} caracteres; Anexo I na posição {pos}: "
                  + re.sub(r"\s+", " ", texto[pos:pos + 1500] if pos >= 0 else texto[-1500:]))
            for t in (res.get("turmas") or [])[:3]:
                print(f"    proposta não comprovada: {str(t)[:300]}")
            if not res.get("turmas"):
                print(f"    resposta sem turmas ({len(resposta)} caracteres): {re.sub(chr(10), ' ', resposta[:700])}")
        print(f"  edital nº {e.get('number')} ({(e.get('published_at') or '')[:10]}): inscrição "
              f"{edital['ini'] or '?'} a {edital['fim'] or '?'}, modo {edital['modo'] or '?'}, "
              f"{len(edital['turmas'])}/{propostas} cursos comprovados" + (f" | {'; '.join(problemas)}" if problemas else ""))
        for t in edital["turmas"]:
            ancora = t['curso'] + ' ' + (t.get('horario') or '')
            if fonte.get("codigo_turma") and re.fullmatch(fonte["codigo_turma"], str(t.get("codigo") or "")):
                ancora = str(t["codigo"])  # o código da turma é único na chamada (SENAI AM)
            elif fonte.get("ancora_com_data"):
                # a mesma chamada tem várias turmas do mesmo curso e horário em meses diferentes (SENAI AM)
                ancora += ' ' + (t.get('inicio_aulas') or '')
            link = f"{pagina}#{re.sub(r'[^a-z0-9]+', '-', chave(ancora)).strip('-')}"
            if link not in existentes and not t.get("horario"):
                # releitura em que o horário não veio: não se cria uma turma nova se o mesmo curso deste edital já
                # existe com horário (a âncora seria outra e a turma ficava repetida no site)
                base_link = f"{pagina}#{re.sub(r'[^a-z0-9]+', '-', chave(t['curso'])).strip('-')}-"
                if any(l.startswith(base_link) for l in existentes):
                    continue
            k = chave(t["curso"])
            if k in ocultos:
                continue
            p = auditar(t, edital, problemas, fonte.get("inicio_opcional", False))
            if e.get("tem_aviso"):
                p.append("o edital tem aviso de prorrogação ou alteração: confirmar prazos e vagas")
            if texto_avisos:
                cursos_nos_avisos = [x for x in edital["turmas"] if chave(x["curso"]) in chave(texto_avisos)]
                # o comunicado nomeia o anexo/cidade que altera (ex.: «ANEXO I – … – ARAPIRACA»): um curso com o
                # mesmo nome noutra cidade não é afetado (Senac AL 19/2026, 23/11/2026)
                outra_cidade = bool(t["cidade"]) and chave(t["cidade"]) not in chave(texto_avisos) and any(
                    x["cidade"] and chave(x["cidade"]) in chave(texto_avisos) for x in edital["turmas"])
                if not cursos_nos_avisos:
                    p.append("o edital tem comunicado ou retificação: confirmar prazos e vagas")
                elif k in chave(texto_avisos) and not outra_cidade and not citacao_valida(t["frase"], texto_avisos):
                    p.append("um comunicado altera este curso e as datas não vieram do comunicado: confirmar")
            ed_t = {**edital, "ini": t["insc_propria"]["ini"], "fim": t["insc_propria"]["fim"],
                    "frase_insc": t["insc_propria"]["frase"], "ate_vagas": False} if t.get("insc_propria") else edital
            if t.get("local_proprio") and not ed_t["modo"]:
                ed_t = {**ed_t, "modo": "presencial", "local": t["local_proprio"]}
            prazo = ed_t["fim"]
            if ed_t.get("ate_vagas"):
                # «até o limite de vagas»: a turma deixa de aparecer na véspera do início das aulas
                prazo = ((datetime.date.fromisoformat(t["inicio_aulas"]) - datetime.timedelta(days=1)).isoformat()
                         if t["inicio_aulas"] else "")
            situacao = "Aberta" if prazo and hoje <= prazo else "Encerrada"
            if situacao == "Aberta" and ed_t.get("ini") and hoje < ed_t["ini"]:
                situacao = "Por abrir"  # a inscrição ainda não começou: fica fora do site até ao dia (23/11/2026)
            campos = {
                "Título na fonte": t["curso"], "Unidade na fonte": t.get("local_curso") or "", "Cidade": t["cidade"],
                "Unidade": "", "Link de matrícula": t.get("link_inscricao") or "", "Início": t["inicio_aulas"], "Fim": t.get("fim_aulas") or "",
                "Horário": t.get("horario") or "", "Dias": str(t.get("dias") or ""), "Vagas": str(t.get("vagas") or ""),
                "Carga horária": str(t.get("carga_horaria") or ""), "Prazo de inscrição": prazo,
                "Idade mínima": "", "Escolaridade": "", "Documentos": "",
                "Mais informações": (f"Inscrições de {data_br(ed_t['ini'])} a {data_br(ed_t['fim'])}"
                                     if ed_t["fim"] else
                                     f"Inscrições a partir de {data_br(edital['ini'])}, até o limite de vagas "
                                     f"(a turma sai do site quando as aulas começam, a {data_br(t['inicio_aulas'])})"
                                     if edital.get("ate_vagas") and t["inicio_aulas"] else ""),
                "Local na fonte": ed_t["local"], "Modo de inscrição": ed_t["modo"], "Situação": situacao,
                "Vagas reservadas": edital["reserva"][:300],
                "Última verificação": hoje, "Falhas seguidas": 0,
                "Evidência": (f"«{ed_t['frase_insc']}» | «{t['frase']}»"
                              + (f" | local: «{ed_t['local']}»" if ed_t["local"] else "")
                              + (f" | vagas: «{edital['selecao'][:200]}»" if edital.get("selecao") else "")
                              + (" | nome do curso corrigido de letras trocadas pelo OCR (90%+ igual)" if t.get("nome_ocr") else ""))[:900],
                "Auditoria": (f"{hoje}: não passou: " + "; ".join(p) + ".") if p else
                f"{hoje}: ok (frases conferidas no documento do edital; datas e horário coerentes).",
            }
            if edital["gratuito"] and (existentes.get(link, {}).get("Curso") or cursos.get(k)):
                gratuidade_provada[(existentes.get(link, {}).get("Curso") or cursos.get(k)).strip()] = str(res.get("gratuidade"))
            if edital["acessibilidade"] and (existentes.get(link, {}).get("Curso") or cursos.get(k)):
                acessibilidade_provada[(existentes.get(link, {}).get("Curso") or cursos.get(k)).strip()] = edital["acessibilidade"]
            if link in existentes:
                if p and existentes[link].get("Estado") == "Publicado":
                    # releitura (ex.: saiu um comunicado) que já não passa na auditoria: a turma volta a Rever
                    alteracoes.append((existentes[link]["_linha"], {**campos, "Estado": "Rever"}))
                    historico.append(registo(existentes[link], fonte["nome"], "Rever", campos["Auditoria"]))
                elif (not p and existentes[link].get("Estado") == "Rever"
                      and not (existentes[link].get("Notas") or "").strip()):
                    # releitura que agora passa na auditoria (ex.: leitura do PDF melhorada): a turma que só estava
                    # em Rever por causa da auditoria automática é publicada (nunca a que uma pessoa ou um aviso
                    # mandou para Rever: essas têm Notas)
                    alteracoes.append((existentes[link]["_linha"], {**campos, "Estado": "Publicado"}))
                    historico.append(registo(existentes[link], fonte["nome"], "Publicado", campos["Auditoria"]))
                else:
                    alteracoes.append((existentes[link]["_linha"], campos))
                continue
            if situacao not in ("Aberta", "Por abrir"):
                continue
            curso = cursos.get(k)
            if not curso:
                titulo = re.sub(r"\s+", " ", t["curso"]).strip()
                titulo = titulo[:1].upper() + titulo[1:].lower() if titulo.isupper() else titulo
                provados = ["internet"] + (["renda"] if edital["renda"] else [])
                novo = {
                    "ID": id_curso(fonte["lista"], titulo), "Estado": "Novo", "Título": titulo[:200],
                    "Entidade": fonte["entidade"], "Link": fonte["lista"], "Página do curso": pagina,
                    "Local": fonte["local"], "Modalidade": "presencial", "País": "BR", "Região": fonte["regiao"],
                    "Cidade": "", "Descrição": "", "Necessidades": necessidades("", titulo),
                    "Perfis": ", ".join(perfis_da_frase(edital["reserva"])) or "todos",
                    "Condição de acesso": "", "Requisitos": requisito_fixo, "Certificado": "desconhecido", "Inscrições até": "",
                    "Início": "", "Duração": (f"{t['carga_horaria']} horas" if re.fullmatch(r"\d+(?:[.,]\d+)?", str(t.get("carga_horaria") or "").strip()) else str(t.get("carga_horaria") or "")), "Link verificado": "SIM",
                    "Primeiro visto": hoje, "Última verificação": hoje, "Origem": "turmas", "Notas": "",
                    "Como me inscrever": "", **VERIFICACAO_INICIAL,
                    "Nota da verificação": f"{hoje}: curso criado a partir do edital nº {e.get('number')} do {fonte['nome']}.",
                    "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
                    "Evidência": (f"gratuito: «{res.get('gratuidade')}»" if edital["gratuito"]
                                  else f"programa: «{res.get('programa')}»" if res.get("programa") else "")
                    + (f" | renda: «{edital['renda']}»" if edital["renda"] else "")
                    + (f" | acessibilidade: «{edital['acessibilidade']}»" if edital["acessibilidade"] else ""),
                    "Campos comprovados": ", ".join((["gratuito"] if edital["gratuito"] else
                                                     ["programa"] if res.get("programa") else []) + provados
                                                    + (["acessibilidade"] if edital["acessibilidade"] else [])),
                    "Renda máxima": edital["renda"][:200], "Precisa de internet": "Não" if edital["modo"] == "presencial" else "",
                    "O que falta confirmar": "" if edital["gratuito"] else SEM_FRASE_GRATUIDADE,
                }
                cursos_novos.append(novo)
                curso = cursos[k] = novo["ID"]
            if any(n["Link da turma"] == link for n in novas):
                continue  # a mesma turma lida em duas partes do documento (linhas sobrepostas)
            novas.append({"ID": id_turma(link), "Curso": curso, "Estado": "Rever" if p else "Publicado",
                          "Link da turma": link, "Primeiro visto": hoje, **campos})
            print(f"  + {t['curso'][:40]} | {t['cidade']} | inscrição até {prazo or '—'} | {situacao}"
                  + (f" | AUDITORIA: {'; '.join(p)}" if p else ""))
        estado["tratados"][chave_estado] = {
            "data": hoje, "inscricao_ate": edital["fim"] or ("até o limite de vagas" if edital.get("ate_vagas") else "")
            or max([x["insc_propria"]["fim"] for x in edital["turmas"] if x.get("insc_propria")] or [""]),
            "cursos": len(edital["turmas"]),
            "tentativas": (feito.get("tentativas", 0) if isinstance(feito, dict) else 0) + 1}
        time.sleep(1)

    # situação das turmas já conhecidas: só pelas datas do documento
    for link, t in existentes.items():
        prazo = (t.get("Prazo de inscrição") or "")[:10]
        if t.get("Situação") == "Aberta" and prazo and prazo < hoje:
            alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje}))
        elif t.get("Situação") == "Por abrir":
            # abre no primeiro dia do período (a data está em «Mais informações»: «Inscrições de dd/mm/aaaa a …»)
            m = re.search(r"Inscrições de (\d{2})/(\d{2})/(\d{4})", t.get("Mais informações") or "")
            ini = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""
            if prazo and prazo < hoje:
                alteracoes.append((t["_linha"], {"Situação": "Encerrada", "Última verificação": hoje}))
            elif ini and ini <= hoje:
                alteracoes.append((t["_linha"], {"Situação": "Aberta", "Última verificação": hoje}))

    # publicar cursos e atualizar a situação de cada curso pelas suas turmas
    turmas_finais = {l: (t.get("Curso"), t.get("Situação"), t.get("Estado")) for l, t in existentes.items()}
    for linha, campos in alteracoes:
        for l, t in existentes.items():
            if t["_linha"] == linha:
                antes = turmas_finais[l]
                turmas_finais[l] = (antes[0], campos.get("Situação", antes[1]), campos.get("Estado", antes[2]))
    for n in novas:
        turmas_finais[n["Link da turma"]] = (n["Curso"], n["Situação"], n["Estado"])
    abertas = {}
    for curso, sit, est in turmas_finais.values():
        if est == "Publicado" and sit == "Aberta":
            abertas[curso] = abertas.get(curso, 0) + 1
    # cursos «por abrir» (regra I3/M5, 25/11/2026; aplicada aqui a 27/11/2026): sem turma aberta, mas com turma
    # publicada cuja inscrição começa nos próximos DIAS_POR_ABRIR dias, com a frase do período no edital
    limite_abertura = (datetime.date.fromisoformat(hoje) + datetime.timedelta(days=DIAS_POR_ABRIR)).isoformat()

    def _ini_frase(t):
        m = re.search(r"Inscrições de (\d{2})/(\d{2})/(\d{4})", t.get("Mais informações") or "")
        f = re.match(r"«([^»]+)»", t.get("Evidência") or "")
        return (f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else "", f.group(1) if f else "")
    info_turma = {l: _ini_frase(t) for l, t in existentes.items()}
    info_turma.update({n["Link da turma"]: _ini_frase(n) for n in novas})
    por_abrir = {}
    for l, (curso, sit, est) in turmas_finais.items():
        ini, fr = info_turma.get(l, ("", ""))
        if est == "Publicado" and sit == "Por abrir" and ini and fr and hoje < ini <= limite_abertura:
            if curso not in por_abrir or ini < por_abrir[curso][0]:
                por_abrir[curso] = (ini, fr, l.split("#")[0])
    nota = (f"{hoje}: publicado automaticamente: turma aberta aprovada na auditoria e edital do Programa Senac de "
            "Gratuidade (sem frase de gratuidade, o site mostra “Gratuidade por confirmar”).")
    for n in cursos_novos:
        if (abertas.get(n["ID"]) or por_abrir.get(n["ID"])) and ("gratuito" in n["Campos comprovados"] or "programa" in n["Campos comprovados"]):
            n["Estado"], n["Nota da verificação"] = "Publicado", nota
    alteracoes_cursos = []
    for r in linhas_cursos:
        if r.get("Estado") == "Oculto" or (r.get("Revisto por pessoa") or "").strip():
            continue
        campos = {}
        comprovados = r.get("Campos comprovados") or ""
        # gratuidade gravada antes da regra de 20/11/2026 só com o nome do programa: passa a «programa»
        lista_prov = [c.strip() for c in comprovados.split(",") if c.strip()]
        if "gratuito" in lista_prov and not gratuidade_comprovada(r):
            lista_prov = ["programa" if c == "gratuito" else c for c in lista_prov]
            comprovados = ", ".join(dict.fromkeys(lista_prov))
            falta = (r.get("O que falta confirmar") or "").replace(SEM_FRASE_GRATUIDADE_ANTIGA, "").strip()
            campos.update({"Campos comprovados": comprovados,
                           "Evidência": (r.get("Evidência") or "").replace("gratuito: «", "programa: «"),
                           "O que falta confirmar": (SEM_FRASE_GRATUIDADE + " " + falta).strip()[:900]
                           if SEM_FRASE_GRATUIDADE not in falta else falta})
        frase = gratuidade_provada.get(r["ID"].strip())
        if frase and "gratuito" not in comprovados:
            comprovados = ", ".join(["gratuito"] + [c for c in comprovados.split(", ") if c])
            campos.update({"Campos comprovados": comprovados,
                           "Evidência": f"gratuito: «{frase}»" + (" | " + r["Evidência"] if r.get("Evidência") else ""),
                           "O que falta confirmar": ""})
        frase_acess = acessibilidade_provada.get(r["ID"].strip())
        if frase_acess and "acessibilidade" not in comprovados.split(", "):
            comprovados = ", ".join([c for c in comprovados.split(", ") if c] + ["acessibilidade"])
            evid = campos.get("Evidência", r.get("Evidência") or "")
            campos.update({"Campos comprovados": comprovados,
                           "Evidência": (evid + " | " if evid else "") + f"acessibilidade: «{frase_acess}»"})
        pa = por_abrir.get(r["ID"].strip())
        nova = "Aberto" if abertas.get(r["ID"].strip()) else "Por abrir" if pa else "Encerrado"
        if nova != r.get("Situação das inscrições"):
            campos["Situação das inscrições"] = nova
        if nova == "Por abrir":
            if (r.get("Inscrições abrem em") or "") != pa[0]:
                campos["Inscrições abrem em"] = pa[0]
            if "abertura" not in comprovados.split(", "):
                comprovados = ", ".join([c for c in comprovados.split(", ") if c] + ["abertura"])
                evid = campos.get("Evidência", r.get("Evidência") or "")
                campos.update({"Campos comprovados": comprovados,
                               "Evidência": ((evid + " | ") if evid else "") + f"abertura: «{pa[1]}» ({pa[2]})"})
        if (r.get("Estado") == "Novo" and r.get("Origem") == "turmas" and (abertas.get(r["ID"].strip()) or pa)
                and ("gratuito" in comprovados or "programa" in comprovados) and not sim(r.get("Mudança a rever"))):
            campos.update({"Estado": "Publicado", "Nota da verificação": nota})
        if campos:
            alteracoes_cursos.append((r["_linha"], campos))

    if os.environ.get("SECO"):
        # ensaio: mostra o que seria escrito e não grava nada (nem a folha nem o estado)
        print(f"  [SECO] {fonte['nome']}: {len(novas)} turmas novas, {len(cursos_novos)} cursos novos, "
              f"{len(alteracoes)} alterações; custo ≈ {round(custo, 3)} USD")
        for t in novas[:2]:
            print("   ", {k: str(v)[:900] for k, v in t.items() if v})
        for c in cursos_novos[:3]:
            print("   ", {k: (c.get(k) or "")[:300] for k in ("Título", "Requisitos", "Evidência", "Campos comprovados")})
        return
    base.atualizar(ABA, alteracoes)
    base.acrescentar(ABA, novas)
    base.atualizar("Cursos", alteracoes_cursos)
    base.acrescentar("Cursos", cursos_novos)
    if historico and HISTORICO in base.abas():
        base.acrescentar(HISTORICO, historico)
    base.guardar()
    gravar_json(fonte["estado"], estado)
    print(f"\n{fonte['nome']}: {lidos} editais lidos, {len(novas)} turmas novas, {len(cursos_novos)} cursos novos "
          f"({sum(1 for n in cursos_novos if n['Estado'] == 'Publicado')} publicados) | custo estimado {round(custo, 3)} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
