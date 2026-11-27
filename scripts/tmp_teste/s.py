import re, sys
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from ifro_fic import pdf_do_edital, ler_edital
P = "https://selecao.ifro.edu.br/extensao-jiparana/2102-edital-n-52-2026-selecao-de-estudantes-curso-de-libras-basico-i-2027-1"
url, t, res = pdf_do_edital(P)
print("URL:", url, "resultado:", res, "chars:", len(t))
c, f = ler_edital(t); print("FALTAS:", f); print("CAMPOS:", c)
print(re.sub(r"\s+", " ", t)[:12000])
