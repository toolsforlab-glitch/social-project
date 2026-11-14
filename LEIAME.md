# Projeto Social (nome provisório)

Site com cursos gratuitos e informação útil, começando por um piloto no **Ceará** (mais cursos on-line do Brasil). Tudo é gerido numa folha do Google Sheets e publicado sozinho pelo GitHub Actions, com o Claude (API da Anthropic) a pesquisar, verificar e escrever em linguagem simples.

## Onde se gere tudo: a folha

**Projeto Social – Base de dados** (Google Sheets). Cada aba é uma tabela:

| Aba | Para quê |
|---|---|
| Cursos | Todos os cursos. A coluna **Estado** decide o que aparece no site |
| Notícias | Notícias do setor social escolhidas todos os dias |
| Propostas de parceiros | O que as organizações enviam pelo formulário. Mudar o Estado para **Aceite** cria o curso |
| Métricas | Uma linha por semana |
| Pesquisas de cursos, Sites de confiança, Locais, Fontes de notícias, Temas, Necessidades, Perfis | As regras das rotinas: o que procurar, onde, e o que as pessoas podem escolher no site |
| Configuração | Nome, links, território piloto, publicação automática, modelos |

**Estados:** Novo → Publicado, ou Rever / Oculto / Expirado. Com `publicacao_automatica = SIM`, os cursos Novo já aparecem no site; Rever e Oculto nunca aparecem.

Para trabalhar sem a folha (testes), `MODO_LOCAL=1` usa a cópia em `dados_locais/folha.json`.

## O que corre e quando

| Rotina | Quando | O que faz |
|---|---|---|
| **Notícias do dia** (`noticias.yml`) | Todos os dias, 09:17 UTC | Escolhe e resume as notícias, trata propostas aceites e atualiza o site |
| **Cursos e resumo da semana** (`semanal.yml`) | Segundas, 08:23 UTC | Pesquisa cursos → verifica cada página e escreve o passo a passo de inscrição → verifica as organizações → propostas de parceiros → site → texto do WhatsApp, cartaz em PDF com QR code e newsletter |
| **Atualizar o site** (`site.yml`) | Quando muda a pasta `site/`, ou à mão depois de editar a folha | Volta a gerar as páginas a partir da folha |

O site fica em `docs/` (GitHub Pages). O resumo da semana fica em `docs/semanal/` (`whatsapp.txt`, `cartaz.pdf`, `newsletter.html`).

## O que o site faz por quem procura um curso

- **Posso me inscrever?** Perguntas simples por curso (idade, escolaridade, renda, experiência) com resposta imediata. Nada é guardado.
- **O que facilita para você?** Filtros "À noite", "Sem precisar de internet", "Sem escolaridade exigida", "Com ajuda de custo" e "Cidade". Só entram cursos em que isso está comprovado.
- **Antes de começar:** guias para tirar o CPF, criar e subir a conta gov.br e fazer o CadÚnico, ligados aos cursos que os exigem.
- **Onde se inscrever:** morada, horário de matrículas e o que levar, da unidade mais próxima.

## Como se evita informação errada

- **O que a página oficial não diz fica vazio.** O Claude nunca deduz datas, gratuidade, requisitos ou contactos.
- **Prova por código.** Nos cursos, cada afirmação importante exige a frase exata da página, e o script confirma que ela existe (`verificar.py`). Nas organizações, cada dado é procurado no texto bruto da fonte (`verificar_organizacoes.py`, sem Claude).
- **Resumos não são fonte.** Ferramentas que resumem páginas servem para descobrir, nunca para preencher a folha.
- **A rotina marca, uma pessoa decide.** "Mudança a rever" só é desmarcada por uma pessoa; "Revisto por pessoa" impede a rotina de alterar campos importantes.
- **No site só aparece o que está comprovado** (ou revisto por uma pessoa). O WhatsApp e o cartaz só levam cursos Abertos e sem dúvidas pendentes.
- Tudo o que a rotina muda fica no separador **Histórico de verificações**.

## Segredos (Settings → Secrets and variables → Actions)

| Segredo | Para quê | Obrigatório |
|---|---|---|
| `ANTHROPIC_API_KEY` | Pesquisar, verificar e resumir | Sim |
| `GOOGLE_CREDENTIALS` | Chave JSON da conta de serviço do Google com acesso de edição à folha | Sim |
| `FOLHA_ID` | O ID da folha (a parte do link entre `/d/` e `/edit`) | Sim |
| `BREVO_API_KEY`, `BREVO_LISTA_ID`, `EMAIL_ADMIN` | Enviar a newsletter e o texto semanal por email | Não |

## Correr à mão

Separador **Actions** → escolher a rotina → **Run workflow**. Na rotina semanal pode indicar só algumas pesquisas (ex.: `ce-sistema-s,ce-estado`).

## Custo aproximado

Cerca de 0,03 USD por dia nas notícias e 1,5 USD por semana nos cursos e verificações (9 pesquisas ativas), ou seja perto de 7 USD por mês. Desligar pesquisas na aba Pesquisas de cursos reduz o custo.
