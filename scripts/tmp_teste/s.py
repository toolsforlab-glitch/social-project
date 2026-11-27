import re, sys, io
sys.path.insert(0, ".")
from comum import baixar
from pypdf import PdfReader
U = "http://iema.ma.gov.br/wp-content/uploads/2026/"
for n in ["11/SEI_018801690_Edital_77", "11/SEI_018728351_Edital_76", "11/EDITAL-RETIFICACAO-SEI_018608693_Edital_73",
          "11/SEI_018427218_Edital_68", "11/SEI_018443700_Edital_69", "10/SEI_018274917_Edital_65", "10/SEI_018277624_Edital_66",
          "10/SEI_018047759_Edital_62", "10/SEI_017861890_Edital_56", "10/SEI_017867718_Edital_57", "09/SEI_017340084_Edital_20",
          "09/SEI_017343061_Edital_44", "09/SEI_017375511_Edital_46"]:
    try:
        r = PdfReader(io.BytesIO(baixar(U + n + ".pdf", timeout=40)))
        t = re.sub(r"\s+", " ", (r.pages[0].extract_text() or ""))
        t = re.sub(r"GOVERNO DO ESTADO DO MARANH[ÃA]O|INSTITUTO ESTADUAL DE EDUCA[ÇC][ÃA]O, CI[ÊE]NCIA E TECNOLOGIA DO MARANH[ÃA]O", "", t)
        print(f"\n## {n} ({len(r.pages)} p.)\n{t[:700]}")
    except Exception as e:
        print(f"\n## {n} ERRO {type(e).__name__} {str(e)[:80]}")
