import re, json, time, urllib.request, zipfile, io, datetime
UA={"User-Agent":"Mozilla/5.0"}
def get(u,t=60): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t).read()
def dv(base12):
    def d(s,pesos):
        r=sum(int(a)*b for a,b in zip(s,pesos))%11; return "0" if r<2 else str(11-r)
    d1=d(base12,[5,4,3,2,9,8,7,6,5,4,3,2]); d2=d(base12+d1,[6,5,4,3,2,9,8,7,6,5,4,3,2]); return base12+d1+d2
CAND={"Fundação Esperança - FÉ (BA)":"08197332","Associação Central de Cidadania (BA)":"18338286",
 "Instituto Casa da Cidadania (BA)":"07961355","ASDEC (BA)":"12049952","MOC (BA)":"16260713",
 "OELA (AM/AP)":"03470157","Instituto Centec (CE)":"03021597"}
imped={}
for base in ["cepim","ceis","cnep"]:
    for d in range(15):
        dia=(datetime.date.today()-datetime.timedelta(days=d)).strftime("%Y%m%d")
        try:
            z=zipfile.ZipFile(io.BytesIO(get(f"https://portaldatransparencia.gov.br/download-de-dados/{base}/{dia}",120)))
            imped[base]=set(re.sub(r"\D","",x)[:8] for x in re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}",z.read(z.namelist()[0]).decode("latin-1"))); print(base,dia); break
        except Exception: pass
hoje=datetime.date.today()
for nome,raiz in CAND.items():
    c=dv(raiz+"0001")
    try: j=json.loads(get(f"https://brasilapi.com.br/api/cnpj/v1/{c}",30))
    except Exception as e: j={"erro":str(e)}
    ab=j.get("data_inicio_atividade"); anos=(hoje-datetime.date.fromisoformat(ab)).days//365 if ab else "?"
    imp=",".join(b for b,s in imped.items() if raiz in s) or "nenhum"
    print(f"{nome} | {c} | {j.get('razao_social')} | abertura {ab} ({anos} anos) | {j.get('descricao_situacao_cadastral')} | natureza {j.get('natureza_juridica')} | impedimentos: {imp}")
    time.sleep(0.6)
