# -*- coding: utf-8 -*-
"""MHF DIARIO - portafolio. Un resumen diario de cada activo de la lista.
Solo NOMBRES: la página es pública, así que aquí no hay cantidades ni precios de entrada.

Precios y velas: Yahoo (sin clave, el mismo que usa el bot V6).
Próximos resultados: Nasdaq (sin clave). Titulares de cada empresa: Google Noticias (RSS).
Los titulares NO salen en la página (están en inglés): se los damos a Gemini para que
escriba la línea de cada activo."""
import json, re, time, urllib.request, urllib.parse, datetime as dt
import xml.etree.ElementTree as ET
import niveles

# (ticker, nombre, lo que se busca en noticias)
PORTAFOLIO = [
    ("KO",   "Coca-Cola",         "Coca-Cola KO stock"),
    ("NVDA", "Nvidia",            "Nvidia NVDA stock"),
    ("AVGO", "Broadcom",          "Broadcom AVGO stock"),
    ("SOFI", "SoFi Technologies", "SoFi Technologies SOFI stock"),
    ("ORCL", "Oracle",            "Oracle ORCL stock"),
    ("IBM",  "IBM",               "IBM stock"),
    ("MP",   "MP Materials",      "MP Materials stock"),
]

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
      "Accept": "application/json"}
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d"
FECHA = "https://api.nasdaq.com/api/analyst/%s/earnings-date"
NOTI = "https://news.google.com/rss/search?q=%s+when:2d&hl=en-US&gl=US&ceid=US:en"


def _get(url, tiempo=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=tiempo) as r:
        return r.read()


def velas(tk):
    j = json.loads(_get(CHART % urllib.parse.quote(tk)))["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    m = j["meta"]
    cl = rellena_ultimo(j["timestamp"], q["close"], m)
    out = []
    for t, h, l, c in zip(j["timestamp"], q["high"], q["low"], cl):
        if c is not None:
            h = c if h is None else h; l = c if l is None else l
            out.append((dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), float(h), float(l), float(c)))
    return out


def rellena_ultimo(ts, cierres, meta):
    """23-sep-2026: Yahoo deja la vela del último día con cierre VACÍO durante horas
    (KO: vela del 22 con close=None, pero meta.regularMarketPrice=88,61). Si se tira esa
    vela, el 'cambio del día' sale del día anterior. Se rellena con el precio de la meta
    cuando la meta es del mismo día que esa vela."""
    cl = list(cierres)
    p, tm = meta.get("regularMarketPrice"), meta.get("regularMarketTime")
    if cl and cl[-1] is None and p and tm and ts:
        f = lambda x: dt.datetime.utcfromtimestamp(x).strftime("%Y-%m-%d")
        if f(tm) == f(ts[-1]):
            cl[-1] = float(p)
    return cl


def _pct(a, b):
    return None if not b else (a / b - 1) * 100


def proximo_resultado(tk):
    """Fecha de los próximos resultados. 'estimada' = Nasdaq la calcula por el histórico,
    la empresa aún no la ha confirmado."""
    try:
        d = json.loads(_get(FECHA % tk))["data"]
    except Exception:
        return None
    txt = (d.get("reportText") or "") + " " + (d.get("announcement") or "")
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", txt)
    if m:
        f = dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    else:
        m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", txt)
        if not m:
            return None
        try:
            f = dt.datetime.strptime(" ".join(m.groups()), "%b %d %Y").date()
        except ValueError:
            return None
    return {"fecha": f.isoformat(), "estimada": "estimated" in txt or "algorithm" in txt}


def titulares(busca, tope=5):
    try:
        raiz = ET.fromstring(_get(NOTI % urllib.parse.quote_plus(busca)))
    except Exception:
        return []
    out, vistos = [], set()
    for it in raiz.iter("item"):
        t = (it.findtext("title") or "").strip()
        k = t.rsplit(" - ", 1)[0].lower()          # el mismo artículo sale en varios medios
        if t and k not in vistos:
            vistos.add(k); out.append(t)
        if len(out) >= tope:
            break
    return out


def uno(tk, nombre, busca):
    v = velas(tk)
    if len(v) < 30:
        raise RuntimeError("pocas velas")
    cie = [x[3] for x in v]
    p = cie[-1]
    ano = str(dt.date.today().year)
    ini_ano = next((x[3] for x in reversed(v) if x[0] < ano + "-01-01"), None)
    a = niveles.analiza([(x[1], x[2], x[3]) for x in v]) or {}
    return {
        "ticker": tk, "nombre": nombre, "fecha": v[-1][0], "precio": round(p, 2),
        "dia": _pct(p, cie[-2]),
        "semana": _pct(p, cie[-6]) if len(cie) > 6 else None,
        "mes": _pct(p, cie[-22]) if len(cie) > 22 else None,
        "ano": _pct(p, ini_ano),
        "niveles": a,
        "resultados": proximo_resultado(tk),
        "titulares": titulares(busca),
    }


def estado():
    out, fallos = [], []
    for i, (tk, nombre, busca) in enumerate(PORTAFOLIO):
        if i:
            time.sleep(1.5)                  # sin prisa: son fuentes gratis
        try:
            out.append(uno(tk, nombre, busca))
        except Exception as e:
            fallos.append(("portafolio " + tk, "%s: %s" % (type(e).__name__, str(e)[:60])))
    return out, fallos


if __name__ == "__main__":
    o, f = estado()
    for x in o:
        a = x["niveles"]
        print("%-5s %9.2f  día %+5.2f  sem %+6.2f  mes %+6.2f  año %s  EMA50 %s (%+.1f)  EMA200 %s  res %s  %d titulares"
              % (x["ticker"], x["precio"], x["dia"], x["semana"], x["mes"],
                 "%+.1f" % x["ano"] if x["ano"] is not None else "-",
                 a.get("ema50"), a.get("dist_ema50") or 0, a.get("ema200"), x["resultados"], len(x["titulares"])))
    print("fallos:", f)
