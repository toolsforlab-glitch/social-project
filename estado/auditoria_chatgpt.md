Você vai me ajudar a auditar informações de cursos gratuitos para pessoas em situação de vulnerabilidade no Brasil. Preciso de provas escritas, não de conclusões. Use a pesquisa na web.

Regras:
- Procure só em páginas OFICIAIS da entidade de cada curso (o domínio indicado em cada curso): primeiro na própria página ou edital do curso, depois na página do programa no site da entidade. Não servem notícias, blogs nem sites de terceiros. Não deduza.
- Para cada pergunta, copie a frase EXATA, letra a letra, sem resumir, e o link exato da página onde ela está.
- Quando não encontrar uma frase, responda null nessa pergunta. É melhor null do que uma frase aproximada.
- Hoje é 2026-11-22.

O que significa cada pergunta:
- "certificado": se o curso dá certificado e se é gratuito; valor "gratuito", "pago" ou "sem certificado", com a frase que fala do certificado.

Cursos:
1. Por que devo entender o que é formalização? E como me preparar?
   Entidade: Sebrae (cursos online)
   Página ou edital: https://loja.sebrae.com.br/por-que-devo-entender-o-que-e-formalizac-o-e-como-me-preparar-a0jv2000000h5cnmaa
   Domínio oficial: sebrae.com.br
   Perguntas: certificado

2. A gestão da propriedade rural por um novo ponto de vista
   Entidade: Sebrae (cursos online)
   Página ou edital: https://loja.sebrae.com.br/a-gest-o-da-propriedade-rural-por-um-novo-ponto-de-vista-a0jv2000000h5damaq
   Domínio oficial: sebrae.com.br
   Perguntas: certificado

Responda só com um bloco JSON, sem texto antes nem depois, com uma chave por número de curso e, dentro, uma chave por pergunta, assim:
{"1": {"gratuito": {"valor": "…ou null", "frase": "…", "url": "…"}}, "2": {…}}
Quando não encontrar uma frase, ponha {"valor": null, "frase": null, "url": null} nessa pergunta.
