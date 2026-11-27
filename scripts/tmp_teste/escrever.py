"""Temporário (27/11/2026): SENAI-SP, cartão geral dos cursos livres gratuitos (como o do Senac SP, decisão do responsável de 27/11).
A lista e as perguntas frequentes abrem no GitHub; as turmas (POST /cursosturmas/) só no navegador."""
import sys, re
sys.path.insert(0, ".")
from base import VERIFICACAO_INICIAL, Base, carregar_config, citacao_valida, texto_de_html
from comum import baixar
from cursos import id_curso
from turmas import hoje_ceara
hoje = hoje_ceara()
FAQ = "https://www.sp.senai.br/perguntas-frequentes"
LISTA = "https://www.sp.senai.br/cursos/cursos-livres/0?gratuito=1"
F = {"gratuito": "o SENAI-SP oferece alguns cursos livres gratuitos",
     "lista": "Você também encontra uma lista de cursos livres gratuitos em nosso site."}
TURMA = ("As matrículas serão realizadas presencialmente na secretaria da escola SENAI em Americana e se encerram ao término das vagas.")
t = texto_de_html(baixar(FAQ, timeout=40))
ok = all(citacao_valida(v, t) for v in F.values())
lista = baixar(LISTA, timeout=40).decode("utf-8", "replace")
total = re.findall(r"\d+ a \d+ de (\d+)", lista)
print("frases:", ok, "cursos na lista:", total[:1])
if ok and total:
    base = Base(); carregar_config(base)
    T = "Cursos livres gratuitos do SENAI-SP (Gratuidade Regimental)"
    ident = id_curso(LISTA, T)
    if ident not in {r.get("ID") for r in base.tabela("Cursos")}:
        ev = [f"{k}: «{v}» ({FAQ}; conferida por código)" for k, v in F.items()]
        ev.append(f"lista: {total[0]} cursos livres com o filtro «Gratuitos» a {hoje} ({LISTA}; contados por código)")
        ev.append(f"vagas (exemplo de turma, curso 5S em Americana, visto no navegador a {hoje}): «{TURMA}»")
        base.acrescentar("Cursos", [{"ID": ident, "Estado": "Publicado", "Título": T, "Entidade": "SENAI São Paulo (Gratuidade Regimental)",
            "Link": LISTA, "Página do curso": LISTA, "Destino do link": "lista", "Local": "BR-SP", "Modalidade": "presencial", "País": "BR",
            "Região": "São Paulo", "Cidade": "Escolas SENAI da capital, da Grande São Paulo e do interior",
            "Descrição": (f"O SENAI-SP tem {total[0]} cursos livres gratuitos (aperfeiçoamento e qualificação), sobretudo presenciais nas "
                          "suas escolas. Em cada curso, «Ver unidades» mostra as escolas e as turmas, com as datas, as vagas e o que é "
                          "preciso para a matrícula."),
            "Origem da descrição": "Resumo", "Necessidades": "profissao", "Perfis": "todos", "Condição de acesso": "",
            "Requisitos": "A idade e a escolaridade mínimas dependem de cada curso (estão na turma)", "Certificado": "desconhecido",
            "Inscrições até": "", "Início": "", "Duração": "", "Link verificado": "SIM", "Primeiro visto": hoje, "Última verificação": hoje,
            "Origem": "página oficial", "Precisa de internet": "Sim",
            "Notas": f"{hoje}: criado à mão pelo Claude (cartão geral, como o do Senac SP; as turmas uma a uma só se leem no navegador).",
            "Como me inscrever": ("1. Abra a lista de cursos livres gratuitos do SENAI-SP e filtre pela sua região ou cidade.\n"
                                  "2. Em cada curso, clique em «Ver unidades» e depois em «Ver turmas» para ver datas, vagas e requisitos.\n"
                                  "3. Siga o que a turma indicar: em muitas, a matrícula é presencial na secretaria da escola, até acabarem as "
                                  "vagas, com RG, CPF, comprovante de escolaridade e de endereço."),
            "Nota da verificação": f"{hoje}: perguntas frequentes e lista lidas por código; uma turma de exemplo vista no navegador.",
            **VERIFICACAO_INICIAL, "Situação das inscrições": "Aberto", "Verificar automaticamente": "FALSE",
            "Evidência": " | ".join(ev)[:1800], "Campos comprovados": "gratuito, vagas", "Mudança a rever": "FALSE",
            "O que falta confirmar": ("As turmas uma a uma não estão no site (o pedido das turmas só funciona no navegador). Os cursos a "
                                      "distância gratuitos (121 a 27/11) ainda não foram verificados quanto a quem se pode inscrever.")}])
        base.guardar(); print("+", ident)
