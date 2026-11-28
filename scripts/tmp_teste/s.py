import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
from base import texto_de_html
B = "https://www.senacrs.com.br/hotsite/psg/"
js = baixar(B + "assets/js/appPSG.js", timeout=60).decode("utf-8", "replace")
print(js[:2500])
for p in re.findall(r'templateUrl\s*:\s*["\']([^"\']+)', js):
    try:
        t = texto_de_html(baixar(B + p, timeout=60))
        print("==", p, len(t), "| gratuitas:", "custo zero" in t, "| ordem:", "ordem cronológica" in t)
        if "custo zero" in t or "ordem cronológica" in t:
            i = t.find("custo zero"); print(t[max(0, i-400):i+100]); j = t.find("ordem cronológica"); print(t[max(0, j-200):j+60])
    except Exception as e:
        print("==", p, "erro", e)
