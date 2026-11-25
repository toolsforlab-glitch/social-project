import re, html, json, time, subprocess, collections, urllib.request, urllib.parse, zipfile, io, datetime
UA={"User-Agent":"Mozilla/5.0"}
def get(u,t=60): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t).read()
pag=get("https://www.ba.gov.br/trabalho/292/termo-de-colaboracao").decode("utf-8","replace")
hrefs=sorted(set(re.findall(r'href="([^"]+\.pdf)"',pag,re.I)))
docs=[]
for u in hrefs:
    nome=urllib.parse.unquote(u.rsplit("/",1)[-1])
    if re.search(r"aditivo|relat|apostil",nome,re.I) or not re.search(r"termo\s*de\s*(colabora|fomento)",nome,re.I): continue
    m=re.search(r"(?:n[º°.o]*\s*|/)\s*0*\d{1,3}[_/ ]?(20[12]\d)",nome,re.I) or re.search(r"(20[12]\d)",nome)
    docs.append((urllib.parse.urljoin("https://www.ba.gov.br",u),nome,m.group(1) if m else "?"))
print("PDFs:",len(hrefs),"termos (sem aditivos):",len(docs))
cache={}
def receita(n):
    if n not in cache:
        try: cache[n]=json.loads(get(f"https://brasilapi.com.br/api/cnpj/v1/{n}",30))
        except Exception: cache[n]={}
        time.sleep(0.4)
    return cache[n]
OSC={"3999","3069","3220","2143","3301","3204"}   # associação, fundação privada, org. religiosa, cooperativa, OS, ...
por=collections.defaultdict(lambda:{"anos":set(),"n":0})
for u,nome,ano in docs:
    try:
        open("/tmp/d.pdf","wb").write(get(u))
        txt=subprocess.run(["pdftotext","-l","3","/tmp/d.pdf","-"],capture_output=True,text=True).stdout
    except Exception as e: print("ERRO",nome[:80],e); continue
    achou=None
    for c,_ in collections.Counter(re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",txt)).most_common():
        j=receita(re.sub(r"\D","",c))
        if str(j.get("codigo_natureza_juridica","")) in OSC: achou=c; break
    if not achou: print("SEM OSC:",nome[:90]); continue
    por[achou]["anos"].add(ano); por[achou]["n"]+=1
imped={}
for base in ["cepim","ceis","cnep"]:
    for d in range(15):
        dia=(datetime.date.today()-datetime.timedelta(days=d)).strftime("%Y%m%d")
        try:
            z=zipfile.ZipFile(io.BytesIO(get(f"https://portaldatransparencia.gov.br/download-de-dados/{base}/{dia}",120)))
            imped[base]=set(re.sub(r"\D","",x) for x in re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}",z.read(z.namelist()[0]).decode("latin-1"))); break
        except Exception: pass
print("bases de impedidas lidas:",list(imped))
print("\nanos_distintos | abertura | situação | anos (termos) | impedida | razão social")
for c,v in sorted(por.items(),key=lambda kv:(-len(kv[1]["anos"]),kv[0])):
    n=re.sub(r"\D","",c); j=receita(n)
    imp=",".join(b for b,s in imped.items() if n in s) or "-"
    print(f"{len(v['anos'])} | {j.get('data_inicio_atividade')} | {j.get('descricao_situacao_cadastral')} | {','.join(sorted(v['anos']))} ({v['n']}) | {imp} | {j.get('razao_social')} | {c}")
