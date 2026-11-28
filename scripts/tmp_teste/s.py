import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re, urllib.request, urllib.parse, http.cookiejar, html, json
from comum import AGENTE
U="https://psg.rj.senac.br/Ext/Vagas.aspx"
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
def get(data=None):
    req=urllib.request.Request(U,data=data,headers={"User-Agent":AGENTE,"Content-Type":"application/x-www-form-urlencoded"} if data else {"User-Agent":AGENTE})
    return op.open(req,timeout=40).read().decode("utf-8","replace")
def campos(h):
    d={}
    for m in re.finditer(r'<input[^>]+>',h):
        t=m.group(0); n=re.search(r'name="([^"]+)"',t); v=re.search(r'value="([^"]*)"',t)
        if n and 'type="hidden"' in t: d[html.unescape(n.group(1))]=html.unescape(v.group(1) if v else "")
    return d
try:
    h=get(); print("GET ok", len(h), h.count("btnCalendario")); print(h[:3000])
    alvos=re.findall(r"__doPostBack\(&#39;(grdPesquisa\$ctl\d+\$btnCalendario)&#39;",h) or re.findall(r"__doPostBack\('(grdPesquisa\$ctl\d+\$btnCalendario)'",h)
    print("alvos",len(alvos), alvos[:2])
    d=campos(h); d["__EVENTTARGET"]=alvos[0]; d["__EVENTARGUMENT"]=""
    h2=get(urllib.parse.urlencode(d).encode()); t=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",h2))
    i=t.find("Início da Turma"); print("POST ok", len(h2), t[i-200:i+500])
except Exception as e: print("ERRO", repr(e))
