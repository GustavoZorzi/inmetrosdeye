"""
scripts/process.py  —  Deye Inmetro
Baixa o CSV do Inmetro, processa e salva dados.json com links de manuais/datasheets.
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

# ── Base de documentos Brasil (manuais + datasheets) ──────────────────────────
DOCS = [
    # MANUAIS
    {"t":"SUN-(3-12)K-G06P3-EU-BM2-P1","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2025/12/22/%E3%80%90B%E3%80%91Maunal_SUN-3-12K-G06P3-EU-BM2-P1_20251222_pt.pdf"},
    {"t":"SUN-15K-G06P3-EU-CM2-P1","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2026/01/12/%E3%80%90B%E3%80%91Maunal_SUN-15K-G06P3-EU-CM2-P1_20260112_pt.pdf"},
    {"t":"SUN-(30-36)K-G04P3-EU-CM2","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2026/01/12/%E3%80%90B%E3%80%91Maunal_SUN-30-36k-G04P3-EU-CM2_20260112_pt.pdf"},
    {"t":"SUN-10K-G02P1-EU-CM2-P","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2025/10/09/%E3%80%90b%E3%80%91manual_sun-10k-g02p1-eu-cm2-p_20251009_pt.pdf"},
    {"t":"SUN-(7.6-12)K-SG02LP1-EU-AM3-P","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2026/02/26/%E3%80%90B%E3%80%91Manual_SUN-7.6-12K-SG02LP1-EU-AM3-P_20260226_pt.pdf"},
    {"t":"SUN-7.5K-SG05LP1-EU-SM2-P","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2025/10/08/%E3%80%90b%E3%80%91manual_sun-7.5k-sg05lp1-eu-sm2-p_20251008_pt.pdf"},
    {"t":"SUN-(8-15)K-SG01LP2-US-AM3","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2025/12/08/%E3%80%90B%E3%80%91Manual_SUN-8-15K-SG01LP2-US-AM3_20251208_pt.pdf"},
    {"t":"SUN-(3.6-10)K-SG05LP1-EU-AM2-P","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2025/12/03/rand/2205/%E3%80%90b%E3%80%91manual_sun-3.6-10k-sg05lp1-eu-am2-p_20251203_pt.pdf"},
    {"t":"SUN-(12-16)K-SG01LP1-EU-AM3-P","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2025/12/04/%E3%80%90B%E3%80%91Manual_SUN-12-16K-SG01LP1-EU-AM3-P_20251204_pt.pdf"},
    {"t":"SUN-(5-12)K-SG05LP2-US-SM2","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2026/02/26/rand/8093/%E3%80%90b%E3%80%91manual_sun-5-12k-sg05lp2-us-sm2_20260226_pt.pdf"},
    {"t":"SUN-(3-6)K-OG02LP1-EU-AM1","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2026/02/26/%E3%80%90B%E3%80%91Manual_SUN-3-6K-OG02LP1-EU-AM1_20260226_pt.pdf"},
    {"t":"SUN-(3.6-6)K-OG01LP1-EU-AM2","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2025/09/15/%E3%80%90b%E3%80%91manual_sun-3.6-6k-og01lp1-eu-am2_20250915_pt.pdf"},
    {"t":"SUN-(29.9-50)K-SG01HP3-EU-BM4","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2026/02/28/rand/7596/%E3%80%90b%E3%80%91manual_sun-29.9-50k-sg01hp3-eu-bm4_20260228_pt.pdf"},
    {"t":"SUN-(8-15)K-SG01HP3-US-AM2","tp":"manual","url":"https://pt.deyeinverter.com/deyeinverter/2026/02/26/rand/4358/%E3%80%90b%E3%80%91manual_sun-8-15k-sg01hp3-us-am2_20260226_pt.pdf"},
    # DATASHEETS
    {"t":"SUN-(25-30)K-SG02HP3-EU-AM3","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-25-30k-sg02hp3-eu-am3_20250805_pt.pdf"},
    {"t":"SUN-(8-15)K-SG01HP3-US-AM2","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-8-15k-sg01hp3-us-am2_20250805_pt.pdf"},
    {"t":"SUN-(5-25)K-SG01HP3-EU","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-5-25k-sg01hp3-eu_20250805_pt.pdf"},
    {"t":"SUN-(3-6)K-SG04LP1-EU","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/09/05/%E3%80%90b%E3%80%91datasheet_sun-3-6k-sg04lp1_20250905_pt.pdf"},
    {"t":"SUN-(7-8)K-SG05LP1-EU-SM2","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-7-8k-sg05lp1-eu-sm2_20250805_pt.pdf"},
    {"t":"SUN-M(60-100)G4-EU-Q0","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m60-80-100g4-eu-q0_20250805_pt.pdf"},
    {"t":"SUN-M(30-50)G4-EU-Q0-I","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m30-40-50g4-eu-q0-i_20250805_pt.pdf"},
    {"t":"SUN-(3-6)K-OG01LP1-EU-AM2","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3-6k-og01lp1-eu-am2_20250805_pt.pdf"},
    {"t":"SUN-(3-6)K-SG03LP1-EU","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-6k-sg03lp1_20250805_pt.pdf"},
    {"t":"SUN-M(130-225)G4-EU-Q0-I","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m130-225g4-eu-q0-i_20250805_pt.pdf"},
    {"t":"SUN-BK60-100SG01-EU-AM2","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-bk60-100sg01-eu-am2_20250805_pt.pdf"},
    {"t":"SUN-(8-15)K-SG01HP2-US-AM2","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-8-15k-sg01hp2-us-am2_20250805_pt.pdf"},
    {"t":"SUN-(3.6-10)K-SG05LP1-EU","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-10k-sg05lp1-eu_20250805_pt.pdf"},
    {"t":"SUN-(18-20)K-G06P3-EU-AM2","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-18-20k-g06p3-eu-am2_20250805_pt.pdf"},
    {"t":"SUN-(3.6-10)K-SG05LP1-EU-AM2-P","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-10k-sg05lp1-eu-am2-p_20250805_pt.pdf"},
    {"t":"SUN-M(130-200)G4-EU-Q0","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m130-160-180-200g4-eu-q0_20250805_pt-1.pdf"},
    {"t":"SUN-BK160-200SG01-EU-AM2","tp":"datasheet","url":"https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-bk160-200sg01-eu-am2_20250805_pt.pdf"},
]


def _pot_in_range(pot, lo, hi):
    return lo * 0.9 <= pot <= hi * 1.1


def get_docs(modelo):
    """Retorna {manual, datasheet} para o modelo dado."""
    m = modelo.upper().strip().replace(" ", "")
    result = {"manual": None, "datasheet": None}

    # Microinversor M/S: potência em W
    micro = re.search(r"SUN-[MS](\d+)G(\d)", m)
    if micro:
        pw, gen = int(micro.group(1)), micro.group(2)
        for doc in DOCS:
            dt = doc["t"].upper().replace(" ", "")
            dr = re.search(r"SUN-[MS]\((\d+)-(\d+)\)G(\d)", dt)
            if dr and int(dr.group(1)) <= pw <= int(dr.group(2)):
                k = doc["tp"]
                if not result[k]: result[k] = doc["url"]
        return result

    # BK storage
    bk = re.search(r"SUN-BK(\d+)(.+)", m)
    if bk:
        bk_pow, bk_suf = int(bk.group(1)), bk.group(2)
        for doc in DOCS:
            dt = doc["t"].upper().replace(" ", "")
            br = re.search(r"SUN-BK(\d+)-?(\d+)?", dt)
            if br:
                lo = int(br.group(1))
                hi = int(br.group(2)) if br.group(2) else lo
                if lo <= bk_pow <= hi:
                    # Verifica família (SG01, SG02…)
                    dm = re.search(r"BK\d+-?\d*([A-Z0-9]+)", dt)
                    mm = re.search(r"BK\d+([A-Z0-9]+)", m)
                    if dm and mm:
                        df = dm.group(1).split("-")[0]
                        mf = mm.group(1).split("-")[0]
                        if df[:4] == mf[:4]:
                            k = doc["tp"]
                            if not result[k]: result[k] = doc["url"]
        return result

    # Inversores padrão SUN-{N}K-{FAM}
    pm = re.search(r"SUN-([0-9.,]+)K-([A-Z0-9]+)", m)
    if not pm:
        return result

    pot = float(pm.group(1).replace(",", "."))
    fam = pm.group(2)[:4]   # primeiros 4 chars da família: G06P, SG05, OG01, SG01…

    for doc in DOCS:
        dt = doc["t"].upper().replace(" ", "")
        # Range
        dr = re.search(r"SUN-\(([0-9.,]+)-([0-9.,]+)\)K-([A-Z0-9]+)", dt)
        if dr:
            lo = float(dr.group(1).replace(",", "."))
            hi = float(dr.group(2).replace(",", "."))
            doc_fam = dr.group(3)[:4]
        else:
            sr = re.search(r"SUN-([0-9.,]+)K-([A-Z0-9]+)", dt)
            if not sr: continue
            lo = hi = float(sr.group(1).replace(",", "."))
            doc_fam = sr.group(2)[:4]

        if doc_fam != fam: continue
        if not _pot_in_range(pot, lo, hi): continue

        k = doc["tp"]
        if not result[k]: result[k] = doc["url"]

    return result


# ── Resto do process.py (igual ao anterior) ───────────────────────────────────
def download(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; DeyeInmetroBot/2.0)",
        "Accept": "text/csv,*/*",
    })
    for attempt in range(1, 5):
        try:
            print(f"  tentativa {attempt}/3…", flush=True)
            with urllib.request.urlopen(req, context=ctx, timeout=240) as r:
                data = r.read()
            print(f"  {len(data):,} bytes", flush=True)
            return data
        except Exception as e:
            print(f"  erro: {e}", flush=True)
            if attempt == 4: raise

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
        if g(c,"Status") != "Ativo":    continue
        if g(c,"ItemStatus") != "Incluido": continue
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
        if   d["mr"] in ("SUP","DIS"):              marca = "Deye Inverter"
        elif d["modelo"].upper() not in supp_dist:  marca = "Deye Inversores"
        else: continue

        docs = get_docs(d["modelo"])
        items.append({
            "numero": d["numero"], "marca": marca, "modelo": d["modelo"],
            "tipo": categorize(d["modelo"], d["familia"]),
            "familia": d["familia"], "descricao": d["descricao"],
            "potencia": parse_potencia(d["descricao"], d["modelo"]),
            "data_concessao": d["data_concessao"], "data_validade": d["data_validade"],
            "data_alter": d["data_alter"], "portaria": d["portaria"],
            "importado": d["importado"], "pais": d["pais"],
            "manual": docs["manual"],
            "datasheet": docs["datasheet"],
        })

    items.sort(key=lambda x: x["modelo"].upper())
    return items

def main():
    print("🔽  Baixando CSV do Inmetro…", flush=True)
    items = parse(decode(download(CSV_URL)))
    inv = sum(1 for d in items if d["marca"] == "Deye Inversores")
    ivt = sum(1 for d in items if d["marca"] == "Deye Inverter")
    com_docs = sum(1 for d in items if d["manual"] or d["datasheet"])
    payload = {"ok": True, "total": len(items), "inversores": inv, "inverter": ivt,
               "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M"), "items": items}
    assign_docs(items)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    print(f"✅  {len(items)} modelos  |  Docs: {com_docs}/{len(items)}", flush=True)

if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════
#  CATÁLOGO DE DOCUMENTOS DEYE (manuais + datasheets)
#  Fonte: pt.deyeinverter.com/download/
# ═══════════════════════════════════════════════════════════════

DOCS_CATALOG = [
  # (padrão_modelo, url, tipo['manual'|'datasheet'])
  ("SUN-(3-12)K-G06P3-EU-BM2","https://pt.deyeinverter.com/deyeinverter/2025/12/22/%E3%80%90B%E3%80%91Maunal_SUN-3-12K-G06P3-EU-BM2-P1_20251222_pt.pdf","manual"),
  ("SUN-15K-G06P3-EU-CM2","https://pt.deyeinverter.com/deyeinverter/2026/01/12/%E3%80%90B%E3%80%91Maunal_SUN-15K-G06P3-EU-CM2-P1_20260112_pt.pdf","manual"),
  ("SUN-(30-36)K-G04P3-EU-CM2","https://pt.deyeinverter.com/deyeinverter/2026/01/12/%E3%80%90B%E3%80%91Maunal_SUN-30-36k-G04P3-EU-CM2_20260112_pt.pdf","manual"),
  ("SUN-10K-G02P1-EU-CM2","https://pt.deyeinverter.com/deyeinverter/2025/10/09/%E3%80%90b%E3%80%91manual_sun-10k-g02p1-eu-cm2-p_20251009_pt.pdf","manual"),
  ("SUN-(7.6-12)K-SG02LP1-EU-AM3","https://pt.deyeinverter.com/deyeinverter/2026/02/26/%E3%80%90B%E3%80%91Manual_SUN-7.6-12K-SG02LP1-EU-AM3-P_20260226_pt.pdf","manual"),
  ("SUN-7.5K-SG05LP1-EU-SM2","https://pt.deyeinverter.com/deyeinverter/2025/10/08/%E3%80%90b%E3%80%91manual_sun-7.5k-sg05lp1-eu-sm2-p_20251008_pt.pdf","manual"),
  ("SUN-(8-15)K-SG01LP2-US-AM3","https://pt.deyeinverter.com/deyeinverter/2025/12/08/%E3%80%90B%E3%80%91Manual_SUN-8-15K-SG01LP2-US-AM3_20251208_pt.pdf","manual"),
  ("SUN-(3.6-10)K-SG05LP1-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/12/03/rand/2205/%E3%80%90b%E3%80%91manual_sun-3.6-10k-sg05lp1-eu-am2-p_20251203_pt.pdf","manual"),
  ("SUN-(12-16)K-SG01LP1-EU-AM3","https://pt.deyeinverter.com/deyeinverter/2025/12/04/%E3%80%90B%E3%80%91Manual_SUN-12-16K-SG01LP1-EU-AM3-P_20251204_pt.pdf","manual"),
  ("SUN-(5-12)K-SG05LP2-US-SM2","https://pt.deyeinverter.com/deyeinverter/2026/02/26/rand/8093/%E3%80%90b%E3%80%91manual_sun-5-12k-sg05lp2-us-sm2_20260226_pt.pdf","manual"),
  ("SUN-(3-6)K-OG02LP1-EU-AM1","https://pt.deyeinverter.com/deyeinverter/2026/02/26/%E3%80%90B%E3%80%91Manual_SUN-3-6K-OG02LP1-EU-AM1_20260226_pt.pdf","manual"),
  ("SUN-(3.6-6)K-OG01LP1-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/09/15/%E3%80%90b%E3%80%91manual_sun-3.6-6k-og01lp1-eu-am2_20250915_pt.pdf","manual"),
  ("SUN-(29.9-50)K-SG01HP3-EU-BM4","https://pt.deyeinverter.com/deyeinverter/2026/02/28/rand/7596/%E3%80%90b%E3%80%91manual_sun-29.9-50k-sg01hp3-eu-bm4_20260228_pt.pdf","manual"),
  ("SUN-(8-15)K-SG01HP3-US-AM2","https://pt.deyeinverter.com/deyeinverter/2026/02/26/rand/4358/%E3%80%90b%E3%80%91manual_sun-8-15k-sg01hp3-us-am2_20260226_pt.pdf","manual"),
  ("SUN-(5-25)K-SG01HP3-EU","https://pt.deyeinverter.com/deyeinverter/2026/02/26/%E3%80%90b%E3%80%91manual_sun-5-25k-sg01hp3-eu_20260226_pt.pdf","manual"),
  ("SUN-(16-25)K-SG05LP3-EU-SM2","https://pt.deyeinverter.com/deyeinverter/2025/12/17/%E3%80%90b%E3%80%91manual_sun-16-25k-sg05lp3-eu-sm2_20251217_pt.pdf","manual"),
  ("SUN-(8-15)K-SG02LP1-EU-AM3","https://pt.deyeinverter.com/deyeinverter/2025/11/04/%E3%80%90b%E3%80%91manual_sun-8-15k-sg02lp1-eu-am3_20251104_pt.pdf","manual"),
  ("SUN-M(60-225)G4-EU-Q0","https://pt.deyeinverter.com/deyeinverter/2025/09/15/%E3%80%90b%E3%80%91manual_sun-m60-225g4-eu-q0_20250915_pt.pdf","manual"),
  ("SUN-M(130-225)G4-EU-Q0-I","https://pt.deyeinverter.com/deyeinverter/2025/09/15/%E3%80%90b%E3%80%91manual_sun-m130-225g4-eu-q0-i_20250915_pt.pdf","manual"),
  ("SUN-M(60-100)G3-EU-Q0","https://pt.deyeinverter.com/deyeinverter/2024/08/12/%E3%80%90b%E3%80%91manual_sun-m60-100g3-eu-q0_20240812_pt.pdf","manual"),
  ("SUN-BK(60-100)SG01-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/18/%E3%80%90b%E3%80%91manual_sun-bk60-100sg01-eu-am2_20250818_pt.pdf","manual"),
  ("SUN-BK(160-200)SG01-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/18/%E3%80%90b%E3%80%91manual_sun-bk160-200sg01-eu-am2_20250818_pt.pdf","manual"),
  ("BOS-G","https://pt.deyeinverter.com/deyeinverter/2025/04/21/%E3%80%90b%E3%80%91manual_bos-g_20250421_pt.pdf","manual"),
  ("BOS-G PRO","https://pt.deyeinverter.com/deyeinverter/2025/04/21/%E3%80%90b%E3%80%91manual_bos-g-pro_20250421_pt.pdf","manual"),
  ("SUN-(3-6)K-SG04LP1-EU","https://pt.deyeinverter.com/deyeinverter/2025/07/03/%E3%80%90b%E3%80%91manual_sun-3-6k-sg04lp1-eu_20250703_pt.pdf","manual"),
  ("SUN-(5-12)K-SG04LP1-EU","https://pt.deyeinverter.com/deyeinverter/2025/07/03/%E3%80%90b%E3%80%91manual_sun-5-12k-sg04lp1-eu_20250703_pt.pdf","manual"),
  ("SUN-(3.6-10)K-G05P1-EU","https://pt.deyeinverter.com/deyeinverter/2024/12/10/%E3%80%90b%E3%80%91manual_sun-3.6-10k-g05p1-eu_20241210_pt.pdf","manual"),
  ("SUN-(12-20)K-G05P3-EU","https://pt.deyeinverter.com/deyeinverter/2024/12/10/%E3%80%90b%E3%80%91manual_sun-12-20k-g05p3-eu_20241210_pt.pdf","manual"),
  ("SUN-(25-36)K-G05P3-EU","https://pt.deyeinverter.com/deyeinverter/2024/12/10/%E3%80%90b%E3%80%91manual_sun-25-36k-g05p3-eu_20241210_pt.pdf","manual"),
  # DATASHEETS
  ("SUN-(25-30)K-SG02HP3-EU-AM3","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-25-30k-sg02hp3-eu-am3_20250805_pt.pdf","datasheet"),
  ("SUN-(8-15)K-SG01HP3-US-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-8-15k-sg01hp3-us-am2_20250805_pt.pdf","datasheet"),
  ("SUN-(5-25)K-SG01HP3-EU","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-5-25k-sg01hp3-eu_20250805_pt.pdf","datasheet"),
  ("SUN-(3-6)K-SG04LP1-EU","https://pt.deyeinverter.com/deyeinverter/2025/09/05/%E3%80%90b%E3%80%91datasheet_sun-3-6k-sg04lp1_20250905_pt.pdf","datasheet"),
  ("SUN-(7-8)K-SG05LP1-EU-SM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-7-8k-sg05lp1-eu-sm2_20250805_pt.pdf","datasheet"),
  ("SUN-M(60-100)G4-EU-Q0","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m60-80-100g4-eu-q0_20250805_pt.pdf","datasheet"),
  ("SUN-M(30-50)G4-EU-Q0-I","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m30-40-50g4-eu-q0-i_20250805_pt.pdf","datasheet"),
  ("SUN-(3-6)K-OG01LP1-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3-6k-og01lp1-eu-am2_20250805_pt.pdf","datasheet"),
  ("SUN-(3-6)K-SG03LP1-EU","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-6k-sg03lp1_20250805_pt.pdf","datasheet"),
  ("SUN-M(130-225)G4-EU-Q0-I","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m130-225g4-eu-q0-i_20250805_pt.pdf","datasheet"),
  ("SUN-BK(60-100)SG01-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-bk60-100sg01-eu-am2_20250805_pt.pdf","datasheet"),
  ("SUN-(8-15)K-SG01HP2-US-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-8-15k-sg01hp2-us-am2_20250805_pt.pdf","datasheet"),
  ("SUN-(3.6-10)K-SG05LP1-EU","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-10k-sg05lp1-eu_20250805_pt.pdf","datasheet"),
  ("SUN-(18-20)K-G06P3-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-18-20k-g06p3-eu-am2_20250805_pt.pdf","datasheet"),
  ("SUN-(3.6-10)K-SG05LP1-EU-AM2-P","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-10k-sg05lp1-eu-am2-p_20250805_pt.pdf","datasheet"),
  ("SUN-M(130-200)G4-EU-Q0","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m130-160-180-200g4-eu-q0_20250805_pt-1.pdf","datasheet"),
  ("SUN-BK(160-200)SG01-EU-AM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-bk160-200sg01-eu-am2_20250805_pt.pdf","datasheet"),
  ("SUN-(3-12)K-G06P3-EU-BM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3-12k-g06p3-eu-bm2_20250805_pt.pdf","datasheet"),
  ("SUN-(3.6-10)K-G05P1-EU","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-10k-g05p1-eu_20250805_pt.pdf","datasheet"),
  ("SUN-(25-50)K-G04P3-EU","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-25-50k-g04p3-eu_20250805_pt.pdf","datasheet"),
  ("SUN-(3.6-6)K-SG01LP1-EU-AM3","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-3.6-6k-sg01lp1-eu-am3_20250805_pt.pdf","datasheet"),
  ("SUN-(7.6-12)K-SG02LP1-EU-AM3","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-7.6-12k-sg02lp1-eu-am3_20250805_pt.pdf","datasheet"),
  ("SUN-(16-25)K-SG05LP3-EU-SM2","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-16-25k-sg05lp3-eu-sm2_20250805_pt.pdf","datasheet"),
  ("BOS-G","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_bos-g_20250805_pt.pdf","datasheet"),
  ("BOS-G PRO","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_bos-g-pro_20250805_pt.pdf","datasheet"),
  ("SUN-(12-20)K-G05P3-EU","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-12-20k-g05p3-eu_20250805_pt.pdf","datasheet"),
  ("SUN-M(185-225)G4-EU-Q0","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-m185-225g4-eu-q0_20250805_pt.pdf","datasheet"),
  ("SUN-(5-12)K-SG04LP1-EU","https://pt.deyeinverter.com/deyeinverter/2025/08/08/%E3%80%90b%E3%80%91datasheet_sun-5-12k-sg04lp1-eu_20250805_pt.pdf","datasheet"),
]


def _nrm(s):
    return re.sub(r"[\s\-]+", "", s.upper())


def _expand_pattern(pat):
    """Expande SUN-(3-12)K-G06P3 → lista de variantes normalizadas."""
    rng = re.search(r"\(([0-9.]+)[-]([0-9.]+)\)", pat)
    if not rng:
        return [_nrm(pat)]
    s, e, pre, suf = float(rng.group(1)), float(rng.group(2)), pat[:rng.start()], pat[rng.end():]
    vals = {rng.group(1), rng.group(2)}
    for step in [0.1,0.2,0.5,1,1.5,2,2.5,3,4,5,6,7,7.5,7.6,8,10,12,14,15,16,20,25,29.9,30,36,40,50]:
        if s <= step <= e:
            vals.add(str(step) if step != int(step) else str(int(step)))
    return [_nrm(f"{pre}{v}{suf}") for v in vals]


def _doc_matches(modelo, pat):
    mn = _nrm(modelo)
    for fam in _expand_pattern(pat):
        fb = re.sub(r"(EU|US)(AM|BM|SM|CM)\d+(P\d?)?$", "", fam)
        mb = re.sub(r"(EU|US)(AM|BM|SM|CM)\d+(P\d?)?$", "", mn)
        if mb and fb and mb.startswith(fb):
            return True
        cl = min(len(fb), len(mb), 12)
        if cl >= 6 and mb[:cl] == fb[:cl]:
            return True
    return False


def _deye_search(modelo):
    m = re.match(r"(SUN-[\d.,]+K)", modelo.upper())
    if m:
        t = m.group(1).lower().replace(",", ".")
        return f"https://pt.deyeinverter.com/download/product-manual/?q={t}"
    return "https://pt.deyeinverter.com/download/product-manual/"


def assign_docs(items):
    """Adiciona campo 'docs' a cada item."""
    for item in items:
        modelo = item["modelo"]
        docs = []
        seen = set()
        for pat, url, tipo in DOCS_CATALOG:
            if _doc_matches(modelo, pat) and url not in seen:
                seen.add(url)
                docs.append({"tipo": tipo, "url": url, "titulo": pat})
        if not docs:
            docs = [{"tipo": "busca", "url": _deye_search(modelo), "titulo": "Buscar manual — Deye Downloads"}]
        item["docs"] = docs
    return items
