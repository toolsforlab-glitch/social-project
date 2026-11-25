import sys, re
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html, citacao_valida
u = "https://escolapublica.ap.gov.br/govap/pre-matricula-jovens-e-adultos"
t = texto_de_html(baixar(u, timeout=60))
print(len(t)); i = t.find("pré"); print(t[:200])
m = re.search(r"(?s).{0,1500}05/01/2027.{0,2500}", t); print(m.group(0) if m else t[:4000])
for f in ["05/01/2027 a 21/01/2027", "Para realizar a inscrição na pré matricula, clique na aba “Inscrição” da página https://www.escolapublica.ap.gov.br/portal_matricula.", "Documentação aluno (maior de idade) CPF RG Certidão de Nascimento Carteira do SUS E-mail de contato Endereço residencial"]:
    print(citacao_valida(f, t), f[:60])
