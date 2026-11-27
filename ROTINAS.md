# Rotinas e fontes

O que corre, quando, e de onde vêm os cursos de cada estado. As regras estão em [REGRAS.md](REGRAS.md); o detalhe de cada leitor está no LEIAME, na secção da fonte.

Última revisão: 27/11/2026. Legenda: **código** = lido por código, sem Claude · **Claude** = precisa da API da Anthropic (paga à parte; não gasta a quota da conversa) · **resumo** = só o resumo usa Claude; os dados vêm por código.

## 1. Rotinas

| Rotina | Quando (hora de Fortaleza) | O que faz |
|---|---|---|
| **Notícias do dia** (`noticias.yml`) | todos os dias, 06:17; reserva às 10:17 | Notícias do site (Claude) → turmas e listas oficiais (código, ver secção 2) → matrícula dos editais novos → notícias oficiais (código) e verificação das novas (Claude) → editais do Senac MA e afins (Claude) → Cetam → catálogos on-line (resumo) → gera, testa (T11) e publica o site |
| **Cursos e resumo da semana** (`semanal.yml`) | segundas, 05:23; reserva às 11:23 | Pesquisa de cursos novos (Claude) → catálogos sob demanda → verificação de todos os cursos (Claude) → unidades → arquivar o que terminou → guias «Antes de começar» → turmas → site → WhatsApp, cartaz e newsletter → publica |
| **Atualizar o site** (`site.yml`) | quando muda o aspeto do site, ou à mão | Turmas do Senac CE e Centec → unidades → gera o site → auditoria dos requisitos (só avisa) → publica |
| **Rodar um passo** (`verificar.yml`) | à mão | Corre um só script (lista no próprio ficheiro) e publica o site |

A ordem entre rotinas é dada por `scripts/vez.py`: uma espera que a outra acabe.

**Tarefas agendadas no Claude** (fora do GitHub; gastam a quota da conta Claude do responsável):
- **Fontes no navegador** (todos os dias, 10:47 em Lisboa, no computador do responsável, pelo Chrome): confirma a VPN do Brasil, lê as pendências de sites que recusaram o GitHub e as fontes de `fontes_navegador.json`, cria os cursos que cumprem as regras (regra T10). Se o computador estiver desligado à hora marcada, a tarefa fica suspensa («computador ausente»): é preciso reativá-la (27/11).
- Disparo de segurança da rotina diária (todos os dias, 09:41 em Lisboa) e da semanal (segundas, 08:47 UTC). Só disparam se o GitHub ainda não a correu.
- **Quando a quota do Claude acaba**, estas tarefas falham (ex.: 27/11, 09:41) e só voltam na hora seguinte marcada ou quando alguém as dispara; as rotinas do GitHub continuam a correr e a publicar.
- Lembretes nesta conversa: 1/12 (balanço dos cursos novos por estado e das fontes novas de 26/11), 5/01/2027 (abre a EJA do Amapá), 6/01 (EJA da Bahia), 1/02 e 3/05 (Seduc PI).

**Auditorias do ChatGPT** (à mão, ChatGPT da assinatura, regra T5): a rotina «Rodar um passo» prepara o texto (`consultar_gpt.py` → `estado/auditoria_chatgpt.md`; `chatgpt_certificado.py` → `estado/chatgpt_certificado.md`); o responsável cola no ChatGPT e devolve a resposta; `aplicar_chatgpt.py` / `aplicar_certificado.py` provam cada frase. Pedidos escritos à mão (revisão de cursos novos, procura em estados fracos) são conferidos pelo Claude; a resposta fica em `estado/`.

## 2. Fontes por estado

Cursos presenciais visíveis no site a 27/11/2026 entre parênteses (incluem os «por abrir»).

| Estado | Fontes e leitor |
|---|---|
| **Ceará** (23) | Senac CE, turmas do PSG (`turmas.py`, código) · Centec (`centec.py`, código) · Cagece Capacita e Prefeitura de Fortaleza, notícias e Fortaleza Inclusiva (notícias oficiais) · EJA (à mão) · vigia: IFCE |
| **Rio Grande do Norte** (6) | IFRN, FIC, extensão e ProEJA (`ifrn_fic.py`, código) · SENAI RN, vagas gratuitas regimentais (`senai_rn.py`, código: lista «Oportunidades» + edital) · Semtas Natal (notícias oficiais) · vigia: Senac RN |
| **Paraíba** (3) | Caminhos Digitais (`caminhos_digitais.py`, código) · vigias: Senac PB, IFPB |
| **Pernambuco** (3) | GO Recife / Qualifica Recife (`gorecife.py`, código) · Qualifica PE, notícias da SEDEPE (notícias oficiais) · SENAI PE (`senac_ma.py`, Claude) · vigia: Senac PE |
| **Alagoas** (21, 16 por abrir) | OxeTech Lab (`oxetech.py`, código) · Senac AL e SENAI AL (`senac_ma.py`, Claude) · Prefeitura de Maceió (notícias oficiais) |
| **Sergipe** (3) | SENAI SE, Matrícula Web «Turmas Abertas» (só abre com IP do Brasil: tarefa do navegador com VPN, `fontes_navegador.json`) · vigia: Senac SE |
| **Bahia** (8) | Senac BA, PSG (`senac_ba.py`, código) · Treinar para Empregar, Salvador (`salvador_tpe.py`, código) · vigias: SENAI BA, SEC BA (técnicos por sorteio), IF Baiano, 4 OSCs aprovadas · EJA (lembrete 6/01) |
| **Piauí** (1) | Senac PI e SENAI PI (`senac_ma.py`, Claude; o Senac PI tem o certificado do site expirado) · Governo do Piauí (notícias oficiais) · FADEX, Acredita no Primeiro Passo (tarefa do navegador) · vigia: Seduc PI (lembretes 1/02 e 3/05) |
| **Maranhão** (3) | Senac MA e SENAI MA (`senac_ma.py`, Claude) · IEMA, editais FIC (notícias oficiais) |
| **Pará** (103) | Senac PA, PSG (`senac_pa.py`, código) · SENAI PA (`senai_pa.py`, código) |
| **Amazonas** (1, 1 por abrir) | Cetam (`cetam.py`, código; «Por abrir» desde que o edital sai, 27/11) · Senac AM e SENAI AM (`senac_ma.py`, Claude) · notícias da Prefeitura de Manaus (`noticias_oficiais.py`) · vigias: SENAI AM (chamada pública), OELA |
| **Amapá** (10, 1 por abrir) | Senac AP e SENAI AP (`senac_ma.py`, Claude) · Ifap ProEJA e EJA estadual (à mão; lembrete 5/01) |
| **Acre** (14, 2 por abrir) | Senac AC (`senac_ma.py`, Claude) |
| **Rondônia** (4) | IFRO, FIC (`ifro_fic.py`, código) · Programa Vencer, SEAS (vigia) · SENAI RO, Gratuidade Regimental (`senai_ro.py`, código: página + editais de aprendizagem) · Senac RO (`senac_ma.py`, Claude) · IDEP e Prefeitura de Porto Velho (notícias oficiais) |
| **Roraima** (1) | Escola Barão de Parima (à mão a 27/11) · Senac RR (`senac_rr.py`, código; turmas todas fechadas a 26/11) · Escolegis da ALE-RR e Governo de Roraima (notícias oficiais) |
| **Tocantins** (1) | Senac TO (`senac_to.py`, código) · Prefeitura de Palmas (notícias oficiais) |
| **Goiás** (2, 1 por abrir) | Prefeitura de Goiânia, EJA 2027 «Por abrir» a 04/01 (à mão, auditoria 5) · Seduc-GO, EJA (à mão, 27/11) · a fazer: Senac GO, SENAI GO, IFG, IF Goiano, Prefeitura de Goiânia |
| **Distrito Federal** (9) | Sedet-DF, Jornada da Mulher Trabalhadora (à mão, 27/11) · IFB, 7 cursos técnicos EJA-EPT 2027 «Por abrir» (à mão, 27/11; o IFB pede CAPTCHA ao GitHub) · SENAI DF, Gratuidade Regimental, Edital 01/2027 (curso geral à mão, 27/11; o site não responde ao GitHub; na tarefa do navegador) · Senac DF bloqueia o GitHub e o Chrome, com e sem VPN |
| **Mato Grosso** (7) | IFMT, 7 cursos técnicos subsequentes (vagas remanescentes, Edital 234/2026, até 13/12; à mão, auditoria 5) · notícias do SENAI MT (`noticias_oficiais.py`) · Senac MT (sem lista de vagas: inscrição por WhatsApp ou na unidade) · SER Família Capacita (SENAI MT e Governo de MT, 50 mil vagas para pessoas vulneráveis; o painel do Power BI só tem turmas de julho de 2026) · IFMT: seleções 2027/1 já fechadas (agosto e setembro); selecao.ifmt.edu.br com erro de certificado |
| **Mato Grosso do Sul** (17) | Senac MS (`senac_ms.py`, código: consulta de vagas e editais em PDF) · IFMS, 8 cursos técnicos EJA EPT 2027.1 (à mão, 27/11; o IFMS recusa o GitHub e a VPN, abre no Chrome sem VPN; o 2027.2 abre inscrições em maio) · notícias do SENAI MS (`noticias_oficiais.py`) |
| **On-line, todo o Brasil** (674) | Escola Virtual de Governo, Fundação Bradesco, FGV, Escola do Trabalhador 4.0, Aprenda Mais, Sebrae (resumo) · catálogos sob demanda (`catalogo.py`) · pesquisa semanal (`cursos.py`, Claude) |

Todos os estados recebem também a pesquisa semanal (Claude) e a verificação (Claude).

**Notícias oficiais** (`noticias_oficiais.py`, lista `FONTES`): leem a página ou a pesquisa do site oficial; uma notícia nova sobre cursos vira um curso «Novo», que a verificação (Claude) ou uma pessoa confere antes de publicar.

**Vigias** (`vigiar.py`): fontes ainda fechadas ou sem lista legível. Avisam nas Pendências quando a página muda. Os vigias do Google Notícias fazem uma pausa de 4 s entre pedidos; num erro 429 esperam e tentam de novo (30, 60, 120 s) e, se o bloqueio continuar, os restantes ficam para o dia seguinte (27/11: 36 falhas numa só rodada antes da correção).

**Não abrem a partir do GitHub** (lidos pela tarefa do navegador; lista em `fontes_navegador.json`): Prefeituras de Boa Vista, Teresina, Aracaju, São Luís e Recife (notícias); Governos de Sergipe, Tocantins, Maranhão e Pernambuco (notícias); Seduc PI; site da Cagece.

**Retirado**: SENAI Play (`senai_play.py`, 24/11): o certificado é pago (regra E1).
