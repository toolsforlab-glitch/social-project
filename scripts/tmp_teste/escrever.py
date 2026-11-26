import json, sys
sys.path.insert(0, ".")
from base import Base
base = Base()
cab = list(base.tabela("Cursos")[0].keys()) if base.tabela("Cursos") else []
H = ["ID","Estado","Título","Entidade","Link","Local","Modalidade","País","Região","Cidade","Descrição","Necessidades","Perfis","Condição de acesso","Requisitos","Certificado","Inscrições até","Início","Duração","Link verificado","Primeiro visto","Última verificação","Origem","Notas","Como me inscrever","Nota da verificação","Situação das inscrições","Verificar automaticamente","Falhas seguidas do link","Impressão da página","Página mudou em","Próxima verificação","Evidência","Campos comprovados","Revisto por pessoa","Mudança a rever","O que falta confirmar","Onde se inscrever","Idade mínima","Escolaridade mínima","Renda máxima","Prioridade CadÚnico","Turno","Precisa de internet","Ajuda de custo ou transporte","Documentos pedidos","Antes de começar","Página do curso","Idade máxima","Destino do link","Origem da descrição","Matrícula (como o edital diz)","Inscrições abrem em"]
ids = {r.get("ID") for r in base.tabela("Cursos")}
novos = [dict(zip(H, r)) for r in json.load(open("tmp_teste/rn_rows.json")) if r[0] not in ids]
print("novos:", [n["ID"] for n in novos])
base.acrescentar("Cursos", novos)
base.guardar()
