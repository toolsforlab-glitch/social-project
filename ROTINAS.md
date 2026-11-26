# Rotinas e fontes

O que corre, quando, e de onde vêm os cursos de cada estado. As regras estão em [REGRAS.md](REGRAS.md); o detalhe de cada leitor está no LEIAME, na secção da fonte.

Última revisão: 26/11/2026. Legenda: **código** = lido por código, sem Claude · **Claude** = precisa da API da Anthropic (**parada até 1/12/2026**) · **resumo** = só o resumo usa Claude; os dados vêm por código.

## 1. Rotinas

| Rotina | Quando (hora de Fortaleza) | O que faz |
|---|---|---|
| **Notícias do dia** (`noticias.yml`) | todos os dias, 06:17; reserva às 10:17 | Notícias do site (Claude) → turmas e listas oficiais (código, ver secção 2) → matrícula dos editais novos → notícias oficiais (código) e verificação das novas (Claude) → editais do Senac MA e afins (Claude) → Cetam → catálogos on-line (resumo) → gera e publica o site |
| **Cursos e resumo da semana** (`semanal.yml`) | segundas, 05:23; reserva às 11:23 | Pesquisa de cursos novos (Claude) → catálogos sob demanda → verificação de todos os cursos (Claude) → unidades → arquivar o que terminou → guias «Antes de começar» → turmas → site → WhatsApp, cartaz e newsletter → publica |
| **Atualizar o site** (`site.yml`) | quando muda o aspeto do site, ou à mão | Turmas do Senac CE e Centec → unidades → gera o site → auditoria dos requisitos (só avisa) → publica |
| **Rodar um passo** (`verificar.yml`) | à mão | Corre um só script (lista no próprio ficheiro) e publica o site |

A ordem entre rotinas é dada por `scripts/vez.py`: uma espera que a outra acabe.

**Tarefas agendadas no Claude** (fora do GitHub):
- Disparo de segurança da rotina diária (todos os dias, 09:41 em Lisboa) e da semanal (segundas, 08:47 UTC). Só disparam se o GitHub ainda não a correu.
- Lembretes nesta conversa: 1/12 (API de volta: conferir os leitores Claude e as notícias novas), 5/01/2027 (abre a EJA do Amapá), 6/01 (EJA da Bahia), 1/02 e 3/05 (Seduc PI).

## 2. Fontes por estado

Cursos presenciais visíveis no site a 26/11/2026 entre parênteses.

| Estado | Fontes e leitor |
|---|---|
| **Ceará** (24) | Senac CE, turmas do PSG (`turmas.py`, código) · Centec (`centec.py`, código) · Cagece Capacita e Prefeitura de Fortaleza, notícias e Fortaleza Inclusiva (notícias oficiais) · EJA (à mão) · vigia: IFCE |
| **Rio Grande do Norte** (3) | IFRN, FIC, extensão e ProEJA (`ifrn_fic.py`, código) · Semtas Natal (notícias oficiais) · vigias: SENAI RN, Senac RN |
| **Paraíba** (3) | Caminhos Digitais (`caminhos_digitais.py`, código) · vigias: Senac PB, IFPB |
| **Pernambuco** (2) | GO Recife / Qualifica Recife (`gorecife.py`, código) · Qualifica PE, notícias da SEDEPE (notícias oficiais) · SENAI PE (`senac_ma.py`, Claude) · vigia: Senac PE |
| **Alagoas** (6) | OxeTech Lab (`oxetech.py`, código) · Senac AL e SENAI AL (`senac_ma.py`, Claude) · Prefeitura de Maceió (notícias oficiais) |
| **Sergipe** (0) | vigia: Senac SE · SENAI SE só abre com VPN do Brasil (pendência) |
| **Bahia** (9) | Senac BA, PSG (`senac_ba.py`, código) · Treinar para Empregar, Salvador (`salvador_tpe.py`, código) · vigias: SENAI BA, SEC BA (técnicos por sorteio), IF Baiano, 4 OSCs aprovadas · EJA (lembrete 6/01) |
| **Piauí** (0) | Senac PI e SENAI PI (`senac_ma.py`, Claude; o Senac PI tem o certificado do site expirado) · Governo do Piauí (notícias oficiais) · vigia: Seduc PI (lembretes 1/02 e 3/05) |
| **Maranhão** (2) | Senac MA e SENAI MA (`senac_ma.py`, Claude) · IEMA, editais FIC (notícias oficiais) |
| **Pará** (102) | Senac PA, PSG (`senac_pa.py`, código) · SENAI PA (`senai_pa.py`, código) |
| **Amazonas** (0) | Cetam (`cetam.py`, código) · Senac AM e SENAI AM (`senac_ma.py`, Claude) · vigias: SENAI AM (chamada pública), OELA |
| **Amapá** (10) | Senac AP e SENAI AP (`senac_ma.py`, Claude) · Ifap ProEJA e EJA estadual (à mão; lembrete 5/01) |
| **Acre** (4) | Senac AC (`senac_ma.py`, Claude) |
| **Rondônia** (0) | IFRO, FIC (`ifro_fic.py`, código) · Senac RO (`senac_ma.py`, Claude) · IDEP e Prefeitura de Porto Velho (notícias oficiais) |
| **Roraima** (0) | Senac RR (`senac_rr.py`, código; turmas todas fechadas a 26/11) · Escolegis da ALE-RR e Governo de Roraima (notícias oficiais) |
| **Tocantins** (1) | Senac TO (`senac_to.py`, código) · Prefeitura de Palmas (notícias oficiais) |
| **On-line, todo o Brasil** (645) | Escola Virtual de Governo, Fundação Bradesco, FGV, Escola do Trabalhador 4.0, Aprenda Mais, Sebrae (resumo) · catálogos sob demanda (`catalogo.py`) · pesquisa semanal (`cursos.py`, Claude) |

Todos os estados recebem também a pesquisa semanal (Claude) e a verificação (Claude).

**Notícias oficiais** (`noticias_oficiais.py`, lista `FONTES`): leem a página ou a pesquisa do site oficial; uma notícia nova sobre cursos vira um curso «Novo», que a verificação (Claude) ou uma pessoa confere antes de publicar.

**Vigias** (`vigiar.py`): fontes ainda fechadas ou sem lista legível. Avisam nas Pendências quando a página muda.

**Não abrem a partir do GitHub** (só pelo navegador, ou à espera): Prefeituras de Boa Vista, Teresina, Aracaju, São Luís e Recife (notícias); Governos de Sergipe, Tocantins, Maranhão e Pernambuco (notícias); Seduc PI; site da Cagece.

**Retirado**: SENAI Play (`senai_play.py`, 24/11): o certificado é pago (regra E1).
