# -*- coding: utf-8 -*-
"""MHF DIARIO - recolector. Baja precios de Twelve Data y titulares por RSS.
No escribe analisis: solo datos comprobables. Escribe diario/datos.json."""
import json, os, time, urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
import semaforo, earnings
from datetime import datetime, timezone

API   = "https://api.twelvedata.com/quote"
CLAVE = os.environ.get("TWELVE_KEY", "")
LOTE, ESPERA = 8, 62          # el plan gratis da 8 creditos por minuto
SALIDA = "diario/datos.json"

# (simbolo, nombre, bloque) - todo ETF/divisa/cripto de EEUU, que es lo que da el plan gratis
UNIVERSO = [
    ("SPY",  "S&P 500",            "bolsa"),
    ("QQQ",  "Nasdaq 100",         "bolsa"),
    ("DIA",  "Dow Jones",          "bolsa"),
    ("IWM",  "Russell 2000",       "bolsa"),
    ("EWJ",  "Japon",              "mundo"),
    ("EWH",  "Hong Kong",          "mundo"),
    ("VGK",  "Europa",             "mundo"),
    ("EEM",  "Emergentes",         "mundo"),
    ("SHY",  "Bono 1-3 anos",      "bonos"),
    ("IEF",  "Bono 7-10 anos",     "bonos"),
    ("TLT",  "Bono 20+ anos",      "bonos"),
    ("LQD",  "Credito bueno",      "bonos"),
    ("HYG",  "Credito basura",     "bonos"),
    ("GLD",  "Oro",                "metales"),
    ("SLV",  "Plata",              "metales"),
    ("CPER", "Cobre",              "metales"),
    ("USO",  "Petroleo",           "energia"),
    ("VIXY", "Volatilidad (VIX)",  "miedo"),
    ("UUP",  "Dolar (DXY)",        "divisas"),
    ("XLE",  "Energia",            "sectores"),
    ("XLF",  "Financieras",        "sectores"),
    ("XLK",  "Tecnologia",         "sectores"),
    ("XLU",  "Utilities",          "sectores"),
    ("XLY",  "Consumo discrecional","sectores"),
    ("XLP",  "Consumo basico",     "sectores"),
    ("XLV",  "Salud",              "sectores"),
    ("SMH",  "Semiconductores",    "semis"),
    ("MRVL", "Marvell (posicion)", "semis"),
    ("EUR/USD", "Euro/Dolar",      "divisas"),
    ("USD/JPY", "Dolar/Yen",       "divisas"),
    ("BTC/USD", "Bitcoin",         "cripto"),
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
        d["extra"] = {"semaforo": {"nivel": niv, "titulo": tit, "motivos": mot},
                      "earnings": e, "semana": semaforo.semana()}
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
