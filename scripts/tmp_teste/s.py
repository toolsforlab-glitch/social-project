import sys, os, io; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
from pypdf import PdfReader
u="https://www.fumec.sp.gov.br//sites/www.fumec.sp.gov.br/files/1.edital_tecnico_1o_sem_2027.docx.pdf"
os.makedirs("../sonda",exist_ok=True)
try:
    b=baixar(u,timeout=90); r=PdfReader(io.BytesIO(b)); t="\n".join((p.extract_text() or "") for p in r.pages)
    open("../sonda/ceprocamp.txt","w").write(t); print("ok",len(b),len(r.pages),len(t))
except Exception as e: print("ERRO",repr(e))
