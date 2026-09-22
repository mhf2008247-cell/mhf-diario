# -*- coding: utf-8 -*-
"""MHF DIARIO - posicionamiento en contratos de futuros.
 - CFTC Commitments of Traders (informe oficial, cada viernes con datos del martes).
   Neto de los especuladores grandes (no comerciales) = largos - cortos.
   'Extremo 3 anos' = donde esta ese neto entre su minimo (0) y su maximo (100) de 3 anos.
 - Bitcoin: ratio de cuentas largas/cortas en futuros perpetuos de OKX (diario)."""
import json, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
CFTC = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
MERCADOS = [
    ("13874A", "S&P 500 (E-mini)"),
    ("209742", "Nasdaq 100 (mini)"),
    ("043602", "Bono 10 anos"),
    ("098662", "Dolar DXY"),
    ("099741", "Euro"),
    ("097741", "Yen"),
    ("088691", "Oro"),
    ("084691", "Plata"),
    ("085692", "Cobre"),
    ("067651", "Petroleo WTI"),
    ("133741", "Bitcoin (CME)"),
]


def cot():
    desde = (datetime.now(timezone.utc) - timedelta(days=3 * 365 + 10)).strftime("%Y-%m-%d")
    q = {"$select": "cftc_contract_market_code,report_date_as_yyyy_mm_dd,"
                    "noncomm_positions_long_all,noncomm_positions_short_all,open_interest_all",
         "$where": "cftc_contract_market_code in(%s) AND report_date_as_yyyy_mm_dd >= '%s'"
                   % (",".join("'%s'" % c for c, _ in MERCADOS), desde),
         "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": "5000"}
    req = urllib.request.Request(CFTC + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        filas = json.load(r)
    serie = {}
    for f in filas:
        try:
            neto = int(float(f["noncomm_positions_long_all"])) - int(float(f["noncomm_positions_short_all"]))
            serie.setdefault(f["cftc_contract_market_code"], []).append(
                (f["report_date_as_yyyy_mm_dd"][:10], neto, int(float(f["open_interest_all"]))))
        except (KeyError, ValueError):
            continue
    out = []
    for cod, nombre in MERCADOS:
        s = serie.get(cod) or []
        if len(s) < 2:
            continue
        fe, neto, oi = s[-1]
        netos = [x[1] for x in s]
        lo, hi = min(netos), max(netos)
        out.append({"mercado": nombre, "fecha": fe, "neto": neto, "cambio": neto - s[-2][1],
                    "pct_oi": 100.0 * neto / oi if oi else 0.0,
                    "extremo": 100.0 * (neto - lo) / (hi - lo) if hi > lo else 50.0})
    return out


def btc_ratio():
    u = "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1D"
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=20) as r:
        d = json.load(r)["data"]
    return {"ahora": float(d[0][1]), "ayer": float(d[1][1]), "semana": float(d[7][1]),
            "fecha": datetime.fromtimestamp(int(d[0][0]) / 1000, timezone.utc).strftime("%Y-%m-%d"),
            "fuente": "OKX"}


def estado():
    out, fallos = {}, []
    for k, fn in (("cot", cot), ("btc", btc_ratio)):
        try:
            out[k] = fn()
        except Exception as e:
            fallos.append(("posiciones " + k, "%s: %s" % (type(e).__name__, str(e)[:60])))
    return out, fallos


if __name__ == "__main__":
    print(json.dumps(estado(), ensure_ascii=False, indent=1))
