# Projeto Social (nome provisório)

Site com informação e oportunidades para quem ajuda e para quem precisa: cursos gratuitos, notícias do setor social e, em breve, vagas, voluntariado e um diretório de organizações.

Tudo corre sozinho no GitHub Actions, com o Claude (API da Anthropic) a escolher e a resumir os conteúdos.

## O que corre e quando

| Rotina | Quando | O que faz |
|---|---|---|
| **Notícias do dia** (`noticias.yml`) | Todos os dias, 07:17 UTC | Lê os feeds de `config.json`, o Claude escolhe até 8 notícias e escreve um resumo em português |
| **Cursos e resumo da semana** (`semanal.yml`) | Segundas-feiras, 06:23 UTC | O Claude pesquisa cursos gratuitos só nos sites de confiança da configuração; a rotina confirma que cada link abre; gera a newsletter e a publicação para o WhatsApp |
| **Atualizar o site** (`site.yml`) | Quando se muda `config.json` ou a pasta `site/` | Volta a gerar as páginas |

O site fica na pasta `docs/` e é publicado pelo GitHub Pages.

## Mudar coisas sem mexer no código (`config.json`)

- **Nome e frase do projeto:** `nome` e `slogan`. O site atualiza-se sozinho.
- **Link do canal de WhatsApp:** `links.canal_whatsapp`.
- **Fontes de notícias:** `noticias.fontes` (nome, link do feed RSS, idioma).
- **O que as pessoas podem escolher ("Quero aprender…"):** `cursos.necessidades`.
- **Regiões:** `cursos.locais`, com os sites de confiança de cada uma em `cursos.dominios` e o que procurar em `cursos.pesquisas`.
- **Perfis internos** (nunca aparecem no site; servem para classificar os cursos): `cursos.perfis_internos`.

## Segredos (Settings → Secrets and variables → Actions)

| Segredo | Para quê | Obrigatório |
|---|---|---|
| `ANTHROPIC_API_KEY` | Escolher notícias e pesquisar cursos | Sim |
| `BREVO_API_KEY` | Enviar a newsletter e o email com a publicação de WhatsApp | Não |
| `BREVO_LISTA_ID` | Número da lista de subscritores da newsletter no Brevo | Não |
| `EMAIL_ADMIN` | Email que recebe todas as semanas o texto para colar no canal de WhatsApp | Não |

Sem o Brevo, o texto da semana para o WhatsApp fica em `docs/semanal/whatsapp.txt` (também acessível no site, em `/semanal/whatsapp.txt`).

## Correr à mão

Separador **Actions** → escolher a rotina → **Run workflow**.
