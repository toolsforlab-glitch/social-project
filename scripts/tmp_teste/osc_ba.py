import re, html, json, time, subprocess, collections, urllib.request, urllib.parse, zipfile, io, csv, datetime
UA={"User-Agent":"Mozilla/5.0"}
def get(u,t=60):
    return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t).read()
pag=get("https://www.ba.gov.br/trabalho/292/termo-de-colaboracao").decode("utf-8","replace")
links=re.findall(r'href="([^"]+\.pdf)"[^>]*>(.*?)</a>',pag,re.S)
docs=[]
for u,t in links:
    t=html.unescape(re.sub(r"<[^>]+>","",t)).strip()
    if re.search(r"aditivo",t,re.I) or not re.search(r"(colabora|fomento)",t,re.I): continue
    m=re.search(r"(20\d\d)",t)
    docs.append((urllib.parse.urljoin("https://www.ba.gov.br",u),t,m.group(1) if m else "?"))
print("termos (sem aditivos):",len(docs))
por=collections.defaultdict(lambda:{"nomes":set(),"anos":set(),"termos":[]})
for u,t,ano in docs:
    try:
        open("/tmp/d.pdf","wb").write(get(u))
        txt=subprocess.run(["pdftotext","-l","3","/tmp/d.pdf","-"],capture_output=True,text=True).stdout
    except Exception as e:
        print("ERRO",t,e); continue
    cn=re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",txt)
    cn=[c for c in cn if not c.startswith("13.937.123")]   # CNPJ da SETRE
    if not cn: print("SEM CNPJ:",t[:90]); continue
    c=collections.Counter(cn).most_common(1)[0][0]
    por[c]["nomes"].add(re.sub(r".*?[-–]\s*","",t,1)[:80]); por[c]["anos"].add(ano); por[c]["termos"].append(t[:60])
json.dump({k:{"nomes":sorted(v["nomes"]),"anos":sorted(v["anos"]),"n":len(v["termos"])} for k,v in por.items()},open("/tmp/por.json","w"),ensure_ascii=False)
# CEPIM / CEIS / CNEP (Portal da Transparência)
imped={}
for base in ["cepim","ceis","cnep"]:
    ok=False
    for d in range(0,15):
        dia=(datetime.date.today()-datetime.timedelta(days=d)).strftime("%Y%m%d")
        try:
            z=zipfile.ZipFile(io.BytesIO(get(f"https://portaldatransparencia.gov.br/download-de-dados/{base}/{dia}",120)))
            txt=z.read(z.namelist()[0]).decode("latin-1")
            imped[base]=set(re.sub(r"\D","",x) for x in re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}",txt))
            print(base,dia,"linhas:",txt.count("\n")); ok=True; break
        except Exception as e: last=e
    if not ok: print(base,"FALHOU",last)
print()
print("CNPJ | abertura | situação | anos de parceria (n termos) | impedida? | nome")
for c,v in sorted(por.items(),key=lambda kv:-len(kv[1]["anos"])):
    n=re.sub(r"\D","",c)
    try:
        j=json.loads(get(f"https://brasilapi.com.br/api/cnpj/v1/{n}",30)); ab=j.get("data_inicio_atividade"); si=j.get("descricao_situacao_cadastral"); rs=j.get("razao_social","")
    except Exception as e: ab=si="?"; rs=""
    imp=",".join(b for b,s in imped.items() if n in s) or "-"
    print(f"{c} | {ab} | {si} | {','.join(sorted(v['anos']))} ({len(v['termos'])}) | {imp} | {rs or sorted(v['nomes'])[0]}")
    time.sleep(0.6)
