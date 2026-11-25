Você vai me ajudar a encontrar onde e quando pessoas jovens e adultas podem se matricular na EJA (Educação de Jovens e Adultos) da rede pública estadual, para voltar a estudar. Preciso de provas escritas, não de conclusões. Use a pesquisa na web. Hoje é 2026-11-25.

Para cada estado abaixo, procure a página OFICIAL da Secretaria de Educação do estado (domínio terminado em .<sigla do estado>.gov.br, por exemplo seduc.ce.gov.br ou educacao.ba.gov.br) que diga:
- "periodo": o período de matrícula ou inscrição na EJA para 2027 (ou para o 1º semestre de 2027), ou que a matrícula na EJA fica aberta o ano todo. Pode ser uma notícia no site da própria secretaria, uma portaria ou um edital de matrícula.
- "como": como e onde a pessoa se matricula na EJA (site de matrícula, na escola, telefone).
- "requisitos": idade mínima ou documentos pedidos para a matrícula na EJA.

Regras:
- Só sites oficiais do governo do estado (….<sigla>.gov.br). Não servem jornais, blogs, portais de notícias nem sites de terceiros.
- Copie cada frase EXATA, letra a letra, sem resumir nem corrigir, com o link exato da página ou do PDF.
- Se só houver informação de 2026 (matrícula já encerrada), diga isso no campo "observacao" e ponha as frases de 2027 como null.
- Não deduza. Quando não encontrar, ponha null. É melhor null do que uma frase aproximada.

Estados:
- AC: Acre
- AL: Alagoas
- AP: Amapá
- AM: Amazonas
- BA: Bahia
- CE: Ceará
- MA: Maranhão
- PA: Pará
- PB: Paraíba
- PE: Pernambuco
- PI: Piauí
- RN: Rio Grande do Norte
- RO: Rondônia
- RR: Roraima
- SE: Sergipe
- TO: Tocantins

Responda só com um bloco JSON, sem texto antes nem depois, com uma chave por sigla do estado:
{"CE": {"periodo": {"frase": "…", "url": "…"}, "como": {"frase": "…", "url": "…"}, "requisitos": {"frase": "…", "url": "…"}, "observacao": "…"}, "BA": {…}}
