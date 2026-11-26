import sys, re, subprocess, tempfile, urllib.parse
sys.path.insert(0, ".")
from comum import baixar
u="https://www.rn.senai.br/wp-content/uploads/2026/11/"+urllib.parse.quote("EDITAL Cursos Técnicos Gratuidade 2026_2.pdf")
b=baixar(u,timeout=60); f=tempfile.mktemp(suffix=".pdf"); open(f,"wb").write(b)
t=subprocess.run(["pdftotext","-layout",f,"-"],capture_output=True,text=True).stdout
print(len(b), len(t)); print(t[:30000])
