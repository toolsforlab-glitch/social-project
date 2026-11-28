import sys, os, io; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
from pypdf import PdfReader
U={"vencer":"https://rondonia.ro.gov.br/wp-content/uploads/2026/07/SEI_74690921_Edital_6.pdf",
   "firjan":"https://www.firjansenai.com.br/sites/default/files/2026-11/OFERTAS%201%20EDITAL%20QP_Gratuidade_REV.0_atual.%2011.11.2026.pdf.pdf"}
os.makedirs("../sonda",exist_ok=True)
for k,u in U.items():
    try:
        b=baixar(u,timeout=90); r=PdfReader(io.BytesIO(b))
        t="\n\n=====PAGINA=====\n".join((p.extract_text() or "") for p in r.pages)
        open(f"../sonda/{k}.txt","w").write(t); print(k,"ok",len(b),len(r.pages),len(t))
    except Exception as e: print(k,"ERRO",repr(e))
