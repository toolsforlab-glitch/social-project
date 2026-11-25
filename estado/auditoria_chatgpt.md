Você vai me ajudar a auditar informações de cursos gratuitos para pessoas em situação de vulnerabilidade no Brasil. Preciso de provas escritas, não de conclusões. Use a pesquisa na web.

Regras:
- Procure só em páginas OFICIAIS da entidade de cada curso (o domínio indicado em cada curso): primeiro na própria página ou edital do curso, depois na página do programa no site da entidade. Não servem notícias, blogs nem sites de terceiros. Não deduza.
- Para cada pergunta, copie a frase EXATA, letra a letra, sem resumir, e o link exato da página onde ela está.
- Quando não encontrar uma frase, responda null nessa pergunta. É melhor null do que uma frase aproximada.
- Hoje é 2026-11-25.

O que significa cada pergunta:
- "gratuito": uma frase que diga, com essas palavras, que este curso, ou as vagas do programa a que ele pertence, é gratuito (ex.: "gratuito", "vagas gratuitas", "sem custo", "sem ônus", "bolsa integral"). O nome do programa sozinho (ex.: "Programa Senac de Gratuidade") não serve.
- "situacao": se as inscrições deste curso estão abertas ou encerradas HOJE (2026-11-25); valor "aberto" ou "encerrado", com a frase que o diz (ex.: "inscrições abertas", "inscreva-se", "inscrições encerradas"). Um curso CLARAMENTE sob demanda, sem datas, conta como "aberto" se a página o disser com palavras (ex.: "faça no seu ritmo", "comece quando quiser", "acesso imediato"); um botão sozinho não chega.
- "inscricoes_ate": a data-limite de inscrição; valor no formato AAAA-MM-DD, com a frase onde essa data está escrita.
- "certificado": se o curso dá certificado e se é gratuito; valor "gratuito", "pago" ou "sem certificado", com a frase que fala do certificado.

Cursos:
1. Aprender inglês e espanhol
   Entidade: Ministério da Educação (MEC Idiomas)
   Página ou edital: https://www.gov.br/mec/pt-br/mec-idiomas
   Domínio oficial: www.gov.br
   Perguntas: gratuito, certificado

2. Auxiliar de cozinha
   Entidade: Senac Maranhão (Programa Senac de Gratuidade)
   Página ou edital: https://ma.senac.br/editais_psg/edital-senac-ma-psg-2026-no-172-auxiliar-de-cozinha-e-pizzaiolo-barreirinhas-ma/
   Domínio oficial: ma.senac.br
   Perguntas: gratuito

3. Auxiliar de Linha de Produção
   Entidade: SENAI Pernambuco (Gratuidade Regimental)
   Página ou edital: https://www.pe.senai.br/wp-content/uploads/2026/11/EDITAL_-_QUA_-_SANTO_AMARO_-_AUXILIAR_DE_LINHA_DE_PROD._-_PR_20261123130333507156.pdf
   Domínio oficial: pe.senai.br
   Perguntas: gratuito, certificado

4. 32 cursos de capacitação profissional (Programa Autonomia Econômica)
   Entidade: Prefeitura de Fortaleza (SDE – Plano Fortaleza Inclusiva)
   Página ou edital: https://www.fortaleza.ce.gov.br/noticias/prefeitura-de-fortaleza-oferta-7-3-mil-vagas-em-32-cursos-gratuitos-de-capacitacao-profissional
   Domínio oficial: ce.gov.br
   Perguntas: situacao, inscricoes_ate, certificado

5. Gestão de Departamento de Pessoal
   Entidade: Senac Sergipe (Programa Senac de Gratuidade)
   Página ou edital: https://www.se.senac.br/senac-sergipe-abre-vagas-647-vagas-para-36-cursos-de-gratuitos/
   Domínio oficial: se.senac.br
   Perguntas: situacao

6. Cursos técnicos a distância (Santo Estêvão)
   Entidade: IF Baiano
   Página ou edital: https://ingresso.ifbaiano.edu.br/concursos/subsequente-ead-santo-estevao-2027/
   Domínio oficial: ifbaiano.edu.br
   Perguntas: inscricoes_ate

7. Inglês
   Entidade: Instituto Federal do Acre (Ifac)
   Página ou edital: https://editais.ifac.edu.br/edital/visualizacao/8656/
   Domínio oficial: ifac.edu.br
   Perguntas: certificado

8. NR10
   Entidade: Prefeitura do Recife – Qualifica Recife (GO Recife)
   Página ou edital: https://gorecife.recife.pe.gov.br/cursos
   Domínio oficial: pe.gov.br
   Perguntas: certificado

9. Assistente de Marketing e Vendas
   Entidade: Prefeitura de Maceió (Semtes) com o Senac
   Página ou edital: https://maceio.al.gov.br/noticias/semtes/prefeitura-de-maceio-oferta-50-vagas-em-cursos-gratuitos-de-qualificacao-profissional-para-2027
   Domínio oficial: al.gov.br
   Perguntas: certificado

10. Operador de Computador integrado ao ensino médio (EJA, curso FIC)
   Entidade: IFRN (Instituto Federal do Rio Grande do Norte)
   Página ou edital: https://processoseletivo.ifrn.edu.br/edital/visualizar/696/
   Domínio oficial: ifrn.edu.br
   Perguntas: certificado

Responda só com um bloco JSON, sem texto antes nem depois, com uma chave por número de curso e, dentro, uma chave por pergunta, assim:
{"1": {"gratuito": {"valor": "…ou null", "frase": "…", "url": "…"}}, "2": {…}}
Quando não encontrar uma frase, ponha {"valor": null, "frase": null, "url": null} nessa pergunta.
