"""Temporário (28/11/2026): pesquisas semanais e sites de confiança do Centro-Oeste, Sudeste e Sul.

A revisão T15 antes do Sul mostrou que o Centro-Oeste e o Sudeste ficaram sem linhas em «Pesquisas de cursos» e
«Sites de confiança» (só os locais tinham sido ligados). O modelo é o do Rio Grande do Norte (7 pesquisas por estado).
«Tudo gratuito» só nos institutos federais e nas Secretarias da Educação (escolas públicas, decisão do responsável de
23/11/2026, já aplicada ao Nordeste e ao Norte)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base import Base  # noqa: E402

J = "Só para descobrir: cursos com link de notícia entram em Rever"
EP = "Escola pública: institutos federais e Secretarias da Educação (decisão do responsável, 23/11/2026)"

# sigla: (nome, «no/na/em» nome, cidades, fontes da pesquisa geral, jornais da pesquisa de notícias, igualdade e
#         mulheres, pcd, idades, prefeitura da capital, sites [(domínio, notas, tudo gratuito)])
E = {
 "GO": ("Goiás", "em Goiás", "Goiânia, Aparecida de Goiânia, Anápolis, Rio Verde, Luziânia, Águas Lindas, Valparaíso, Trindade, Formosa, Catalão, Itumbiara, Jataí e interior",
        "Programa Senac de Gratuidade em Goiás, Gratuidade Regimental do SENAI Goiás (Sistema Fieg), cursos FIC do IFG e do IF Goiano (todos os campi), Colégios Tecnológicos (Cotecs) e Escolas do Futuro do Governo de Goiás, cursos da Secretaria da Retomada, programas da Prefeitura de Goiânia e de outras prefeituras, extensão da UFG e da UEG, EJA",
        "O Popular, g1 Goiás, Agência Cora (Governo de Goiás)", "Secretaria da Mulher e Secretaria de Desenvolvimento Social de Goiás, programa Mulheres Mil (IFG, IF Goiano), Prefeitura de Goiânia",
        "Superintendência dos Direitos da Pessoa com Deficiência de Goiás, APAEs, Centro de Reabilitação (CRER), associações de surdos e de cegos, Napne do IFG e do IF Goiano",
        "programas de juventude do Governo de Goiás e da Prefeitura de Goiânia, universidades abertas à terceira idade (UFG, UEG)",
        "Prefeitura de Goiânia (Secretaria de Desenvolvimento Econômico, Sine Goiânia, Casa da Mulher)", "goiania.go.gov.br",
        [("go.gov.br", "", False), ("goias.gov.br", "", False), ("ifg.edu.br", EP, True), ("ifgoiano.edu.br", EP, True),
         ("ufg.br", "", False), ("ueg.br", "", False), ("senac.br", "", False), ("senai.br", "", False),
         ("senaigo.com.br", "SENAI Goiás", False), ("sistemafieg.org.br", "", False), ("sebrae.com.br", "", False),
         ("www.gov.br", "", False), ("seduc.go.gov.br", EP, True), ("opopular.com.br", J, False), ("g1.globo.com", J, False)]),
 "DF": ("Distrito Federal", "no Distrito Federal", "Brasília (Plano Piloto), Ceilândia, Taguatinga, Samambaia, Planaltina, Gama, Santa Maria, Sobradinho, Recanto das Emas, São Sebastião, Paranoá, Itapoã, Estrutural e entorno",
        "Programa Senac de Gratuidade no DF, Gratuidade Regimental do SENAI DF (Sistema Fibra), cursos FIC do IFB (todos os campi), escolas técnicas da Secretaria de Educação do DF (EJA e cursos técnicos), cursos da Secretaria do Trabalho (Sedet) e das administrações regionais, extensão da UnB, EJA",
        "Correio Braziliense, Metrópoles, g1 DF, Agência Brasília", "Secretaria da Mulher do DF, Jornada da Mulher Trabalhadora (Sedet), programa Mulheres Mil (IFB), Secretaria de Justiça e Cidadania",
        "Secretaria da Pessoa com Deficiência do DF, APAEs, associações de surdos e de cegos, Napne do IFB",
        "programas de juventude do GDF, universidade aberta à terceira idade (UnB), centros de convivência",
        "Secretaria do Trabalho do DF (Sedet: Agência do Trabalhador, Fábrica Social) e administrações regionais", "df.gov.br",
        [("df.gov.br", "", False), ("ifb.edu.br", EP, True), ("unb.br", "", False), ("senac.br", "", False), ("senai.br", "", False),
         ("sistemafibra.org.br", "SENAI DF", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False),
         ("educacao.df.gov.br", EP, True), ("correiobraziliense.com.br", J, False), ("metropoles.com", J, False), ("g1.globo.com", J, False)]),
 "MT": ("Mato Grosso", "em Mato Grosso", "Cuiabá, Várzea Grande, Rondonópolis, Sinop, Tangará da Serra, Cáceres, Sorriso, Lucas do Rio Verde, Primavera do Leste, Barra do Garças, Alta Floresta e interior",
        "Programa Senac de Gratuidade em Mato Grosso, Gratuidade Regimental do SENAI MT (Sistema Fiemt), cursos FIC e técnicos sem prova do IFMT (todos os campi), escolas técnicas estaduais, cursos da Secretaria de Assistência Social e Cidadania (Setasc), programas da Prefeitura de Cuiabá e de outras prefeituras, extensão da UFMT e da Unemat, EJA",
        "Gazeta Digital, g1 MT, Secom MT", "Secretaria da Mulher e Setasc de Mato Grosso, programa Mulheres Mil (IFMT), Prefeitura de Cuiabá",
        "Superintendência da Pessoa com Deficiência de Mato Grosso, APAEs, associações de surdos e de cegos, Napne do IFMT",
        "programas de juventude do Governo de MT e da Prefeitura de Cuiabá, universidades abertas à terceira idade (UFMT, Unemat)",
        "Prefeitura de Cuiabá (Secretaria de Trabalho e Desenvolvimento Econômico, Sine Cuiabá)", "cuiaba.mt.gov.br",
        [("mt.gov.br", "", False), ("ifmt.edu.br", EP, True), ("ufmt.br", "", False), ("unemat.br", "", False), ("senac.br", "", False),
         ("senai.br", "", False), ("senaimt.ind.br", "SENAI MT", False), ("fiemt.ind.br", "", False), ("sebrae.com.br", "", False),
         ("www.gov.br", "", False), ("seduc.mt.gov.br", EP, True), ("gazetadigital.com.br", J, False), ("g1.globo.com", J, False)]),
 "MS": ("Mato Grosso do Sul", "em Mato Grosso do Sul", "Campo Grande, Dourados, Três Lagoas, Corumbá, Ponta Porã, Naviraí, Nova Andradina, Aquidauana, Sidrolândia, Paranaíba e interior",
        "Programa Senac de Gratuidade em MS, Gratuidade Regimental do SENAI MS (Fiems), cursos FIC e técnicos sem prova do IFMS (todos os campi), cursos da Fundação do Trabalho (Funtrab) e da Secretaria de Assistência Social, programas da Prefeitura de Campo Grande e de outras prefeituras, extensão da UFMS, UEMS e UFGD, EJA",
        "Campo Grande News, Correio do Estado, g1 MS, Agência de Notícias do Governo de MS", "Subsecretaria de Políticas para as Mulheres de MS, Casa da Mulher Brasileira, programa Mulheres Mil (IFMS), Prefeitura de Campo Grande",
        "Subsecretaria da Pessoa com Deficiência de MS, APAEs, associações de surdos e de cegos, Napne do IFMS",
        "programas de juventude do Governo de MS e da Prefeitura de Campo Grande, universidades abertas à terceira idade (UFMS, UEMS)",
        "Prefeitura de Campo Grande (Funsat, Secretaria da Mulher)", "campogrande.ms.gov.br",
        [("ms.gov.br", "", False), ("ifms.edu.br", EP, True), ("ufms.br", "", False), ("uems.br", "", False), ("ufgd.edu.br", "", False),
         ("senac.br", "", False), ("senai.br", "", False), ("fiems.com.br", "SENAI MS", False), ("sebrae.com.br", "", False),
         ("www.gov.br", "", False), ("sed.ms.gov.br", EP, True), ("campograndenews.com.br", J, False), ("correiodoestado.com.br", J, False), ("g1.globo.com", J, False)]),
 "SP": ("São Paulo", "em São Paulo", "São Paulo (capital), Guarulhos, Campinas, São Bernardo do Campo, Santo André, Osasco, Sorocaba, Ribeirão Preto, São José dos Campos, Santos, Mauá, Diadema, Carapicuíba, Piracicaba, Bauru, São José do Rio Preto e interior",
        "Programa Senac de Gratuidade em São Paulo, cursos gratuitos do SENAI-SP, cursos FIC e técnicos por sorteio do IFSP (todos os campi), Qualifica SP e Fundo Social de São Paulo, cursos livres do Centro Paula Souza, Fundação Paulistana e Cate da Prefeitura de São Paulo, programas de outras prefeituras (Campinas, Guarulhos, ABC), extensão da USP, Unesp, Unicamp, UFABC, Unifesp e UFSCar, EJA",
        "g1 SP, Agência SP, Estadão, Folha de S.Paulo", "Secretaria da Mulher do Estado de SP, Secretaria Municipal de Direitos Humanos e Cidadania de SP, Casas da Mulher, programa Mulheres Mil (IFSP), Centros de Cidadania LGBTI",
        "Secretaria dos Direitos da Pessoa com Deficiência de SP, APAEs, Fundação Dorina Nowill, Derdic, associações de surdos, Napne do IFSP",
        "programas de juventude do Governo de SP e da Prefeitura de São Paulo (Fábricas de Cultura, CEUs), universidades abertas à terceira idade (USP 60+, Unesp)",
        "Prefeitura de São Paulo (Fundação Paulistana, Cate, Secretaria de Desenvolvimento Econômico e Trabalho, Teias, CEUs)", "capital.sp.gov.br",
        [("sp.gov.br", "", False), ("ifsp.edu.br", EP + "; o IFSP cobra taxa de inscrição em alguns editais: vale a página (regra E12)", True),
         ("cps.sp.gov.br", "Etecs têm prova e taxa (fora); cursos livres MOOC lidos por moodle_abertos.py", False),
         ("usp.br", "", False), ("unesp.br", "", False), ("unicamp.br", "", False), ("ufabc.edu.br", "", False), ("unifesp.br", "", False),
         ("ufscar.br", "", False), ("senac.br", "", False), ("senai.br", "", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False),
         ("educacao.sp.gov.br", EP, True), ("prefeitura.sp.gov.br", "", False), ("estadao.com.br", J, False), ("folha.uol.com.br", J, False), ("g1.globo.com", J, False)]),
 "RJ": ("Rio de Janeiro", "no Rio de Janeiro", "Rio de Janeiro (capital), São Gonçalo, Duque de Caxias, Nova Iguaçu, Niterói, Belford Roxo, Campos dos Goytacazes, São João de Meriti, Petrópolis, Volta Redonda, Macaé, Magé, Itaboraí, Cabo Frio e interior",
        "Programa Senac de Gratuidade no RJ, editais gratuitos do SENAI Firjan, cursos FIC do IFRJ, do IFF, do CEFET/RJ e do Colégio Pedro II, cursos da Faetec, cursos da Secretaria de Trabalho e Renda, programas da Prefeitura do Rio e de outras prefeituras, extensão da UFRJ, UFF, UERJ, UNIRIO e UFRRJ, EJA",
        "O Dia, Extra, g1 Rio", "Secretaria da Mulher do RJ e da Prefeitura do Rio, programa Mulheres Mil (IFRJ, IFF), Rio sem LGBTIfobia",
        "Secretaria da Pessoa com Deficiência do RJ e da Prefeitura do Rio, Instituto Benjamin Constant, INES, APAEs, Napne do IFRJ e do IFF",
        "programas de juventude do Governo do RJ e da Prefeitura do Rio, universidade aberta à terceira idade (UnATI/UERJ), Casas de Convivência",
        "Prefeitura do Rio (Secretaria de Trabalho e Renda, Naves do Conhecimento, Secretaria da Mulher)", "prefeitura.rio",
        [("rj.gov.br", "", False), ("ifrj.edu.br", EP, True), ("iff.edu.br", EP, True), ("cefet-rj.br", "", False), ("cp2.g12.br", "", False),
         ("ufrj.br", "", False), ("uff.br", "", False), ("uerj.br", "", False), ("unirio.br", "", False), ("ufrrj.br", "", False),
         ("senac.br", "", False), ("firjan.com.br", "SENAI Firjan", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False),
         ("seeduc.rj.gov.br", EP, True), ("prefeitura.rio", "", False), ("odia.ig.com.br", J, False), ("extra.globo.com", J, False), ("g1.globo.com", J, False)]),
 "MG": ("Minas Gerais", "em Minas Gerais", "Belo Horizonte, Uberlândia, Contagem, Juiz de Fora, Betim, Montes Claros, Ribeirão das Neves, Uberaba, Governador Valadares, Ipatinga, Sete Lagoas, Divinópolis, Santa Luzia, Poços de Caldas, Teófilo Otoni e interior",
        "Programa Senac de Gratuidade em MG, Gratuidade Regimental do SENAI MG (Fiemg), cursos FIC e técnicos sem prova do IFMG, IFNMG, IF Sudeste MG, IFSULDEMINAS, IFTM e CEFET-MG, Trilhas de Futuro e cursos da Sedese, Minas Forma, programas da Prefeitura de Belo Horizonte e de outras prefeituras, extensão da UFMG, UFU, UFJF, UFOP, UFV, UEMG e Unimontes, EJA",
        "Estado de Minas, O Tempo, g1 Minas, Agência Minas", "Subsecretaria de Políticas para as Mulheres de MG, programa Mulheres Mil (institutos federais de MG), Prefeitura de Belo Horizonte, Centro de Referência LGBT",
        "Coordenadoria da Pessoa com Deficiência de MG, APAEs, Instituto São Rafael, associações de surdos, Napne dos institutos federais de MG",
        "programas de juventude do Governo de MG e da Prefeitura de BH, universidades abertas à terceira idade (UFMG, UFU, UFJF)",
        "Prefeitura de Belo Horizonte (Secretaria de Desenvolvimento Econômico, Sine BH, Centro de Formação e Qualificação)", "pbh.gov.br",
        [("mg.gov.br", "", False), ("ifmg.edu.br", EP, True), ("ifnmg.edu.br", EP, True), ("ifsudestemg.edu.br", EP, True),
         ("ifsuldeminas.edu.br", EP, True), ("iftm.edu.br", EP, True), ("cefetmg.br", "", False), ("ufmg.br", "", False), ("ufu.br", "", False),
         ("ufjf.br", "", False), ("ufop.br", "", False), ("ufv.br", "", False), ("uemg.br", "", False), ("unimontes.br", "", False),
         ("senac.br", "", False), ("fiemg.com.br", "SENAI MG", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False),
         ("educacao.mg.gov.br", EP, True), ("pbh.gov.br", "", False), ("em.com.br", J, False), ("otempo.com.br", J, False), ("g1.globo.com", J, False)]),
 "ES": ("Espírito Santo", "no Espírito Santo", "Vitória, Vila Velha, Serra, Cariacica, Cachoeiro de Itapemirim, Linhares, São Mateus, Colatina, Guarapari, Aracruz e interior",
        "Programa Senac de Gratuidade no ES, Gratuidade Regimental do SENAI ES (Findes), cursos FIC do IFES (todos os campi), Qualificar ES e cursos da Secretaria de Ciência e Tecnologia (Sectides), programas da Prefeitura de Vitória e de outras prefeituras, extensão da UFES, EJA",
        "A Gazeta, Folha Vitória, g1 ES", "Secretaria das Mulheres do ES, programa Mulheres Mil (IFES), Prefeitura de Vitória",
        "Secretaria de Direitos Humanos do ES, APAEs, associações de surdos e de cegos, Napne do IFES",
        "programas de juventude do Governo do ES e da Prefeitura de Vitória, universidade aberta à terceira idade (UFES)",
        "Prefeitura de Vitória (Secretaria de Trabalho, Sine Vitória, Centro de Qualificação)", "vitoria.es.gov.br",
        [("es.gov.br", "", False), ("ifes.edu.br", EP, True), ("ufes.br", "", False), ("senac.br", "", False), ("senaies.com.br", "SENAI ES", False),
         ("findes.com.br", "", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False), ("sedu.es.gov.br", EP, True),
         ("agazeta.com.br", J, False), ("folhavitoria.com.br", J, False), ("g1.globo.com", J, False)]),
 "PR": ("Paraná", "no Paraná", "Curitiba, Londrina, Maringá, Ponta Grossa, Cascavel, São José dos Pinhais, Foz do Iguaçu, Colombo, Guarapuava, Paranaguá, Araucária, Toledo, Apucarana e interior",
        "Programa Senac de Gratuidade no Paraná, Gratuidade Regimental do SENAI PR (Sistema Fiep), cursos FIC do IFPR e da UTFPR, cursos da Secretaria do Trabalho (Agências do Trabalhador) e da Secretaria de Desenvolvimento Social, Liceu de Ofícios e FAS da Prefeitura de Curitiba, programas de outras prefeituras, extensão da UFPR, UEL, UEM, UEPG, Unioeste e Unicentro, EJA",
        "Gazeta do Povo, Banda B, g1 PR, Agência Estadual de Notícias", "Secretaria da Mulher do Paraná, programa Mulheres Mil (IFPR), Prefeitura de Curitiba",
        "Departamento da Pessoa com Deficiência do Paraná, APAEs, Instituto Paranaense de Cegos, associações de surdos, Napne do IFPR",
        "programas de juventude do Governo do Paraná e da Prefeitura de Curitiba, universidades abertas à terceira idade (UFPR, UEL, UEM)",
        "Prefeitura de Curitiba (Liceu de Ofícios, FAS, Agência Curitiba)", "curitiba.pr.gov.br",
        [("pr.gov.br", "", False), ("ifpr.edu.br", EP, True), ("utfpr.edu.br", "", False), ("ufpr.br", "", False), ("uel.br", "", False),
         ("uem.br", "", False), ("uepg.br", "", False), ("unioeste.br", "", False), ("unicentro.br", "", False), ("senac.br", "", False),
         ("senaipr.org.br", "SENAI PR", False), ("sistemafiep.org.br", "", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False),
         ("educacao.pr.gov.br", EP, True), ("gazetadopovo.com.br", J, False), ("bandab.com.br", J, False), ("g1.globo.com", J, False)]),
 "SC": ("Santa Catarina", "em Santa Catarina", "Joinville, Florianópolis, Blumenau, São José, Itajaí, Chapecó, Palhoça, Criciúma, Jaraguá do Sul, Lages, Balneário Camboriú, Brusque, Tubarão e interior",
        "Programa Senac de Gratuidade em SC, Gratuidade Regimental do SENAI SC (Fiesc), EJA profissionalizante do SESI SC (SEJA PRO+), cursos FIC do IFSC e do IFC (todos os campi), cursos da Secretaria de Assistência Social, Mulher e Família, programas da Prefeitura de Florianópolis, de Joinville e de outras prefeituras, extensão da UFSC, Udesc e UFFS, EJA",
        "NSC Total, ND+, g1 SC, Agência de Notícias SECOM SC", "Secretaria da Mulher e Família de SC, programa Mulheres Mil (IFSC, IFC), Prefeitura de Florianópolis",
        "Fundação Catarinense de Educação Especial (FCEE), APAEs, Associação Catarinense para Integração do Cego, associações de surdos, Napne do IFSC e do IFC",
        "programas de juventude do Governo de SC e das prefeituras, universidades abertas à terceira idade (UFSC NETI, Udesc)",
        "Prefeitura de Florianópolis (Secretaria de Assistência Social, Sine Florianópolis)", "pmf.sc.gov.br",
        [("sc.gov.br", "", False), ("ifsc.edu.br", EP, True), ("ifc.edu.br", EP, True), ("ufsc.br", "", False), ("udesc.br", "", False),
         ("uffs.edu.br", "", False), ("senac.br", "", False), ("senai.br", "", False), ("fiesc.com.br", "", False),
         ("sesisc.org.br", "SESI SC (EJA)", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False), ("sed.sc.gov.br", EP, True),
         ("nsctotal.com.br", J, False), ("ndmais.com.br", J, False), ("g1.globo.com", J, False)]),
 "RS": ("Rio Grande do Sul", "no Rio Grande do Sul", "Porto Alegre, Caxias do Sul, Canoas, Pelotas, Santa Maria, Gravataí, Viamão, Novo Hamburgo, São Leopoldo, Rio Grande, Alvorada, Passo Fundo, Sapucaia do Sul, Uruguaiana e interior",
        "Programa Senac de Gratuidade no RS, Gratuidade Regimental do SENAI RS (Fiergs), cursos FIC do IFRS, do IFSul e do IF Farroupilha (todos os campi), cursos da Fundação Gaúcha do Trabalho (FGTAS, Sine) e da Secretaria de Desenvolvimento Social, programas da Prefeitura de Porto Alegre e de outras prefeituras, extensão da UFRGS, UFSM, UFPel, FURG, Unipampa e Uergs, EJA",
        "GZH, Correio do Povo, g1 RS, Secom RS", "Secretaria da Mulher do RS, programa Mulheres Mil (IFRS, IFSul, IF Farroupilha), Prefeitura de Porto Alegre",
        "Faders (Acessibilidade e Inclusão), APAEs, associações de surdos e de cegos, Napne dos institutos federais do RS",
        "programas de juventude do Governo do RS e da Prefeitura de Porto Alegre, universidades abertas à terceira idade (UFRGS, UFSM, PUCRS)",
        "Prefeitura de Porto Alegre (Secretaria de Desenvolvimento Econômico, Sine Municipal, Fasc)", "prefeitura.poa.br",
        [("rs.gov.br", "", False), ("ifrs.edu.br", EP, True), ("ifsul.edu.br", EP, True), ("iffarroupilha.edu.br", EP, True),
         ("ufrgs.br", "", False), ("ufsm.br", "", False), ("ufpel.edu.br", "", False), ("furg.br", "", False), ("unipampa.edu.br", "", False),
         ("uergs.edu.br", "", False), ("senacrs.com.br", "Senac RS", False), ("senac.br", "", False), ("senairs.org.br", "SENAI RS", False),
         ("fiergs.org.br", "", False), ("sebrae.com.br", "", False), ("www.gov.br", "", False), ("educacao.rs.gov.br", EP, True),
         ("prefeitura.poa.br", "", False), ("gauchazh.clicrbs.com.br", J, False), ("correiodopovo.com.br", J, False), ("g1.globo.com", J, False)]),
}


def pesquisas(uf, d):
    nome, em, cidades, fontes, jornais, mulheres, pcd, idades, capital, dom_capital, _sites = d
    x = uf.lower()
    return [
        (f"br-{x}", f"cursos gratuitos presenciais com inscrições abertas {em} ({cidades}): {fontes}. Cursos só para alunos da rede pública podem entrar; não incluir cursos só para servidores ou funcionários, nem cursos com prova, vestibular ou nota do ENEM", ""),
        (f"{x}-noticias", f"notícias recentes sobre cursos gratuitos com inscrições abertas {em} ({jornais}): Senac, SENAI, institutos federais, Governo do estado e prefeituras; sempre que possível, usar o link oficial da inscrição em vez do link da notícia", "Fonte de descoberta: cursos com link de notícia entram em Rever"),
        (f"{x}-publicos-prioritarios", f"cursos gratuitos com inscrições abertas {em} feitos para mulheres, pessoas LGBTQIA+, população negra, quilombolas ou indígenas, ou com vagas reservadas para esses grupos: {mulheres}, Senac e SENAI", "Públicos prioritários: só marca o perfil quando a página diz para quem é o curso"),
        (f"{x}-pcd", f"cursos gratuitos com inscrições abertas {em} feitos para pessoas com deficiência (PcD), com vagas reservadas para elas, ou com acessibilidade declarada (intérprete de Libras, local acessível, material em braile, audiodescrição): {pcd}, Senac e SENAI, cursos de Libras", "Pessoas com deficiência: só marca o perfil quando a página diz para quem é o curso; acessibilidade só com a frase da página"),
        (f"{x}-idades", f"cursos gratuitos com inscrições abertas {em} só para jovens (ex.: 15 a 29 anos) ou só para pessoas com 60 anos ou mais, com inscrição direta da própria pessoa: {idades}, cursos para pessoas idosas do CRAS, do Sesc e das prefeituras, inclusão digital para pessoas idosas. Não incluir vagas de Jovem Aprendiz (são empregos, não cursos)", "Faixas de idade: só com a idade escrita na página"),
        (f"{x}-igrejas-ongs", f"cursos de formação profissional gratuitos com inscrições abertas {em} oferecidos por igrejas, paróquias, congregações, pastorais, Cáritas, centros espíritas, institutos e ONGs, abertos a qualquer pessoa", "Igrejas e ONGs (23/11/2026): só entram se forem gratuitos e abertos a todos, sem exigir ser membro nem atividade religiosa; a instituição tem de ter histórico robusto (critérios de 25/11/2026)"),
        (f"{x}-prefeitura-capital", f"cursos de qualificação profissional gratuitos e presenciais com inscrições abertas oferecidos pela {capital}, com a notícia oficial em {dom_capital} e o prazo de inscrição escrito", "Prefeituras das capitais (23/11/2026): só com a página oficial da prefeitura e frase de que o curso é gratuito"),
    ]


def main():
    b = Base()
    ps_exist = {r.get("ID") for r in b.tabela("Pesquisas de cursos")}
    ss_exist = {(r.get("Local"), r.get("Domínio")) for r in b.tabela("Sites de confiança")}
    ps, ss = [], []
    for uf, d in E.items():
        local = "BR-" + uf
        for pid, texto, notas in pesquisas(uf, d):
            if pid not in ps_exist:
                ps.append({"Ativa": "TRUE", "ID": pid, "Local": local, "O que procurar": texto, "Notas": notas})
        for dom, notas, tudo in d[-1]:
            if (local, dom) not in ss_exist:
                ss.append({"Ativo": "TRUE", "Local": local, "Domínio": dom, "Notas": notas, "Tudo gratuito": "TRUE" if tudo else "FALSE",
                           "Inscrição aberta quando a página mostra": "FALSE"})
    b.acrescentar("Pesquisas de cursos", ps)
    b.acrescentar("Sites de confiança", ss)
    b.guardar()
    print(f"Pesquisas novas: {len(ps)}; sites novos: {len(ss)} ({sum(s['Tudo gratuito'] == 'TRUE' for s in ss)} «Tudo gratuito»).")
    for uf in E:
        print(uf, sum(p["Local"] == "BR-" + uf for p in ps), "pesquisas,", sum(s["Local"] == "BR-" + uf for s in ss), "sites")


if __name__ == "__main__":
    main()
