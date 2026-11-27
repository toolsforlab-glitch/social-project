# Regras do site (em vigor)

Lista única. Uma regra nova entra **primeiro aqui**, com a data e o código que a aplica; só depois na secção da fonte, no LEIAME (que fica como histórico). As rotinas e as fontes estão em [ROTINAS.md](ROTINAS.md).

Última revisão: 27/11/2026. Os códigos (F, I, E, M, T) não mudam de número: uma regra nova recebe o número seguinte, mesmo que fique arrumada noutro grupo.

## 1. Quem pode ser fonte

- **F1. Só instituições conceituadas**: órgãos e escolas do governo, institutos federais, Sistema S (Senac, SENAI, Sebrae…), fundações reconhecidas. Nada «de fundo de quintal» (25/11).
- **F2. OSC executora só com os 5 critérios**: 10 anos ou mais de CNPJ ativo; histórico com o Estado; confiança além de um curso avulso; sem impedimentos (CEPIM, CEIS, CNEP); sem notícias de irregularidades. Detalhe e resultado no LEIAME, «OSCs executoras» (25/11).
- **F3. Igrejas, congregações e ONGs**: entram se o curso for gratuito e aberto a qualquer pessoa (23/11).
- **F4. Jornais só servem para descobrir** (marcados «Só para descobrir» em Sites de confiança). O curso precisa de uma página oficial. Uma notícia no site oficial da própria entidade que oferece o curso (ex.: a Semtas no site da Prefeitura do Natal) conta como página oficial; uma notícia antiga, que o portal já não mostra, não publica.
- **F5. Instagram de uma OSC aprovada** conta como página oficial da turma; é conferido no navegador (25/11).
- **F6. Escolas públicas são «Tudo gratuito»**: institutos federais, Secretarias de Educação, EJA da rede pública (23/11 e 25/11). Se a página disser que é pago, vale a página.

## 2. Um curso entra quando TODAS estas são verdade

- **I1. Tudo vem da fonte oficial, com a frase exata.** Cada afirmação importante tem a frase da página ou do edital na Evidência, conferida por código (`citacao_valida`, base.py). O que a fonte não diz fica vazio. Nada deduzido (20/11).
- **I2. É gratuito, com frase explícita** («gratuito», «sem custo»…; `gratuidade_explicita`, base.py), ou a entidade é «Tudo gratuito» (F6), ou foi revisto por uma pessoa. Uma frase só sobre a inscrição («a inscrição é gratuita», «não será cobrada taxa de inscrição») não basta. Sem prova, o cartão diz «Gratuidade por confirmar» (20/11).
- **I3. A inscrição está aberta e isso está provado**: frase da página, prazo do edital, botão marcado por uma pessoa, ou curso claramente sob demanda (`ACAO_SOB_DEMANDA`, base.py; 21/11). Curso **por abrir**: entra com a data de abertura provada (prova «abertura»), até 60 dias antes (`DIAS_POR_ABRIR` em app.js e senac_ma.py; 25/11; nos leitores do Senac desde 27/11).
- **I4. Qualquer pessoa do público pode concorrer.** Ser de um grupo (baixa renda, mulheres, PcD, jovens, alunos da rede pública ou da EJA) não é disputa e pode entrar (23/11). Vagas que a comunidade só recebe depois de outro público (ex.: aprendizagem do SENAI RO, sobras das vagas das indústrias) entram, com isso em «O que falta confirmar» (27/11).
- **I5. A vaga não se disputa**: entram ordem de inscrição e sorteio, com aviso no cartão (`regra_vagas`, construir_site.py; 23/11). Se a fonte não diz como as vagas são preenchidas e não fala de prova, o curso entra, com «A página não diz como as vagas são preenchidas» em «O que falta confirmar» (prática das listas de turmas do Senac e do SENAI SE).
- **I6. A página oficial abre** (8.ª regra de exclusão abaixo).
- **I7. Passou a auditoria**: segunda leitura independente ou regras de código (datas coerentes, frases conferidas). Senão fica em Rever, com o motivo (regra antiga 10).

## 3. Um curso fica fora se QUALQUER uma destas acontecer

| | Motivo | Código / data |
|---|---|---|
| E1 | É pago, ou o curso é gratuito mas o certificado é pago («Ou é grátis ou não é») | `curso_no_site`, base.py; 24/11 |
| E2 | Só fala em «bolsa» («bolsa integral», «bolsa de 100%»), sem dizer que é gratuito. «Bolsas gratuitas» do PSG conta | `_GRATUIDADE`, base.py; 24/11 e 25/11 |
| E3 | Exige prova, redação, nota do ENEM, entrevista, análise de currículo ou de títulos | `exige_prova`, base.py; 23/11 e 24/11 |
| E4 | É só para quem já trabalha: servidores, funcionários de uma empresa, profissionais de uma área (ex.: Profuncionário do IEMA, 26/11). Na Escola Virtual de Governo, entra se o público incluir cidadãos, pais ou «qualquer pessoa» | 23/11 |
| E5 | Exige ser membro, ir ao culto ou à catequese, ou é formação religiosa | 23/11 |
| E6 | Veio de jornal ou notícia e não há página oficial | 16/11 |
| E7 | Não se prova o prazo nem as vagas | 16/11 |
| E8 | A página do curso dá 404/410, confirmado por uma segunda leitura | `Pagina404`, verificar.py; 25/11 |
| E9 | As inscrições já fecharam (prazo passado ou turma encerrada), ou o curso já está a decorrer/terminou sem inscrição aberta | rotinas de turmas, `arquivar.py` |
| E10 | A executora é uma OSC que não cumpre os 5 critérios (F2) | 25/11 |

Regras de uma só fonte (ex.: no SENAI Play, só cursos com 16 horas ou mais, já retirado) ficam na secção da fonte, no LEIAME.

## 4. Como se mostra

- **M1. Requisitos com o texto da fonte, um por linha**, sem reescrever (25/11).
- **M2. Linguagem simples só nos textos do projeto** (descrições «Em resumo», etiquetas, botões). As frases da fonte nunca se alteram. Tudo em português do Brasil (`IDIOMA`, comum.py; 21/11).
- **M3. «Em resumo:»** aparece quando o projeto reescreveu a descrição; sem rótulo quando foi copiada da página (`origem_descricao`; 20/11).
- **M4. Datas só com prova**: «Inscrições até …» com prazo provado; «Aulas começam em …» com data de início; «Se for aprovado: matrícula de … a …» com a frase do cronograma (`matricula_do_edital`, base.py). O semestre de ingresso não vira etiqueta (25/11).
- **M5. Curso por abrir**: «Inscrições abrem em … e vão até …»; o botão diz «Ver a página oficial» e o lembrete é para o dia da abertura; no dia passa sozinho a Aberto (25/11 e 26/11).
- **M6. Cada botão diz que página abre** (curso, lista, PDF, formulário…; `paginas.py`).
- **M7. «Só mulheres»** vai no título e na condição de acesso.
- **M8. Cursos do mesmo edital num só cartão** («N cursos com a mesma inscrição»; `agrupar`, app.js; 26/11).
- **M9. Certificado, acessibilidade e idades só com frase**: o certificado tem de estar descrito; a acessibilidade tem de nomear um recurso concreto; a idade tem de estar escrita. O preço da 2ª via ou da reimpressão não diz como é o certificado do curso, nem pago nem gratuito (`certificado_da_frase`, base.py; 25/11 e 27/11).

## 5. Como se trabalha

### 5a. Decisões e registos
- **T1. Problemas viram pendências** na aba «Pendências para verificar» (`registar_pendencia`, base.py). Se a pendência depende de uma data futura, marca-se logo um lembrete (22/11 e 25/11).
- **T2. A rotina marca, uma pessoa decide**: «Mudança a rever» só sai por uma pessoa; «Feito» nas pendências só é marcado por uma pessoa; «Revisto por pessoa» protege a linha das rotinas; Oculto e Rever postos por uma pessoa nunca mudam.
- **T13. Curso criado à mão segue as mesmas regras** (27/11): Evidência no formato «campo: «frase» (url)», Campos comprovados, Notas a dizer como foi achado (ex.: auditoria do ChatGPT, tarefa do navegador) e Nota da verificação. Escreve-se pelo passo temporário `escrever.py` (rotina «Rodar um passo», retirado logo a seguir) ou pela tarefa do navegador; nunca sem frase oficial.

- **T14. Data claramente trocada no edital: decide o responsável** (27/11). Não se corrige uma data por dedução. Quando o erro é evidente (ex.: Edital 52/2026 do IFRO Ji-Paraná, inscrições «30/11/2027 a 11/12/2027» com aulas a 05/02/2027), o responsável decidiu publicar com as datas certas e um aviso em «O que falta confirmar», com o contacto da entidade para confirmar. Cada caso novo vai às Pendências para a mesma decisão.
- **T15. Revisão antes de abrir uma região nova** (27/11): rotinas com falhas, cursos em Rever ou Novo, «Mudança a rever», linhas repetidas e «O que falta confirmar» por entidade; o que é erro corrige-se, o que é dúvida vai à auditoria do ChatGPT (ex.: `estado/auditoria4_chatgpt_2026-11-27.md`).

### 5b. Como se encontram os cursos
- **T3. Leitores sem Claude sempre que a fonte é estruturada** (listas, APIs, editais com modelo fixo). O Claude só escolhe ou resume, nunca prova.
- **T6. Antes de escrever um leitor novo, procurar se já existe** (`grep -ril <site> scripts/ LEIAME.md .github/workflows/`; 26/11).
- **T12. Fonte nova de notícias oficiais entra com `primeira_leitura_cria`**: a primeira leitura cria os cursos das notícias dos últimos 20 dias, em vez de as marcar como vistas (27/11: a fonte «Governo de Roraima» perdeu assim os cursos técnicos da Escola Barão de Parima).
- **T10. O que o GitHub não abre é lido no Chrome do responsável, com a VPN do Brasil** (26/11). **Antes de qualquer varredura num site brasileiro** (27/11, a pedido do responsável): usar o Chrome dele (Claude in Chrome), nunca o navegador integrado, que não tem a extensão; abrir primeiro ipinfo.io e só continuar com «country: BR». Se não for BR, pedir ao responsável que ligue a Urban VPN em Brazil (o Claude não consegue carregar no botão da extensão) e esperar. Os leitores registam uma pendência sempre que um site recusa o acesso; a tarefa diária «Projeto Social – fontes no navegador» confirma que o IP é do Brasil (Urban VPN, país Brazil), lê essas pendências e a lista fixa `fontes_navegador.json` (sites que recusam sempre, sites que só abrem com IP do Brasil como o SENAI SE, Instagram das OSCs aprovadas), aplica estas regras e regista o resultado. Se nem assim abrir, a pendência diz isso, para não ficar esquecida.
- **T5. O ChatGPT da assinatura ajuda a procurar e a auditar, sem API** (22/11; revisto a 27/11). O ChatGPT só aponta a frase e o link; quem prova é o código ou o Claude, na página oficial. Frase vista só no resumo da pesquisa (versão indexada), sem a página abrir, não conta (auditoria 3, 27/11). Três tipos: dúvidas de cursos (`consultar_gpt.py` → resposta em `estado/resposta_chatgpt.txt` → `aplicar_chatgpt.py`); certificado por entidade (`chatgpt_certificado.py` → `estado/resposta_certificado.txt` → `aplicar_certificado.py`); revisão e procura escritas à mão (ex.: auditoria 3 de 27/11, guardada em `estado/`), conferidas pelo Claude uma a uma.
- **T4. Se a API da Anthropic falhar**, as notícias novas com data próxima são revistas à mão («Revisto por pessoa»), com as mesmas regras (26/11). Antes de supor que está parada, confirmar nos registos da rotina (custos e erros de limite).

### 5c. Segurança e qualidade técnica
- **T9. Segurança**: nunca desligar a verificação TLS (um certificado vencido não se ignora: a fonte fica parada até ser renovado); nunca ler dados de pagamento nem dados pessoais expostos pelas fontes (ex.: no Senac PB só se conta o número de turmas); chaves só em GitHub Secrets.
- **T11. O site é testado antes de publicar** (`scripts/testar_site.js`, em todas as rotinas): abre a lista de cursos num navegador simulado e percorre todas as páginas; se houver erro, não publica e fica a versão anterior (26/11, depois de um erro que apagou a lista inteira).
- **T7. Antes de mudar uma rotina, validar o YAML** de todas as rotinas (`yaml.safe_load`; 25/11).
- **T8. Fluxos temporários** (`teste-rede.yml`, `scripts/tmp_teste/`, ramo `sonda-tmp`, opção `tmp_teste/escrever.py` no `verificar.yml`) são apagados logo depois do uso.

## Correspondência com a numeração antiga (até 26/11)

1→I1 · 2→I2 · 3→E2 · 4→F6 · 5→E1 · 6→I5 e E3 · 7→I3 · 8→E8 · 9→E6 e E7 · 10→I7 e T2 · 11→F5 · 12→I4 e E4 · 13→F3 e E5 · 14→F4 · 15→M9 · 16→M1 · 17→M2 · 18→M3 · 19→M4 · 20→M5 · 21→M6 · 22→M7 · 22a→M8 · 23→T1 · 24→T2 · 25→T3 · 26→T9 · 27→T8 · 28→T7 · 29→T6
