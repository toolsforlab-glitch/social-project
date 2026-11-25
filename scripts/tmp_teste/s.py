import sys, re
sys.path.insert(0, "scripts")
from comum import baixar
from base import texto_de_html
t = texto_de_html(baixar("https://www.ifap.edu.br/documents/1317/Edital_PROEJA_2027.pdf", timeout=90))
print(len(t))
for pat in [r".{0,200}in[íi]cio (das aulas|do semestre|do per[íi]odo letivo|das atividades).{0,200}", r".{0,150}semestre letivo.{0,200}", r".{0,150}calend[áa]rio acad[êe]mico.{0,200}", r".{0,120}matr[íi]cula.{0,120}\d{2}/\d{2}.{0,80}", r".{0,100}ingresso.{0,150}"]:
    for m in list(re.finditer(pat, t, re.I))[:4]: print(pat[:16], "→", m.group(0))
