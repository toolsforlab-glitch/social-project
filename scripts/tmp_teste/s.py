import os, sys, json, re, html, datetime, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs("../sonda", exist_ok=True)
U = "https://www.senacrs.com.br/hotsite/psg/partials/vagas-filter.php"
req = urllib.request.Request(U, headers={"User-Agent": "Mozilla/5.0"})
t = urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "replace")
out = []
cards = re.split(r'<div class="card box ', t)
out.append(f"cards: {len(cards)-1}")
for c in cards[1:]:
    c = c[:8000]
    m = re.search(r"Inscri[çc][õo]es:\s*(\d\d/\d\d/\d{4})\s*a\s*(\d\d/\d\d/\d{2,4})", c)
    out.append("=== " + c[:200].replace("\n", " "))
    if m and m.group(2)[-4:] >= "2026":
        out.append(c[:4000])
        for alvo in re.findall(r'data-bs-target="#([^"]+)"', c):
            i = t.find(f'id="{alvo}"')
            out.append(f"--- modal {alvo}: " + (re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t[i:i+5000]))) if i >= 0 else "não achado")[:2500])
i = t.find('id="exampleModal"'); out.append("--- exampleModal: " + t[i:i+4000])
i = t.find("abertas"); 
for m in re.finditer(r"abertas", t[:300000]): out.append("ABERTAS ctx: " + t[max(0, m.start()-200):m.start()+100].replace("\n", " "))
open("../sonda/rs.txt", "w").write("\n".join(out))
json.dump([{"ok": len(t)}], open("../sonda/resumo.json", "w"))
