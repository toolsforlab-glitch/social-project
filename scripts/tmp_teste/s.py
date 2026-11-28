import sys, subprocess
sys.path.insert(0, ".")
from comum import baixar
from base import texto_de_html
U = {"qp": "https://www.firjansenai.com.br/sites/default/files/2026-11/OFERTAS%201%20EDITAL%20QP_Gratuidade_REV.0_atual.%2011.11.2026.pdf.pdf",
     "setorial": "https://www.firjansenai.com.br/sites/default/files/2026-11/Edital%20Programa%20Qualifica%C3%A7%C3%A3o%20Setorial%20SENAI-RJ%202026%20Vers%C3%A3o%209.0.pdf"}
try:
    print("pagina", len(texto_de_html(baixar("https://www.firjansenai.com.br/sobre/conheca-a-firjan-senai/editais-gratuitos", timeout=40))))
except Exception as e: print("pagina ERRO", e)
for k, u in U.items():
    try:
        b = baixar(u, timeout=60); open(f"../sonda/{k}.pdf", "wb").write(b)
        t = subprocess.run(["pdftotext", "-layout", f"../sonda/{k}.pdf", "-"], capture_output=True, text=True).stdout
        open(f"../sonda/{k}.txt", "w").write(t); print(k, len(b), len(t))
    except Exception as e: print(k, "ERRO", e)
