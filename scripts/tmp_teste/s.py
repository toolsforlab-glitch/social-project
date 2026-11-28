import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
p = baixar("https://www.senacrs.com.br/hotsite/psg/partials/vagas-filter.php", timeout=180).decode("utf-8", "replace")
for m in re.finditer("Gestão Financeira", p):
    print("=====", m.start()); print(p[m.start()-1500:m.start()+1200])
