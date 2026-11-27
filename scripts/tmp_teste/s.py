import sys, os, time
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, ".")
from comum import baixar
os.makedirs("../sonda", exist_ok=True)
A = "https://www.ifb.edu.br/attachments/article/"
U = [A+"49010/Edital%2037-2026-Sele%C3%A7%C3%A3o%20EJA-EPT-2027.pdf",
     A+"49010/Retifica%C3%A7%C3%A3o%20Anexo%20A%20Edital%2037%20campus%20gama.pdf",
     A+"49023/Edital%20%C3%9Anico%20para%20Ingresso%20de%20Discentes%20nos%20Cursos%20T%C3%A9cnicos%20de%20EJA-EPT%20do%20IFB%20-%20Sele%C3%A7%C3%A3o%202027%20-%20Taguatinga.pdf",
     A+"49023/Anexo%20A%20Cronograma%20do%20Edital%20%C3%9Anico%20para%20Ingresso%20de%20Discentes%20nos%20Cursos%20T%C3%A9cnicos%20de%20EJA-EPT%20do%20IFB%20-%20Sele%C3%A7%C3%A3o%20%C3%9Anica%20-%20Taguatinga%20(Retificado%20II).pdf",
     A+"49122/Edital%2026_2026%20-%20DGSA_RIFB_IFBRASILIA%20%20-Processo%20Seletivo%20para%20PROEJA%20em%20Edifica%C3%A7%C3%B5es%20CSAM.pdf",
     A+"49096/Edital%2044.2026%20-%20EJA%20EPT%20T%C3%A9cnico%20em%20Marketing.pdf",
     A+"49052/EDITAL_45_EJA.pdf",
     A+"49019/Edital%2013_2026%20-%20DGSS_RIFB_IFBRASILIA.pdf",
     A+"49081/Edital%2011-2026%20-%20DGES-RIFB-IFBRASILIA.pdf"]
for i, u in enumerate(U):
    try:
        d = baixar(u, timeout=40)
        ok = d[:5] == b"%PDF-"
        open(f"../sonda/e{i}.pdf" if ok else f"../sonda/e{i}.html", "wb").write(d); print("OK" if ok else "NAO-PDF", i, len(d), u[-60:])
    except Exception as e:
        print("ERRO", i, type(e).__name__, str(e)[:100])
    time.sleep(12)
