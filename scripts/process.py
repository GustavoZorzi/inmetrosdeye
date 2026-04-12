"""
scripts/process.py
Baixa o CSV do Inmetro e gera dados.json.
Executado pelo GitHub Action todo dia às 00:00 BRT.
"""
import json, re, ssl, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
import pytz

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
        "User-Agent": "Mozilla/5.0 (compatible; DeyeInmetroBot/1.0)",
        "Accept": "text/csv,*/*",
    })
    for attempt in range(1, 4):
        try:
            print(f"  tentativa {attempt}/3…", flush=True)
            with urllib.request.urlopen(req, context=ctx, timeout=90) as r:
                data = r.read()
            print(f"  baixado: {len(data):,} bytes", flush=True)
            return data
        except Exception as e:
            print(f"  erro: {e}", flush=True)
            if attempt == 3:
                raise


def decode(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig", errors="replace")
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def split_row(line, sep):
    out, cur, inq = [], [], False
    for i, ch in enumerate(line):
        if ch == '"':
            if inq and i + 1 < len(line) and line[i + 1] == '"':
                cur.append('"')
            else:
                inq = not inq
        elif ch == sep and not inq:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur).strip())
    return out


def categorize(modelo):
    """Classifica o modelo por tipo de inversor/produto."""
    m = modelo.upper().strip().replace(" ", "")
    # Cabo/acessório elétrico
    if m.startswith("H07"):
        return "bateria"
    # Microinversor: SUN-Mxxx ou SUN-Sxxx
    if re.match(r"^SUN-[MS]\d", m):
        return "microinversor"
    # Microinversor: SUN-\d+G2/G3/G4 (com hífen)
    if re.match(r"^SUN-\d+G[234]", m):
        return "microinversor"
    # Microinversor: SUN\d+G (sem hífen, modelos legados/americanos)
    if re.match(r"^SUN\d+G", m):
        return "microinversor"
    # Bateria / storage / acessórios
    for p in ("BOS", "RW-", "SE", "GE", "AE-", "AE", "AI-", "HVB", "STM", "ZY", "WN", "TS25"):
        if m.startswith(p):
            return "bateria"
    # Off-grid
    if "-OG" in m:
        return "offgrid"
    # Híbrido
    if re.search(r"-(SG|BK)\d", m):
        return "hibrido"
    # On-grid
    if re.search(r"K[-\s]*(G|HD|PCS)", m):
        return "ongrid"
    return "ongrid"  # fallback conservador


def parse(text):
    lines = text.splitlines()
    if not lines:
        raise ValueError("CSV vazio.")
    sep = ";" if lines[0].count(";") >= lines[0].count(",") else ","
    hdrs = split_row(lines[0], sep)
    idx = {h.strip(): i for i, h in enumerate(hdrs)}

    iNum = idx["NumeroRegistro"]
    iSt  = idx["Status"]
    iRaz = idx["RazaoSocial"]
    iMod = idx["ItemModelo"]
    iSti = idx["ItemStatus"]
    iFam = idx.get("Familia", -1)

    raw_items = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        c = split_row(ln, sep)
        if len(c) <= max(iNum, iSt, iRaz, iMod, iSti):
            continue
        if c[iSt].strip() != "Ativo" or c[iSti].strip() != "Incluido":
            continue
        modelo = c[iMod].strip()
        numero = c[iNum].strip()
        razao  = c[iRaz].strip()
        familia = c[iFam].strip() if iFam >= 0 else ""
        if not modelo or not numero:
            continue
        ru = razao.upper()
        if   "DEYE INVERSORES LTDA" in ru:          mr = "INV"
        elif "DEYE BRASIL SUPPORT CENTER" in ru:    mr = "SUP"
        elif "DEYE BRASIL DISTRIBUTION CENTER" in ru: mr = "DIS"
        else:
            continue
        raw_items.append({"numero": numero, "mr": mr, "modelo": modelo, "familia": familia})

    # Regra de dedup: Brasil Support/Distribution têm prioridade.
    # Se o mesmo modelo existe em Support/Dist, não mostra o da INVERSORES LTDA.
    supp_dist_modelos = {d["modelo"].upper() for d in raw_items if d["mr"] in ("SUP", "DIS")}
    items = []
    for d in raw_items:
        if d["mr"] in ("SUP", "DIS"):
            marca = "Deye Inverter"
        elif d["modelo"].upper() not in supp_dist_modelos:
            marca = "Deye Inversores"
        else:
            continue   # já está em Deye Inverter
        items.append({
            "numero":  d["numero"],
            "marca":   marca,
            "modelo":  d["modelo"],
            "familia": d["familia"],
            "tipo":    categorize(d["modelo"]),
        })

    items.sort(key=lambda x: x["modelo"].upper())
    return items


def main():
    print("🔽  Baixando CSV do Inmetro…", flush=True)
    raw   = download(CSV_URL)
    text  = decode(raw)
    items = parse(text)
    inv   = sum(1 for d in items if d["marca"] == "Deye Inversores")
    ivt   = sum(1 for d in items if d["marca"] == "Deye Inverter")
    tz = pytz.timezone("America/Sao_Paulo")
    now = datetime.now(tz)
    next_update = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    payload = {
        "ok":         True,
        "total":      len(items),
        "inversores": inv,
        "inverter":   ivt,
        "atualizado": now.strftime("%d/%m/%Y %H:%M"),
        "items":      items,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✅  dados.json — {len(items)} modelos (Inversores: {inv} | Inverter: {ivt})", flush=True)


if __name__ == "__main__":
    main()
