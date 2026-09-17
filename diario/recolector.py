# -*- coding: utf-8 -*-
"""MHF DIARIO - recolector. Baja precios de Twelve Data y titulares por RSS.
No escribe analisis: solo datos comprobables. Escribe diario/datos.json."""
import json, os, time, urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
import semaforo, earnings, niveles
from datetime import datetime, timezone

API   = "https://api.twelvedata.com/quote"
SERIE = "https://api.twelvedata.com/time_series"
CLAVE = os.environ.get("TWELVE_KEY", "")
LOTE, ESPERA = 8, 62          # el plan gratis da 8 creditos por minuto
SALIDA = "diario/datos.json"

# (simbolo, nombre, bloque) - todo ETF/divisa/cripto de EEUU, que es lo que da el plan gratis
UNIVERSO = [
    # --- BOLSA E INDICES (indices, no ETF) ---
    ("SPX",     "S&P 500",            "bolsa"),
    ("IXIC",    "Nasdaq",             "bolsa"),
    ("VIX",     "VIX",                "bolsa"),
    ("DXY",     "Dolar (DXY)",        "bolsa"),
    ("N225",    "Nikkei",             "bolsa"),
    ("KS11",    "Kospi",              "bolsa"),
    ("000300.SHG", "CSI 300",         "bolsa"),
    # --- ROTACION POR SECTORES (esto SI son ETF, es lo unico que hay) ---
    ("XLE",  "Energia",              "sectores"),
    ("XLF",  "Financieras",          "sectores"),
    ("XLK",  "Tecnologia",           "sectores"),
    ("XLU",  "Utilities",            "sectores"),
    ("XLY",  "Consumo discrecional", "sectores"),
    ("XLP",  "Consumo basico",       "sectores"),
    ("XLV",  "Salud",                "sectores"),
    ("XLI",  "Industriales",         "sectores"),
    # --- IA ---
    ("NVDA", "Nvidia",               "ia"),
    ("MRVL", "Marvell (posicion)",   "ia"),
    ("AVGO", "Broadcom",             "ia"),
    ("SMH",  "Semiconductores",      "ia"),
    ("MU",   "Micron",               "ia"),
    ("AMD",  "AMD",                  "ia"),
    # --- BONOS Y CREDITO ---
    ("SHY",  "Bono 1-3 anos",        "bonos"),
    ("IEF",  "Bono 7-10 anos",       "bonos"),
    ("TLT",  "Bono 20+ anos",        "bonos"),
    ("LQD",  "Credito bueno",        "bonos"),
    ("HYG",  "Credito basura",       "bonos"),
    # --- METALES ---
    ("GCZ2026", "Oro (futuro dic)",  "metales"),
    ("GLD",  "Oro (GLD)",            "metales"),
    ("SLV",  "Plata",                "metales"),
    ("CPER", "Cobre",                "metales"),
    # --- ENERGIA ---
    ("USO",  "Petroleo (USO)",       "energia"),
    ("BRENT","Brent",                "energia"),
    # --- DIVISAS ---
    ("EUR/USD", "Euro/Dolar",        "divisas"),
    ("USD/JPY", "Dolar/Yen",         "divisas"),
    ("USD/CNY", "Dolar/Yuan",        "divisas"),
    # --- CRIPTO ---
    ("BTC/USD", "Bitcoin",           "cripto"),
]

RSS = [
    ("Economia",      "https://www.investing.com/rss/news_14.rss"),
    ("Mercados",      "https://www.investing.com/rss/news_25.rss"),
    ("Divisas",       "https://www.investing.com/rss/news_1.rss"),
    ("Materias",      "https://www.investing.com/rss/news_11.rss"),
    ("Cripto",        "https://www.investing.com/rss/news_301.rss"),
    ("CNBC mercados", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"),
    ("CNBC economia", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
]


def pide(simbolos):
    q = urllib.parse.urlencode({"symbol": ",".join(simbolos), "apikey": CLAVE})
    with urllib.request.urlopen(API + "?" + q, timeout=30) as r:
        return json.load(r)


def precios():
    out, fallos = {}, []
    simbolos = [s for s, _, _ in UNIVERSO]
    for i in range(0, len(simbolos), LOTE):
        trozo = simbolos[i:i + LOTE]
        if i:
            time.sleep(ESPERA)
        try:
            d = pide(trozo)
        except Exception as e:
            fallos.append(("lote %d" % (i // LOTE), "%s: %s" % (type(e).__name__, e)))
            continue
        if len(trozo) == 1:
            d = {trozo[0]: d}
        for s in trozo:
            v = d.get(s) or {}
            if v.get("status") == "error" or "close" not in v:
                fallos.append((s, str(v.get("message", "sin dato"))[:80]))
                continue
            try:
                out[s] = {
                    "precio": float(v["close"]),
                    "cambio_pct": float(v.get("percent_change") or 0.0),
                    "cierre_previo": float(v.get("previous_close") or 0.0),
                    "maximo_52": float((v.get("fifty_two_week") or {}).get("high") or 0.0),
                    "minimo_52": float((v.get("fifty_two_week") or {}).get("low") or 0.0),
                    "fecha": v.get("datetime", ""),
                }
            except (TypeError, ValueError) as e:
                fallos.append((s, "dato ilegible: %r" % (e,)))
    return out, fallos


def titulares(tope=8):
    vistos, out = set(), []
    for nombre, url in RSS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MHF-DIARIO/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                raiz = ET.fromstring(r.read())
        except Exception:
            continue                       # una fuente caida no tumba el diario
        n = 0
        for it in raiz.iter("item"):
            t = (it.findtext("title") or "").strip()
            if not t or t.lower() in vistos:
                continue
            vistos.add(t.lower())
            out.append({"fuente": nombre, "titular": t,
                        "fecha": (it.findtext("pubDate") or "").strip()})
            n += 1
            if n >= tope:
                break
    return out



def velas(simbolo, n=280):
    """Velas diarias para calcular EMA y niveles. 1 credito por peticion."""
    q = urllib.parse.urlencode({"symbol": simbolo, "interval": "1day",
                                "outputsize": str(n), "order": "ASC", "apikey": CLAVE})
    with urllib.request.urlopen(SERIE + "?" + q, timeout=30) as r:
        d = json.load(r)
    if d.get("status") == "error" or not d.get("values"):
        raise RuntimeError(str(d.get("message", "sin velas"))[:80])
    return [(float(v["high"]), float(v["low"]), float(v["close"])) for v in d["values"]]


def niveles_de(tickers):
    """EMA50, EMA200 y niveles mas tocados de cada empresa que presenta."""
    out, fallos = {}, []
    for i, t in enumerate(sorted(set(tickers))[:7]):
        if i:
            time.sleep(ESPERA / 4)          # estas son 1 credito, no hace falta esperar tanto
        try:
            a = niveles.analiza(velas(t))
            if a:
                out[t] = a
            else:
                fallos.append((t, "pocas velas"))
        except Exception as e:
            fallos.append((t, "%s: %s" % (type(e).__name__, str(e)[:60])))
    return out, fallos


def main():
    if not CLAVE:
        raise SystemExit("falta TWELVE_KEY")
    px, fallos = precios()
    d = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "universo": [{"simbolo": s, "nombre": n, "bloque": b} for s, n, b in UNIVERSO],
        "precios": px,
        "titulares": titulares(),
        "fallos": fallos,
    }
    # --- semaforo de peligro, resultados y calendario de la semana
    try:
        e = earnings.estado()
        ev = semaforo.de_hoy()
        niv, tit, mot = semaforo.decide(ev, [x["ticker"] for x in e["hoy"]], None, None)
        tks = ["BTC/USD"] + [x["ticker"] for x in e["hoy"]] + [x["ticker"] for x in e["semana"]]
        niv_t, fal_n = niveles_de(tks)
        d["extra"] = {"semaforo": {"nivel": niv, "titulo": tit, "motivos": mot},
                      "earnings": e, "semana": semaforo.semana(), "niveles": niv_t}
        for t_, e_ in fal_n:
            fallos.append(("niveles " + t_, e_))
    except Exception as ex:
        d["extra"] = {"error": "%s: %s" % (type(ex).__name__, ex)}
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    json.dump(d, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("precios %d/%d · titulares %d · fallos %d"
          % (len(px), len(UNIVERSO), len(d["titulares"]), len(fallos)))
    for s, e in fallos:
        print("  fallo %s: %s" % (s, e))


if __name__ == "__main__":
    main()
