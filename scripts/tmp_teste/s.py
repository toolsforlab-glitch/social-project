import os, sys, re, urllib.request
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=60); return r.read().decode("utf-8", "replace"), r.geturl()
for u in ["https://portal.sc.senac.br/psg/", "https://www.sc.senac.br/psg/"]:
    b, f = get(u)
    print("=====", u, f, len(b))
    print(re.sub(r"\s+", " ", re.sub(r"<style.*?</style>", "", b, flags=re.S))[:3000])
    print(sorted(set(re.findall(r'(?:src|href)=["\']([^"\']+)', b)))[:80])
    for js in re.findall(r'src=["\']([^"\']+\.js[^"\']*)', b)[:15]:
        url = js if js.startswith("http") else re.sub(r"/[^/]*$", "/", f) + js.lstrip("./") if not js.startswith("/") else re.match(r"https?://[^/]+", f).group(0) + js
        try:
            j, _ = get(url)
            apis = sorted(set(re.findall(r'["\'`](https?://[^"\'`\s]{8,200}|/api/[^"\'`\s]{2,120}|api/[^"\'`\s]{2,120})["\'`]', j)))
            print("JS", url, len(j), apis[:60])
        except Exception as e:
            print("JS", url, "erro", e)
