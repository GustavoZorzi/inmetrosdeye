"""
scripts/process.py
Baixa o CSV do Inmetro e gera dados.json na raiz do repositório.
Executado pelo GitHub Action todo dia às 00:00 BRT.
"""

import json
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CSV_URL = ("https://dados.inmetro.gov.br/registro/SISTEMAS_E_EQUIPAMENTOS_PARA_ENERGIA_FOTOVOLTAICA_(MODULO_CONTROLADOR_DE_CARGA_INVERSOR_E_BATERIA).csv")

OUT_FILE = Path(__file__).parent.parent / "dados.json"


def download(url: str) -> bytes:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DeyeInmetroBot/1.0)",
        "Accept": "text/csv,*/*",
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(1, 5):
        try:
            print(f"  tentativa {attempt}/4…", flush=True)
            with urllib.request.urlopen(req, context=ctx, timeout=360) as r:
                data = r.read()
            print(f"  baixado: {len(data):,} bytes", flush=True)
            return data
        except Exception as e:
            print(f"  erro: {type(e)._name_}: {e}", flush=True)
            if attempt == 4:
                raise
    raise RuntimeError("Download falhou.")


def decode(raw: bytes) -> str:
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


def split_row(line: str, sep: str) -> list:
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


def parse(text: str) -> list:
    lines = text.splitlines()
    if not lines:
        raise ValueError("CSV vazio.")

    h0  = lines[0]
    sep = ";" if h0.count(";") >= h0.count(",") else ","
    hdrs = split_row(h0, sep)
    idx  = {h.strip(): i for i, h in enumerate(hdrs)}

    iNum    = idx["NumeroRegistro"]
    iStReg  = idx["Status"]
    iRazao  = idx["RazaoSocial"]
    iModelo = idx["ItemModelo"]
    iStItem = idx["ItemStatus"]
    iFam    = idx.get("Familia", -1)

    items = []
    for raw in lines[1:]:
        if not raw.strip():
            continue
        c = split_row(raw, sep)
        need = max(iNum, iStReg, iRazao, iModelo, iStItem)
        if len(c) <= need:
            continue
        if c[iStReg].strip() != "Ativo":
            continue
        if c[iStItem].strip() != "Incluido":
            continue

        modelo  = c[iModelo].strip()
        numero  = c[iNum].strip()
        razao   = c[iRazao].strip()
        familia = c[iFam].strip() if iFam >= 0 else ""

        if not modelo or not numero:
            continue

        razao_up = razao.upper()
        if "DEYE INVERSORES LTDA" in razao_up:
            marca = "Deye Inversores"
        elif "DEYE BRASIL" in razao_up:
            marca = "Deye Inverter"
        else:
            continue

        items.append({
            "numero":  numero,
            "marca":   marca,
            "modelo":  modelo,
            "familia": familia,
        })

    items.sort(key=lambda x: x["modelo"].upper())
    return items


def main():
    print("🔽  Baixando CSV do Inmetro…", flush=True)
    raw   = download(CSV_URL)
    text  = decode(raw)
    items = parse(text)

    inv = sum(1 for d in items if d["marca"] == "Deye Inversores")
    ivt = sum(1 for d in items if d["marca"] == "Deye Inverter")

    payload = {
        "ok":         True,
        "total":      len(items),
        "inversores": inv,
        "inverter":   ivt,
        "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "items":      items,
    }

    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"✅  dados.json salvo — {len(items)} modelos "
          f"(Inversores: {inv} | Inverter: {ivt})", flush=True)


if __name__ == "__main__":
    main()
