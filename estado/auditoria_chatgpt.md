Você vai me ajudar a auditar informações de cursos gratuitos para pessoas em situação de vulnerabilidade no Brasil. Preciso de provas escritas, não de conclusões. Use a pesquisa na web.

Regras:
- Procure só em páginas OFICIAIS da entidade de cada curso (o domínio indicado em cada curso): primeiro na própria página ou edital do curso, depois na página do programa no site da entidade. Não servem notícias, blogs nem sites de terceiros. Não deduza.
- Para cada pergunta, copie a frase EXATA, letra a letra, sem resumir, e o link exato da página onde ela está.
- Quando não encontrar uma frase, responda null nessa pergunta. É melhor null do que uma frase aproximada.
- Hoje é 2026-11-26.

O que significa cada pergunta:
- "certificado": se o curso dá certificado e se é gratuito; valor "gratuito", "pago" ou "sem certificado", com a frase que fala do certificado.

Cursos:
1. Cursos de beleza, gastronomia e turismo (Qualifica Natal, 8º ciclo)
   Entidade: Prefeitura do Natal (Semtas, Centros Municipais de Trabalho e Empreendedorismo)
   Página ou edital: https://natal.rn.gov.br/news/post2/46141
   Domínio oficial: rn.gov.br
   Perguntas: certificado

2. Aperfeiçoamento Profissional em Empregabilidade: A Nova Rota da Formação Profissional
   Entidade: SENAI Bahia (em parceria com a Borborema Recursos Minerais)
   Página ou edital: https://www.senaibahia.com.br/processo-seletivo-borborema/
   Domínio oficial: senaibahia.com.br
   Perguntas: certificado

3. Técnico em Eventos
   Entidade: Senac Bahia (Programa Senac de Gratuidade)
   Página ou edital: https://www.ba.senac.br/page/psg-consulta-de-vagas
   Domínio oficial: ba.senac.br
   Perguntas: certificado

4. Inglês para iniciantes (A1), às quartas-feiras
   Entidade: Ifac – Instituto Federal do Acre (Campus Rio Branco)
   Página ou edital: https://editais.ifac.edu.br/quero-estudar-no-ifac/edital/1206/arquivos/
   Domínio oficial: ifac.edu.br
   Perguntas: certificado

5. Preparação de Bolos e Tortas Contemporâneas
   Entidade: Senac Tocantins (Programa Senac de Gratuidade)
   Página ou edital: https://www.to.senac.br/cursos/abertos
   Domínio oficial: to.senac.br
   Perguntas: certificado

6. Informática Básica
   Entidade: SENAI Sergipe
   Página ou edital: https://app.fies.org.br/MatriculaWebSENAI/Cursos/Detalhe/7361
   Domínio oficial: fies.org.br
   Perguntas: certificado

7. Word e Excel Avançados
   Entidade: SENAI Sergipe
   Página ou edital: https://app.fies.org.br/MatriculaWebSENAI/Cursos/Detalhe/7363
   Domínio oficial: fies.org.br
   Perguntas: certificado

Responda só com um bloco JSON, sem texto antes nem depois, com uma chave por número de curso e, dentro, uma chave por pergunta, assim:
{"1": {"gratuito": {"valor": "…ou null", "frase": "…", "url": "…"}}, "2": {…}}
Quando não encontrar uma frase, ponha {"valor": null, "frase": null, "url": null} nessa pergunta.
