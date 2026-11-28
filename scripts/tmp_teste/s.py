import os, sys, json, re, html, urllib.request
os.makedirs("../sonda", exist_ok=True)
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=120); return r.read().decode("utf-8", "replace"), r.geturl()
t, _ = get("https://www.senacrs.com.br/hotsite/psg/partials/vagas-filter.php")
out = []
i = t.find("Lei Lucas")
out.append("RAW: " + t[i-3000:i+4500])
for alvo in re.findall(r'data-bs-target="#([^"]+)"', t[i-3000:i+4500]):
    j = t.find(f'id="{alvo}"'); out.append(f"--- modal {alvo}: " + re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t[j:j+5000])))[:3000])
for u in ["https://apsweb.senacrs.com.br/modulos/vestibular", "https://apsweb.senacrs.com.br/modulos/vestibular/"]:
    try:
        b, fim = get(u); out.append(f"=== {u} -> {fim} {len(b)}\n" + b[:6000])
    except Exception as e:
        out.append(f"=== {u} erro {e}")
open("../sonda/rs.txt", "w").write("\n".join(out))
json.dump([{"ok": len(t)}], open("../sonda/resumo.json", "w"))
