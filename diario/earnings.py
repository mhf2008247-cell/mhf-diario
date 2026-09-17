# -*- coding: utf-8 -*-
"""Escaneo de resultados AUTOMATICO.

Fuente: calendario de Nasdaq (api.nasdaq.com, sin clave). Da fecha, hora, consenso de BPA,
BPA del ano pasado y, cuando ya presentaron, el BPA REAL y la SORPRESA en %.
La reaccion del precio sale de Yahoo (sin clave, la misma que usa el bot V6).

Antes esta lista se mantenia A MANO y el 17-sep-2026 tenia tres errores a la vez:
CCL puesto el 17 cuando presenta el 29, ADBE puesto el 11 cuando presento el 10,
y ADBE marcado como "batio" cuando en BPA fallo un 2,26 %.
Por eso ya no se mantiene a mano. Si la fuente se cae, se usa diario/earnings.json
como red y la pagina avisa de que el dato es viejo."""
import json, os, urllib.request, urllib.error, datetime as dt

CAL   = "https://api.nasdaq.com/api/calendar/earnings?date=%s"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=3mo&interval=1d"
UA    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
         "Accept": "application/json"}
FICH  = "diario/earnings.json"          # solo red de seguridad
MINCAP = 15_000_000_000                 # 15.000 M$: por debajo no entra en el diario
VIGILA = {"MRVL", "NVDA", "AMD", "AVGO", "TSM", "AAPL", "MSFT", "GOOGL", "AMZN", "META",
          "TSLA", "CCL", "RCL", "NCLH", "ADBE", "ORCL", "CRM", "MU", "SMCI", "PLTR"}
ADELANTE, ATRAS, DIAS_FRESCO = 14, 7, 8


def _pide(url, tiempo=20):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=tiempo) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _num(s):
    """'$1.43' -> 1.43   '($0.28)' -> -0.28   '' -> None"""
    if not s: return None
    s = str(s).strip().replace("$", "").replace(",", "")
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try: v = float(s)
    except ValueError: return None
    return -v if neg else v


def _cap(s):
    try: return float(str(s).replace("$", "").replace(",", ""))
    except Exception: return 0.0


def _cuando(t):
    t = (t or "").lower()
    if "pre-market" in t: return "antes de abrir"
    if "after-hours" in t: return "tras el cierre"
    return "sin hora confirmada"


def _interesa(r):
    return r.get("symbol") in VIGILA or _cap(r.get("marketCap")) >= MINCAP


def _dia(fecha):
    d = _pide(CAL % fecha)
    if not d: return None
    try: return d["data"]["rows"] or []
    except Exception: return []


_CIERRES = {}
def _cierres(tk):
    if tk in _CIERRES: return _CIERRES[tk]
    d = _pide(CHART % tk)
    out = []
    try:
        r = d["chart"]["result"][0]
        for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
            if c: out.append((dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), float(c)))
    except Exception:
        out = []
    _CIERRES[tk] = out
    return out


def reaccion(tk, fecha, cuando):
    """% del dia en que el mercado digirio los resultados.
    Si presento antes de abrir, es ESE dia. Si no, la sesion siguiente.
    Devuelve (pct, fecha_de_la_reaccion) o (None, None)."""
    cl = _cierres(tk)
    if len(cl) < 2: return None, None
    i = next((k for k, (f, _) in enumerate(cl) if f >= fecha), None)
    if i is None: return None, None
    j = i if cuando == "antes de abrir" else i + 1
    if j < 1 or j >= len(cl): return None, None
    return (cl[j][1] / cl[j - 1][1] - 1) * 100, cl[j][0]


def _entrada(r, fecha):
    cu = _cuando(r.get("time"))
    real, prev = _num(r.get("eps")), _num(r.get("lastYearEPS"))
    cons = _num(r.get("epsForecast"))
    sor = _num(r.get("surprise"))
    e_basura = False
    e = {"fecha": fecha, "ticker": r.get("symbol", "?"),
         "empresa": (r.get("name") or "").replace(" Inc.", "").replace(" Corporation", "")
                                          .replace(", Inc.", "").strip()[:26],
         "cuando": cu, "consenso": cons, "real": real, "sorpresa": sor, "ano_pasado": prev}
    # guardia: si el consenso es absurdo frente al ano pasado, la fuente trae basura
    # (visto el 17-sep-2026: MU con "consenso 31,17 $" contra 2,86 $ del ano anterior)
    if cons is not None and prev not in (None, 0) and abs(cons) > 10 * abs(prev):
        cons = None; sor = None
        e_basura = True
    trozos = []
    if cons is not None: trozos.append("consenso %.2f $" % cons)
    if prev is not None: trozos.append("hace un ano %.2f $" % prev)
    e["consenso"] = cons; e["sorpresa"] = sor
    e["nota"] = " · ".join(trozos) if trozos else ("dato de consenso descartado por incoherente"
                                                   if e_basura else "")
    return e


def _sin_gemelos(lst):
    """LEN y LEN.B son la misma empresa. Se queda la que trae consenso."""
    mejor = {}
    for e in lst:
        k = (e["fecha"], e["empresa"].lower())
        v = mejor.get(k)
        if v is None or (v.get("consenso") is None and e.get("consenso") is not None):
            mejor[k] = e
    return list(mejor.values())


def estado(hoy=None):
    h = dt.date.fromisoformat(hoy) if hoy else dt.date.today()
    pres, ya, fallos = [], [], 0

    for k in range(0, ADELANTE + 1):
        f = (h + dt.timedelta(days=k)).isoformat()
        rows = _dia(f)
        if rows is None: fallos += 1; continue
        for r in rows:
            if _interesa(r) and _num(r.get("eps")) is None:
                pres.append(_entrada(r, f))

    for k in range(1, ATRAS + 1):
        f = (h - dt.timedelta(days=k)).isoformat()
        rows = _dia(f)
        if rows is None: fallos += 1; continue
        for r in rows:
            if not _interesa(r) or _num(r.get("eps")) is None: continue
            e = _entrada(r, f)
            pct, fr = reaccion(e["ticker"], f, e["cuando"])
            e["reaccion_pct"] = round(pct, 2) if pct is not None else None
            s, real, cons = e["sorpresa"], e["real"], e["consenso"]
            if s is not None and cons is not None and real is not None:
                verbo = "batio" if s > 0 else ("fallo" if s < 0 else "clavo")
                e["resumen"] = "%s el consenso por %.1f %% (%.2f $ frente a %.2f $)%s" % (
                    verbo, abs(s), real, cons, (", reaccion del %s" % fr) if fr else "")
            else:
                e["resumen"] = "sin consenso publicado"
            e["batio_y_cayo"] = bool(s is not None and s > 0 and
                                     e["reaccion_pct"] is not None and e["reaccion_pct"] < 0)
            ya.append(e)

    if fallos and not pres and not ya:          # la fuente se cayo entera -> red de seguridad
        try:
            d = json.load(open(FICH, encoding="utf-8"))
            v = (h - dt.date.fromisoformat(d.get("revisado", "1970-01-01"))).days
            p = d.get("presentan") or []
            return {"hoy": [e for e in p if e.get("fecha") == h.isoformat()],
                    "semana": sorted([e for e in p if e.get("fecha", "") >= h.isoformat()],
                                     key=lambda x: x["fecha"]),
                    "ya": sorted(d.get("ya_presentaron") or [],
                                 key=lambda x: x.get("fecha", ""), reverse=True)[:6],
                    "batio_y_cayo": [e for e in (d.get("ya_presentaron") or [])
                                     if e.get("batio_y_cayo")],
                    "dias_sin_revisar": v, "caducada": True, "fuente": "copia de seguridad"}
        except Exception:
            return {"hoy": [], "semana": [], "ya": [], "batio_y_cayo": [],
                    "dias_sin_revisar": 999, "caducada": True, "fuente": "sin datos"}

    pres = _sin_gemelos(pres)
    ya = _sin_gemelos(ya)
    ya.sort(key=lambda x: x["fecha"], reverse=True)
    pres.sort(key=lambda x: (x["fecha"], x["ticker"]))
    return {"hoy": [e for e in pres if e["fecha"] == h.isoformat()],
            "semana": pres,
            "ya": ya[:6],
            "batio_y_cayo": [e for e in ya if e.get("batio_y_cayo")],
            "dias_sin_revisar": 0,
            "caducada": bool(fallos) and not pres,
            "fuente": "Nasdaq"}


def tickers_hoy(hoy=None):
    return [e["ticker"] for e in estado(hoy)["hoy"]]


if __name__ == "__main__":
    import sys
    e = estado(sys.argv[1] if len(sys.argv) > 1 else None)
    print("fuente:", e["fuente"], "· caducada:", e["caducada"])
    print("\nHOY:", [(x["ticker"], x["cuando"]) for x in e["hoy"]] or "nadie")
    print("\nPROXIMOS 8 DIAS:")
    for x in e["semana"]: print("  %s %-6s %-26s %-22s %s" % (x["fecha"], x["ticker"], x["empresa"], x["cuando"], x["nota"]))
    print("\nYA PRESENTARON:")
    for x in e["ya"]:
        print("  %s %-6s %-24s %s%s" % (x["fecha"], x["ticker"], x["empresa"], x["resumen"],
              ("  ->  %+.2f %%" % x["reaccion_pct"]) if x["reaccion_pct"] is not None else ""))
    print("\nBATIO Y CAYO:", [(x["ticker"], x["reaccion_pct"]) for x in e["batio_y_cayo"]] or "ninguno")
