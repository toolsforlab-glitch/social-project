import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comum import baixar
b = baixar("https://www.senacrs.com.br/hotsite/psg/index.html", timeout=60).decode("utf-8", "replace")
print(b[:3000])
print(re.findall(r'(?:src|href|templateUrl)\s*[=:]\s*["\']([^"\']+)', b))
