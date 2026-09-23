# -*- coding: utf-8 -*-
"""MHF DIARIO - precios REALES de indices, futuros y rentabilidades (Yahoo, sin clave).
Sustituyen a los ETF que se usaban como aproximacion (VIXY no es el VIX, UUP no es el DXY,
GLD no es el precio del oro por onza...). Si Yahoo falla, se queda el ETF de Twelve Data."""
import json, urllib.request, urllib.parse
from portafolio import rellena_ultimo
from datetime import datetime, timezone

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=1mo&interval=1d"

# (simbolo Yahoo, clave en el diario, nombre, bloque, ETF al que sustituye, es rentabilidad)
REALES = [
    ("^GSPC",     "SPX",    "S&P 500 (índice)",      "bolsa",   "SPY",  False),
    ("^NDX",      "NDX",    "Nasdaq 100 (índice)",   "bolsa",   "QQQ",  False),
    ("^VIX",      "VIX",    "VIX (miedo bolsa)",     "bolsa",   "VIXY", False),
    ("DX-Y.NYB",  "DXY",    "Índice dólar DXY",      "bolsa",   "UUP",  False),
    ("^N225",     "NIKKEI", "Nikkei 225 (Japón)",    "bolsa",   "EWJ",  False),
    ("^KS11",     "KOSPI",  "Kospi (Corea)",         "bolsa",   "EWY",  False),
    ("000300.SS", "CSI300", "CSI 300 (China)",       "bolsa",   "ASHR", False),
    ("GC=F",      "ORO",    "Oro $/onza (futuro)",   "metales", "GLD",  False),
    ("SI=F",      "PLATA",  "Plata $/onza (futuro)", "metales", "SLV",  False),
    ("HG=F",      "COBRE",  "Cobre $/libra (futuro)","metales", "CPER", False),
    ("CL=F",      "WTI",    "Petróleo WTI $/barril", "energia", "USO",  False),
    ("BZ=F",      "BRENT",  "Brent $/barril",        "energia", "BNO",  False),
    ("^IRX",      "US3M",   "Tipo 3 meses EE.UU. %", "bonos",   None,   True),
    ("^FVX",      "US5Y",   "Bono 5 años EE.UU. %",  "bonos",   None,   True),
    ("^TNX",      "US10Y",  "Bono 10 años EE.UU. %", "bonos",   None,   True),
    ("^TYX",      "US30Y",  "Bono 30 años EE.UU. %", "bonos",   None,   True),
]


def uno(sym):
    req = urllib.request.Request(URL % urllib.parse.quote(sym), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.load(r)["chart"]["result"][0]
    m = j["meta"]
    ts = j.get("timestamp") or []
    cl = (j.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    cl = rellena_ultimo(ts, cl, m)
    par = [(t, c) for t, c in zip(ts, cl) if c is not None]
    if len(par) < 2:
        raise RuntimeError("menos de 2 cierres")
    (_, prev), (t, last) = par[-2], par[-1]
    return {
        "precio": float(last),
        "cambio_pct": (last / prev - 1) * 100 if prev else 0.0,
        "cierre_previo": float(prev),
        "maximo_52": float(m.get("fiftyTwoWeekHigh") or 0.0),
        "minimo_52": float(m.get("fiftyTwoWeekLow") or 0.0),
        "fecha": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"),
        "fuente": "Yahoo",
    }


MESES = "FGHJKMNQUVXZ"
# raiz de futuro -> (sufijo de bolsa en Yahoo, meses que cotizan)
CONTRATOS = {"CL": (".NYM", MESES), "BZ": (".NYM", MESES), "GC": (".CMX", "GJMQVZ"),
             "SI": (".CMX", "HKNUZ"), "HG": (".CMX", "HKNUZ")}


def _cierres(sym):
    req = urllib.request.Request(URL % urllib.parse.quote(sym), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.load(r)["chart"]["result"][0]
    cl = (j.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    cl = rellena_ultimo(j.get("timestamp") or [], cl, j.get("meta") or {})
    return [c for c in cl if c is not None]


def sin_cambio_de_contrato(ysym, v):
    """El 'CL=F' de Yahoo salta de contrato al vencer (22-sep-2026: octubre -> noviembre)
    y ese dia marca una caida falsa (-4,9 % cuando el contrato real bajaba -1,4 %).
    Se busca el contrato concreto cuyo ultimo cierre es el del continuo y el cambio
    se calcula DENTRO de ese contrato."""
    raiz = ysym[:-2]
    if raiz not in CONTRATOS:
        return v
    suf, meses = CONTRATOS[raiz]
    hoy = datetime.now(timezone.utc)
    for k in range(0, 8):
        mes, ano = (hoy.month - 1 + k) % 12, hoy.year + (hoy.month - 1 + k) // 12
        if MESES[mes] not in meses:
            continue
        sym = "%s%s%02d%s" % (raiz, MESES[mes], ano % 100, suf)
        try:
            c = _cierres(sym)
        except Exception:
            continue
        if len(c) >= 2 and abs(c[-1] / v["precio"] - 1) < 0.0005:
            if abs(c[-2] / v["cierre_previo"] - 1) > 0.0005:
                v["cierre_previo"] = float(c[-2])
                v["cambio_pct"] = (c[-1] / c[-2] - 1) * 100
                v["nota"] = "cambio de contrato: calculado en " + sym
            v["contrato"] = sym
            return v
    return v


def todos():
    """Devuelve (precios, universo, sustituidos, fallos)."""
    px, uni, sust, fallos = {}, [], [], []
    for ysym, clave, nombre, bloque, etf, tipo in REALES:
        try:
            v = sin_cambio_de_contrato(ysym, uno(ysym))
        except Exception as e:
            fallos.append((clave, "Yahoo %s: %s" % (type(e).__name__, str(e)[:60])))
            continue
        if tipo:                      # rentabilidad: el cambio que importa son puntos basicos
            v["pb"] = (v["precio"] - v["cierre_previo"]) * 100
        px[clave] = v
        uni.append({"simbolo": clave, "nombre": nombre, "bloque": bloque})
        if etf:
            sust.append(etf)
    return px, uni, sust, fallos


if __name__ == "__main__":
    p, u, s, f = todos()
    for k, v in p.items():
        print(k, round(v["precio"], 3), "%+.2f%%" % v["cambio_pct"], v.get("pb"), v["fecha"])
    print("sustituye", s, "fallos", f)
