import re, sys, io
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
from pypdf import PdfReader
b = baixar("https://rondonia.ro.gov.br/wp-content/uploads/2026/07/SEI_74690921_Edital_6.pdf", timeout=30)
t = re.sub(r"\s+", " ", "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages))
i = t.find("1. DAS DISPOSI"); j = t.find("7. DOS CURSOS")
print(t[i:j][:9000])
k = t.find("7.2."); print("\n--- 7.2 em diante\n", t[k:k+3500])
a = t.find("ANEXO ÚNICO"); print("\n--- ANEXO\n", t[a:a+2500])
for m in re.finditer(r"aux[íi]lio|kit|bolsa", t, re.I):
    print("  AUX…", t[max(0,m.start()-150):m.end()+250])
