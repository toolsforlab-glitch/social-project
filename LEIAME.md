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
| **Atualizar o site** (`site.yml`) | Quando muda a pasta `site/`, ou à mão depois de editar a folha | Lê as turmas do Senac e volta a gerar as páginas a partir da folha |

`turmas.py` também cria em Cursos, com Estado **Novo**, cada curso do Senac que tenha uma turma aberta e ainda não esteja na folha (título e descrição copiados da página da turma; regras do programa copiadas da página "Bolsas de estudos"). O curso é publicado sozinho quando tem uma turma aberta aprovada na auditoria. Os cursos do Senac PSG deixam de passar pela verificação com Claude.

`centec.py` faz o mesmo para a Rede CVT (Instituto Centec): lê da página oficial as turmas com inscrição on-line (Centec Academy) e presencial (local e telefone), audita cada cartão (as datas e o horário aparecem duas vezes e têm de coincidir) e cria e publica os cursos. O Centec não indica prazo: a turma conta como aberta enquanto estiver na lista oficial e não tiver começado.

`senac_ma.py` lê os editais do Programa Senac de Gratuidade do Maranhão (lista pública em ma.senac.br/editais-psg). Para cada edital recente tira o texto do documento oficial (PDF; Word antigo convertido pelo LibreOffice; Word novo), o Claude extrai o período de inscrição, o modo e o local de inscrição e cada curso do Anexo I, e o código confere cada frase no documento (a frase de cada curso tem de conter o nome e a data de início). Auditoria antes de publicar: datas coerentes, inscrição perto da data do edital, aulas depois da inscrição, horário com sentido, cidade escrita no documento; o que falha fica em Rever. A turma fica Aberta até ao fim do dia em que a inscrição termina. Um termo aditivo manda as turmas do edital alterado para Rever. O estado dos editais já lidos fica em `estado/senac_ma.json` (um edital sem cursos comprovados é relido uma vez).

Públicos prioritários (aba Perfis: mulheres, pessoas LGBTQIA+, população negra, quilombolas e indígenas, pessoas com deficiência, etc.): um curso só recebe um perfil quando a página diz que é feito para esse grupo, só o aceita, ou lhe reserva vagas ou prioridade. A verificação guarda essa frase (campo "público") e o código confere que a frase nomeia o grupo (`perfis_da_frase` em base.py); sem frase, o curso fica "todos". Há pesquisas semanais dedicadas (ce-mulheres, ce-lgbtqia, ce-igualdade-racial, ma-publicos-prioritarios), e os editais do Senac MA registam as vagas reservadas na coluna "Vagas reservadas" (Turmas).

As turmas do Senac Ceará, do Centec e do Senac Maranhão (`turmas.py` e `centec.py` sem Claude; `senac_ma.py` com Claude) são lidas todos os dias na rotina das notícias, à segunda na rotina semanal e sempre que se corre "Atualizar o site".

O site fica em `docs/` (GitHub Pages). O resumo da semana fica em `docs/semanal/` (`whatsapp.txt`, `cartaz.pdf`, `newsletter.html`).

## O que o site faz por quem procura um curso

- **Posso me inscrever?** Perguntas simples por curso (idade, escolaridade, renda, experiência) com resposta imediata. Nada é guardado.
- **O que facilita para você?** Filtros "À noite", "Sem precisar de internet", "Sem escolaridade exigida", "Com ajuda de custo" e "Cidade". Só entram cursos em que isso está comprovado.
- **Antes de começar:** guias para tirar o CPF, criar e subir a conta gov.br e fazer o CadÚnico, ligados aos cursos que os exigem.
- **Onde se inscrever:** morada, horário de matrículas e o que levar, da unidade mais próxima.
- **Botão que leva ao curso, não a uma lista:** cada curso aponta para a sua página própria (`paginas.py`, coluna "Página do curso"). No Senac PSG, cada curso mostra as turmas abertas, cada uma com a sua página e o prazo de inscrição (`turmas.py`, separador "Turmas").

## Como se evita informação errada

- **O que a página oficial não diz fica vazio.** O Claude nunca deduz datas, gratuidade, requisitos ou contactos.
- **Página própria do curso.** O botão do site só diz "Ver curso e se inscrever" quando a página do curso foi confirmada por código (o título do curso está no título da página). Sem ela, diz "Procurar este curso na página oficial".
- **Turmas pelas datas da própria página.** Uma turma do Senac está Aberta até ao fim do dia do prazo de inscrição que a página indica; sem prazo, até começar. O selo "Inscrições abertas" da lista não conta.
- **Publicação com auditoria independente.** Nada é publicado só porque uma leitura o diz. Turmas do Senac: a página é lida duas vezes por métodos diferentes, as leituras têm de coincidir e as datas têm de fazer sentido; as que passam são publicadas, as outras ficam em Rever com o motivo (coluna Auditoria). Cursos encontrados na web: depois da verificação, um segundo modelo (`modelo_auditoria`), que não escreveu os dados, tem de confirmar cada afirmação com a frase exata da página, e o código confere as frases; só então o curso passa de Novo a Publicado. Oculto e Rever postos por uma pessoa nunca são alterados.
- **Unidades e guias também são publicados com auditoria.** Uma unidade é publicada quando a morada está comprovada na página oficial e não tem avisos (`verificar_organizacoes.py`). Um guia "Antes de começar" é publicado quando as frases da Evidência estão na página e um segundo modelo confirma cada passo com frases exatas (`guias.py`).
- **O que terminou sai da base.** Um curso expira quando passa o prazo de inscrição, quando começa (se não tiver prazo) ou quando deixa de ser encontrado. Cursos e turmas terminados há mais de 30 dias passam para os separadores "Arquivo de cursos" e "Arquivo de turmas" (`arquivar.py`), sem serem apagados.
- **Notícias só do Brasil, publicadas sozinhas.** A rotina escolhe apenas notícias sobre o Brasil e o site só mostra essas.
- **Gratuidade por entidade.** Na aba "Sites de confiança", a coluna "Tudo gratuito" só é marcada por uma pessoa, para entidades onde todos os cursos são grátis. Nesses sites, um curso cuja página não fala em preço conta como gratuito; se a página falar em pagamento, vale a página.
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

## Ligar as rotinas

As rotinas estão paradas até existir a variável **ROTINAS_ATIVAS = sim** (Settings → Secrets and variables → Actions → separador Variables). Antes de a criar, configure os segredos `ANTHROPIC_API_KEY`, `GOOGLE_CREDENTIALS` e `FOLHA_ID`.

## Correr à mão

Separador **Actions** → escolher a rotina → **Run workflow**. Na rotina semanal pode indicar só algumas pesquisas (ex.: `ce-sistema-s,ce-estado`).

## Custo aproximado

Cerca de 0,03 USD por dia nas notícias e 1,5 USD por semana nos cursos e verificações (9 pesquisas ativas), ou seja perto de 7 USD por mês. Os editais do Senac Maranhão custam cerca de 0,03 USD por edital lido (uns três por semana). Desligar pesquisas na aba Pesquisas de cursos reduz o custo.
