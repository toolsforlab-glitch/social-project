import re, sys, io
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
from pypdf import PdfReader
b = baixar("https://www.agenciabrasilia.df.gov.br/documents/d/guest/26-11-edital-sedet-1-pdf", timeout=30)
print("bytes", len(b), b[:5])
t = re.sub(r"\s+", " ", "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(b)).pages))
print(len(t)); print(t[:7000])
for p in [r"gratuit", r"sele[çc][ãa]o|classifica|sorteio|ordem", r"inscri[çc][õo]es"]:
    for m in list(re.finditer(p, t, re.I))[:4]: print(f"[{p[:12]}] …{t[max(0,m.start()-250):m.end()+300]}")
