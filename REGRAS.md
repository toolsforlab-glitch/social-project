# Regras do site (em vigor)

Lista única. Uma regra nova entra **primeiro aqui**, com a data e o código que a aplica; só depois na secção da fonte, no LEIAME (que fica como histórico). As rotinas e as fontes estão em [ROTINAS.md](ROTINAS.md).

Última revisão: 27/11/2026 (arrumação antes do Sudeste). Os códigos (F, I, E, M, T) não mudam de número: uma regra nova recebe o número seguinte, mesmo que fique arrumada noutro grupo.

**Índice**: 1. Fontes (F) · 2. Quando um curso entra (I) · 3. Quando fica fora (E) · 4. Como se mostra (M) · 5. Como se trabalha (T): 5a decisões, 5b procura, 5c navegador e sites que bloqueiam, 5d segurança e qualidade · 6. Práticas em uso, por confirmar · Numeração antiga

## 1. Quem pode ser fonte

- **F1. Só instituições conceituadas**: órgãos e escolas do governo, institutos federais, Sistema S (Senac, SENAI, Sebrae…), fundações reconhecidas. Nada «de fundo de quintal» (25/11).
- **F2. OSC executora só com os 5 critérios**: 10 anos ou mais de CNPJ ativo; histórico com o Estado; confiança além de um curso avulso; sem impedimentos (CEPIM, CEIS, CNEP); sem notícias de irregularidades. Detalhe e resultado no LEIAME, «OSCs executoras» (25/11).
- **F3. Igrejas, congregações e ONGs**: entram se o curso for gratuito e aberto a qualquer pessoa (23/11).
- **F4. Jornais só servem para descobrir** (marcados «Só para descobrir» em Sites de confiança). O curso precisa de uma página oficial. Uma notícia no site oficial da própria entidade que oferece o curso (ex.: a Semtas no site da Prefeitura do Natal) conta como página oficial; uma notícia antiga, que o portal já não mostra, não publica.
- **F5. Instagram de uma OSC aprovada** conta como página oficial da turma; é conferido no navegador (25/11).
- **F6. Escolas públicas são «Tudo gratuito»**: institutos federais, Secretarias de Educação, EJA da rede pública (23/11 e 25/11). Mesmo assim guarda-se uma frase: a página de perguntas frequentes da instituição (ex.: IFMS, «Todos os cursos oferecidos são inteiramente gratuitos.»; IFMT, página «Estude no IFMT»; IFB, notícia dos cursos EJA-EPT) ou, se a instituição não tiver essa frase, a LDB: art. 37 para a EJA («assegurarão gratuitamente aos jovens e aos adultos») e art. 3.º, VI para os outros cursos («gratuidade do ensino público em estabelecimentos oficiais»; 27/11). A LDB nunca serve para cursos de fundações de apoio ou parceiros (Funcern, Fadex…). A frase «a inscrição é gratuita» do edital não basta (I2). Se a página disser que é pago, vale a página (27/11).

## 2. Um curso entra quando TODAS estas são verdade

- **I1. Tudo vem da fonte oficial, com a frase exata.** Cada afirmação importante tem a frase da página ou do edital na Evidência, conferida por código (`citacao_valida`, base.py) ou, quando o site recusa o GitHub, pelo Claude no navegador (T10). O que a fonte não diz fica vazio. Nada deduzido (20/11).
- **I2. É gratuito, com frase explícita** («gratuito», «sem custo»…; `gratuidade_explicita`, base.py), ou a entidade é «Tudo gratuito» (F6), ou foi revisto por uma pessoa. Uma frase só sobre a inscrição («a inscrição é gratuita», «não será cobrada taxa de inscrição») não basta. Sem prova, o cartão diz «Gratuidade por confirmar» (20/11).
- **I3. A inscrição está aberta e isso está provado**: frase da página, prazo do edital, botão marcado por uma pessoa, ou curso claramente sob demanda (`ACAO_SOB_DEMANDA`, base.py; 21/11).
  - **Curso por abrir**: entra com a data de abertura provada (prova «abertura»), até 60 dias antes (`DIAS_POR_ABRIR` em app.js, senac_ma.py e cetam.py; 25/11; nos leitores do Senac desde 27/11; no Cetam desde 27/11, logo que o edital sai, porque as janelas de 1 a 4 dias quase não deixavam ver os cursos).
  - **Inscrição «enquanto houver vagas»** (ou «até o limite de vagas»): a turma fica aberta até à véspera do início das aulas (senac_ma.py, senac_ms.py; 26/11 e 27/11).
- **I4. Qualquer pessoa do público pode concorrer.** Ser de um grupo (baixa renda, mulheres, PcD, jovens, alunos da rede pública ou da EJA) não é disputa e pode entrar (23/11). Vagas que a comunidade só recebe depois de outro público (ex.: aprendizagem do SENAI RO, sobras das vagas das indústrias) entram, com isso em «O que falta confirmar» (27/11). Exigir o ensino médio completo (cursos técnicos subsequentes) é um requisito, não uma disputa (IFMT, 27/11).
- **I8. Cursos técnicos integrados ao ensino médio regular entram** (decisão do responsável, 27/11), para quem acaba o 9.º ano, quando a vaga é por sorteio ou ordem de inscrição; os que selecionam por notas ficam fora pela E3. Vão para «Terminar a escola», com a idade mínima e a escolaridade pedidas no cartão. Até 27/11 tinham ficado fora por escolha do Claude, sem regra.
- **I5. A vaga não se disputa**: entram ordem de inscrição, ordem de chegada e sorteio, com aviso no cartão (`regra_vagas`, construir_site.py; 23/11). Se a fonte não diz como as vagas são preenchidas e não fala de prova, o curso entra, com «A página não diz como as vagas são preenchidas» em «O que falta confirmar» (prática das listas de turmas do Senac e do SENAI SE). Classificação por critérios sociais do edital (renda, CadÚnico, ser mulher…) com sorteio no empate também entra, com isso em «O que falta confirmar» (Jornada da Mulher DF; aceite pelo responsável a 27/11).
- **I6. A página oficial abre** (E8).
- **I7. Passou a auditoria**: segunda leitura independente ou regras de código (datas coerentes, frases conferidas). Senão fica em Rever, com o motivo (regra antiga 10).

## 3. Um curso fica fora se QUALQUER uma destas acontecer

| | Motivo | Código / data |
|---|---|---|
| E1 | É pago, ou o curso é gratuito mas o certificado é pago («Ou é grátis ou não é») | `curso_no_site`, base.py; 24/11 |
| E2 | Só fala em «bolsa» («bolsa integral», «bolsa de 100%»), sem dizer que é gratuito. «Bolsas gratuitas» do PSG conta | `_GRATUIDADE`, base.py; 24/11 e 25/11 |
| E3 | Exige prova, redação, nota do ENEM, entrevista, análise de currículo, de títulos ou de notas do histórico escolar | `exige_prova`, base.py; 23/11 e 24/11 |
| E4 | É só para quem já trabalha (servidores, funcionários de uma empresa, profissionais de uma área; ex.: Profuncionário do IEMA, 26/11), ou é uma turma fechada para o público de um parceiro (hospital, presídio, associação, projeto; «turma exclusiva», «turma fechada», «vagas exclusivas para…»; Senac MS e Senac GO, 27/11). Na Escola Virtual de Governo, entra se o público incluir cidadãos, pais ou «qualquer pessoa» | 23/11; `FECHADA`, senac_ms.py |
| E5 | Exige ser membro, ir ao culto ou à catequese, ou é formação religiosa | 23/11 |
| E6 | Veio de jornal ou notícia e não há página oficial | 16/11 |
| E7 | Não se prova o prazo nem as vagas | 16/11 |
| E8 | A página do curso dá 404/410, confirmado por uma segunda leitura | `Pagina404`, verificar.py; 25/11 |
| E9 | As inscrições já fecharam (prazo passado ou turma encerrada), ou o curso já está a decorrer/terminou sem inscrição aberta | rotinas de turmas, `arquivar.py` |
| E10 | A executora é uma OSC que não cumpre os 5 critérios (F2) | 25/11 |
| E11 | É curso superior (graduação) ou pós-graduação (especialização, mestrado) | prática desde o início; escrito a 27/11 |
| E12 | Cobra taxa de inscrição e já não dá para pedir a isenção (o prazo do pedido fechou, ou o edital não prevê isenção). Se a isenção ainda pode ser pedida, o curso entra, com no cartão o valor da taxa, quem tem direito à isenção (frase do edital) e o prazo do pedido; sai quando esse prazo fecha | decisão do responsável, 28/11 (IFSP) |

Regras de uma só fonte (ex.: no SENAI Play, só cursos com 16 horas ou mais, já retirado) ficam na secção da fonte, no LEIAME.

## 4. Como se mostra

- **M1. Requisitos com o texto da fonte, um por linha**, sem reescrever (25/11).
- **M2. Linguagem simples só nos textos do projeto** (descrições «Em resumo», etiquetas, botões). As frases da fonte nunca se alteram. Tudo em português do Brasil (`IDIOMA`, comum.py; 21/11).
- **M3. «Em resumo:»** aparece quando o projeto reescreveu a descrição; sem rótulo quando foi copiada da página (`origem_descricao`; 20/11).
- **M4. Datas só com prova**: «Inscrições até …» com prazo provado; «Aulas começam em …» com data de início; «Se for aprovado: matrícula de … a …» com a frase do cronograma (`matricula_do_edital`, base.py). O semestre de ingresso não vira etiqueta (25/11).
- **M5. Curso por abrir**: «Inscrições abrem em … e vão até …»; o botão diz «Ver a página oficial» e o lembrete é para o dia da abertura; no dia passa sozinho a Aberto (25/11 e 26/11).
- **M6. Cada botão diz que página abre** (curso, lista, PDF, formulário…; `paginas.py`, `DESTINOS_FONTES`).
- **M7. «Só mulheres»** vai no título e na condição de acesso.
- **M8. Cursos do mesmo edital num só cartão** («N cursos com a mesma inscrição»; `agrupar`, app.js; 26/11). Um edital muito grande, com dezenas de cursos e a mesma inscrição, pode entrar como um curso geral que descreve a oferta (SENAI DF, Edital 01/2027, 27/11).
- **M9. Certificado, acessibilidade e idades só com frase**: o certificado tem de estar descrito; a acessibilidade tem de nomear um recurso concreto; a idade tem de estar escrita. O preço da 2ª via ou da reimpressão não diz como é o certificado do curso, nem pago nem gratuito (`certificado_da_frase`, base.py; 25/11 e 27/11).
- **M10. Duração sempre com a unidade** («160 horas», nunca «160» sozinho; `duracao_legivel`, construir_site.py, e senac_ma.py). O filtro e a página de números usam as faixas: até 4, 5–20, 21–40, 41–80, 81–160, 161–400 e mais de 400 horas (`FAIXAS_DURACAO`, app.js; 27/11, a pedido do responsável).
- **M11. O dia do site é o de Brasília** (28/11, a pedido do responsável): os prazos e as turmas mudam à meia-noite de Brasília, não à do relógio de quem abre o site (`hojeIso`, app.js). As rotinas já usam a hora de Fortaleza, igual à de Brasília (`hoje_ceara`). Percentagens com uma casa decimal, para uma faixa com cursos nunca aparecer como 0% (27/11).
- **M12. Cartão geral conta as turmas que reúne** (28/11, a pedido do responsável): um cartão que reúne muitas turmas (Senac SP, Senac RJ) tem na folha «Turmas abertas (cartão geral)» e «Turmas contadas em». O mapa dos números conta cada turma aberta (curso com turmas: as turmas atuais; cartão geral: esse número; os outros: 1), a lista diz o total de turmas, e o cartão mostra «Este cartão reúne N turmas… (contadas a …)». Contagem com mais de 7 dias deixa de contar (volta a 1) até a tarefa do navegador a atualizar (`turmas_do_cartao_geral`, construir_site.py; `opcoesAbertas`, app.js).

## 5. Como se trabalha

### 5a. Decisões e registos

- **T1. Problemas viram pendências** na aba «Pendências para verificar» (`registar_pendencia`, base.py), escritas na primeira linha livre logo a seguir às outras (não no fim da tabela). Se a pendência depende de uma data futura, marca-se logo um lembrete (22/11 e 25/11).
- **T2. A rotina marca, uma pessoa decide**: «Mudança a rever» só sai por uma pessoa; «Feito» nas pendências só é marcado por uma pessoa; «Revisto por pessoa» protege a linha das rotinas; Oculto e Rever postos por uma pessoa nunca mudam.
- **T13. Curso criado à mão segue as mesmas regras** (27/11): Evidência no formato «campo: «frase» (url)», Campos comprovados, Notas a dizer como foi achado (ex.: auditoria do ChatGPT, tarefa do navegador) e Nota da verificação. Escreve-se pelo passo temporário `escrever.py` (rotina «Rodar um passo», retirado logo a seguir) ou pela tarefa do navegador; nunca sem frase oficial.
- **T14. Data claramente trocada no edital: decide o responsável** (27/11). Não se corrige uma data por dedução. Quando o erro é evidente (ex.: Edital 52/2026 do IFRO Ji-Paraná, inscrições «30/11/2027 a 11/12/2027» com aulas a 05/02/2027), o responsável decidiu publicar com as datas certas e um aviso em «O que falta confirmar», com o contacto da entidade para confirmar. Cada caso novo vai às Pendências para a mesma decisão.
- **T15. Revisão antes de abrir uma região nova** (27/11): rotinas com falhas, cursos em Rever ou Novo, «Mudança a rever», linhas repetidas e «O que falta confirmar» por entidade; o que é erro corrige-se, o que é dúvida vai à auditoria do ChatGPT (ex.: `estado/auditoria5_chatgpt_2026-11-27.md`).
- **T16. Estado nunca de memória** (27/11): antes de dizer que uma rotina, a API ou um site está parado ou a funcionar, confirma-se agora (registos da rotina, painel, página). Um estado visto dias antes não se repete como atual (caso do limite da API da Anthropic, dado como atingido quando já não estava).
- **T17. Região nova: ligar antes os locais** (27/11): a aba «Locais» da planilha (Ativo), os nomes e a localização aproximada em `cursos.py` e `semanal.py`. Sem isso, os cursos criados nessa região não aparecem no site (caso de Goiás e do DF, corrigido a 27/11).

### 5b. Como se encontram os cursos

- **T3. Leitores sem Claude sempre que a fonte é estruturada** (listas, APIs, editais com modelo fixo). O Claude só escolhe ou resume, nunca prova.
- **T6. Antes de escrever um leitor novo, procurar se já existe** (`grep -ril <site> scripts/ LEIAME.md .github/workflows/`; 26/11).
- **T12. Fonte nova de notícias oficiais entra com `primeira_leitura_cria`** quando ninguém tratou ainda as notícias recentes: a primeira leitura cria os cursos das notícias dos últimos 20 dias, em vez de as marcar como vistas (27/11: a fonte «Governo de Roraima» perdeu assim os cursos técnicos da Escola Barão de Parima). Sem essa opção, a primeira leitura só marca como vistas.
- **T5. O ChatGPT da assinatura ajuda a procurar e a auditar, sem API** (22/11; revisto a 27/11). O ChatGPT só aponta a frase e o link; quem prova é o código ou o Claude, na página oficial. Frase vista só no resumo da pesquisa (versão indexada), sem a página abrir, não conta (auditoria 3, 27/11). Quando o ChatGPT e a página oficial discordam (ex.: cidade de um curso), vale a página. Três tipos: dúvidas de cursos (`consultar_gpt.py` → `estado/resposta_chatgpt.txt` → `aplicar_chatgpt.py`); certificado por entidade (`chatgpt_certificado.py` → `estado/resposta_certificado.txt` → `aplicar_certificado.py`); revisão e procura escritas à mão (auditorias 3 a 5 de 27/11, guardadas em `estado/`), conferidas pelo Claude uma a uma.
- **T4. Se a API da Anthropic falhar**, as notícias novas com data próxima são revistas à mão («Revisto por pessoa»), com as mesmas regras (26/11). Antes de supor que está parada, confirmar nos registos da rotina (T16).

### 5c. Navegador, VPN e sites que bloqueiam

- **T10. O que o GitHub não abre é lido no Chrome do responsável** (26/11 e 27/11):
  - **Sempre o Chrome dele** (Claude in Chrome), nunca o navegador integrado.
  - **VPN do Brasil antes de qualquer varredura** num site brasileiro (pedido do responsável, 27/11): abrir primeiro ipinfo.io e só continuar com «country: BR». A VPN é a app Urban VPN do Windows (país Brazil), que o Claude liga e desliga (controlo do computador, acesso dado a 27/11); a extensão do Chrome também existe, mas o Claude não carrega no botão dela. Se não for BR e a app não responder, pedir ao responsável e esperar.
  - **Site que bloqueia a VPN** (ex.: IFMS, 403 «verifique se há uma VPN ativa»): desligar a VPN, ler, voltar a ligá-la e confirmar BR no ipinfo.io (pedido do responsável, 27/11). Ao controlar o computador, as outras janelas escondem-se por instantes: fazer só o clique necessário.
  - **Catálogo**: cada site que recusa o GitHub, a VPN ou acessos de fora do Brasil fica na aba «Sites que bloqueiam» da planilha, com o erro visto, se abre no Chrome e o que tentar depois.
  - **Tarefa diária** «Projeto Social – fontes no navegador»: confirma o IP do Brasil, lê as pendências de sites que recusaram o acesso e a lista fixa `fontes_navegador.json` (sites que recusam sempre, sites que só abrem com IP do Brasil, Instagram das OSCs aprovadas, SENAI DF), aplica estas regras e regista o resultado. Se nem assim abrir, a pendência diz isso.
- **T18. PDFs no navegador** (27/11): nunca abrir o endereço de um PDF numa aba (o Chrome pode descarregá-lo sem autorização). Lê-se dentro da página, com `fetch` e o pequeno leitor de PDF em JavaScript (descompressão e mapas ToUnicode, sem bibliotecas de fora); o texto vai para a própria página e lê-se com `get_page_text`. Ficheiros no visualizador do Google Drive não se conseguem ler assim. Quando o GitHub abre o PDF, prefere-se o GitHub (pdftotext ou pypdf).
- **T19. Sites com CAPTCHA por excesso de pedidos** (IFB, 27/11): poucos pedidos por rodada, com pausas de 12 s no GitHub; as páginas leem-se no Chrome.

### 5d. Segurança e qualidade técnica

- **T9. Segurança**: nunca desligar a verificação TLS nem passar por cima de um aviso de certificado no navegador (um certificado vencido não se ignora: a fonte fica parada até ser renovado; ex.: Senac PI, selecao.ifmt.edu.br); nunca ler dados de pagamento nem dados pessoais expostos pelas fontes (ex.: no Senac PB só se conta o número de turmas); chaves só em GitHub Secrets, nunca no chat; a chave da API da Anthropic do projeto expira a 15/12/2026 e é o responsável que a renova.
- **T11. O site é testado antes de publicar** (`scripts/testar_site.js`, em todas as rotinas): abre a lista de cursos num navegador simulado e percorre todas as páginas; se houver erro, não publica e fica a versão anterior (26/11, depois de um erro que apagou a lista inteira).
- **T7. Antes de mudar uma rotina, validar o YAML** de todas as rotinas (`yaml.safe_load`; 25/11).
- **T8. Fluxos temporários** (`teste-rede.yml`, `scripts/tmp_teste/`, ramo `sonda-tmp`, opção `tmp_teste/escrever.py` no `verificar.yml`) são apagados logo depois do uso. O ramo `sonda-tmp` apaga-se pelo próprio `teste-rede.yml` (o GitHub recusa apagá-lo a partir daqui).
- **T20. Leitores que precisam de programas instalados** (pdftotext, LibreOffice, OCR) correm depois do passo que os instala no `noticias.yml`, e no `verificar.yml` o passo de instalação inclui-os (senac_ms.py, 27/11).

## 6. Práticas em uso, por confirmar pelo responsável

Nenhuma de momento (P3, a LDB para institutos federais, entrou na F6 a 27/11).

## Correspondência com a numeração antiga (até 26/11)

1→I1 · 2→I2 · 3→E2 · 4→F6 · 5→E1 · 6→I5 e E3 · 7→I3 · 8→E8 · 9→E6 e E7 · 10→I7 e T2 · 11→F5 · 12→I4 e E4 · 13→F3 e E5 · 14→F4 · 15→M9 · 16→M1 · 17→M2 · 18→M3 · 19→M4 · 20→M5 · 21→M6 · 22→M7 · 22a→M8 · 23→T1 · 24→T2 · 25→T3 · 26→T9 · 27→T8 · 28→T7 · 29→T6
