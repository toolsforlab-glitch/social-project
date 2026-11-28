import os, sys, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
import senac_sc as m
for k in range(3):
    b = baixar("https://portal.sc.senac.br/curso/136973/psg/assistente-de-recursos-humanos", timeout=60).decode("utf-8", "replace")
    print(k, len(b), "h1" , "<h1" in b, "Turmas Dispon" in b, b.count("Turma 20"), "| ", re.sub(r"\s+", " ", m.limpo(b))[-1500:-900])
    i = b.lower().find("turma"); print("   ctx:", re.sub(r"\s+", " ", b[i-300:i+300]))
    time.sleep(5)
