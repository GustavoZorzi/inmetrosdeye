"""
scripts/process.py  —  Deye Inmetro
Baixa o CSV do Inmetro, processa e salva dados.json.
Roda via GitHub Action todo dia às 00:00 BRT.
"""
import json, re, ssl, urllib.request
from datetime import datetime
from pathlib import Path

CSV_URL = (
    "https://dados.inmetro.gov.br/registro/"
    "SISTEMAS_E_EQUIPAMENTOS_PARA_ENERGIA_FOTOVOLTAICA_"
    "(MODULO_CONTROLADOR_DE_CARGA_INVERSOR_E_BATERIA).csv"
)
OUT_FILE = Path(__file__).parent.parent / "dados.json"

def download(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; DeyeInmetroBot/2.0)",
        "Accept": "text/csv,*/*",
    })
    for attempt in range(1, 4):
        try:
            print(f"  tentativa {attempt}/3…", flush=True)
            with urllib.request.urlopen(req, context=ctx, timeout=90) as r:
                data = r.read()
            print(f"  {len(data):,} bytes", flush=True)
            return data
        except Exception as e:
            print(f"  erro: {e}", flush=True)
            if attempt == 3: raise

def decode(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"): return raw.decode("utf-16", errors="replace")
    if raw[:3] == b"\xef\xbb\xbf":           return raw.decode("utf-8-sig", errors="replace")
    for enc in ("utf-8", "latin-1"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: continue
    return raw.decode("latin-1", errors="replace")

def split_row(line, sep):
    out, cur, inq = [], [], False
    for i, ch in enumerate(line):
        if ch == '"':
            if inq and i+1 < len(line) and line[i+1] == '"': cur.append('"')
            else: inq = not inq
        elif ch == sep and not inq: out.append("".join(cur).strip()); cur = []
        else: cur.append(ch)
    out.append("".join(cur).strip())
    return out

def categorize(modelo, familia=""):
    m = modelo.upper().strip().replace(" ", "")
    f = familia.upper()
    if m.startswith("H07"):                      return "bateria"
    if re.search(r"-BK\d", m):                  return "bateria"
    if "PCS" in m:                               return "bateria"
    if re.match(r"^SUN-[MS]\d", m):             return "microinversor"
    if re.match(r"^SUN-\d+G[234]", m):          return "microinversor"
    if re.match(r"^SUN\d+G", m):                return "microinversor"
    for p in ("BOS","RW-","SE","GE","AE","AI-","HVB","STM","ZY","WN","TS25"):
        if m.startswith(p):                      return "bateria"
    if "-OG" in m:                               return "offgrid"
    if re.search(r"-SG\d", m):                  return "hibrido"
    if re.search(r"K[-\s]*(G|HD)", m):          return "ongrid"
    if "MICRO" in f:                             return "microinversor"
    if any(x in f for x in ("BATERIA","STORAGE","BOS")): return "bateria"
    if any(x in f for x in ("HYBRID","HÍBRIDO","HIBRIDO")): return "hibrido"
    return "ongrid"

def parse_potencia(descricao, modelo):
    for txt in [descricao, modelo]:
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*[Kk][Ww]", txt)
        if m:
            try: return float(m.group(1).replace(",","."))
            except: pass
        m = re.search(r"(\d{3,6})\s*W\b", txt)
        if m:
            try: return round(int(m.group(1))/1000, 2)
            except: pass
    m = re.search(r"-(\d+(?:[.,]\d+)?)[Kk]", modelo.upper())
    if m:
        try: return float(m.group(1).replace(",","."))
        except: pass
    return None

def clean(s): return (s or "").replace("\x00","").strip()

def parse(text):
    lines = text.splitlines()
    if not lines: raise ValueError("CSV vazio.")
    sep = ";" if lines[0].count(";") >= lines[0].count(",") else ","
    hdrs = split_row(lines[0], sep)
    idx  = {h.strip(): i for i, h in enumerate(hdrs)}

    def g(c, key): return clean(c[idx[key]]) if key in idx and idx[key] < len(c) else ""

    raw_items = []
    for ln in lines[1:]:
        if not ln.strip(): continue
        c = split_row(ln, sep)
        if c[idx["Status"]].strip() != "Ativo":    continue
        if c[idx["ItemStatus"]].strip() != "Incluido": continue
        modelo = g(c,"ItemModelo"); numero = g(c,"NumeroRegistro")
        if not modelo or not numero: continue
        razao = g(c,"RazaoSocial"); ru = razao.upper()
        if   "DEYE INVERSORES LTDA" in ru:            mr="INV"
        elif "DEYE BRASIL SUPPORT CENTER" in ru:      mr="SUP"
        elif "DEYE BRASIL DISTRIBUTION CENTER" in ru: mr="DIS"
        else: continue
        raw_items.append({
            "numero": numero, "mr": mr, "modelo": modelo,
            "familia": g(c,"Familia"), "descricao": g(c,"ItemDescricao"),
            "data_concessao": g(c,"DataConcessao"), "data_validade": g(c,"DataValidade"),
            "data_alter": g(c,"ItemDataAlteracao"), "portaria": g(c,"PortariaInmetro"),
            "importado": g(c,"ProdutoImportado"), "pais": g(c,"PaisOrigem"),
        })

    supp_dist = {d["modelo"].upper() for d in raw_items if d["mr"] in ("SUP","DIS")}
    items = []
    for d in raw_items:
        if   d["mr"] in ("SUP","DIS"):                 marca = "Deye Inverter"
        elif d["modelo"].upper() not in supp_dist:     marca = "Deye Inversores"
        else: continue
        items.append({
            "numero": d["numero"], "marca": marca, "modelo": d["modelo"],
            "tipo": categorize(d["modelo"], d["familia"]),
            "familia": d["familia"], "descricao": d["descricao"],
            "potencia": parse_potencia(d["descricao"], d["modelo"]),
            "data_concessao": d["data_concessao"], "data_validade": d["data_validade"],
            "data_alter": d["data_alter"], "portaria": d["portaria"],
            "importado": d["importado"], "pais": d["pais"],
        })

    items.sort(key=lambda x: x["modelo"].upper())
    return items

def main():
    print("🔽  Baixando CSV do Inmetro…", flush=True)
    items = parse(decode(download(CSV_URL)))
    inv = sum(1 for d in items if d["marca"] == "Deye Inversores")
    ivt = sum(1 for d in items if d["marca"] == "Deye Inverter")
    payload = {"ok": True, "total": len(items), "inversores": inv, "inverter": ivt,
               "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M"), "items": items}
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    print(f"✅  {len(items)} modelos  (Inversores: {inv} | Inverter: {ivt})", flush=True)

if __name__ == "__main__":
    main()
