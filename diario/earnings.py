# -*- coding: utf-8 -*-
"""Escaneo de resultados. Lee diario/earnings.json (lista mantenida a mano)
y avisa si esta vieja. El filtro 'batio y cayo' se marca a mano porque el dato
de sorpresas no es gratis en ninguna fuente comprobada."""
import json, datetime as dt

FICH = "diario/earnings.json"
DIAS_FRESCO = 8


def carga():
    try:
        return json.load(open(FICH, encoding="utf-8"))
    except Exception:
        return {"revisado": "", "presentan": [], "ya_presentaron": []}


def estado(hoy=None):
    h = dt.date.fromisoformat(hoy) if hoy else dt.date.today()
    d = carga()
    try:
        vieja = (h - dt.date.fromisoformat(d.get("revisado", ""))).days
    except Exception:
        vieja = 999
    pres = d.get("presentan") or []
    hoy_l = [e for e in pres if e.get("fecha") == h.isoformat()]
    fin = h + dt.timedelta(days=7)
    semana = [e for e in pres
              if e.get("fecha") and h.isoformat() <= e["fecha"] <= fin.isoformat()]
    ya = sorted(d.get("ya_presentaron") or [], key=lambda x: x.get("fecha", ""), reverse=True)
    return {
        "hoy": hoy_l,
        "semana": sorted(semana, key=lambda x: x["fecha"]),
        "ya": ya[:6],
        "batio_y_cayo": [e for e in ya if e.get("batio_y_cayo")],
        "dias_sin_revisar": vieja,
        "caducada": vieja > DIAS_FRESCO,
    }


def tickers_hoy(hoy=None):
    return [e["ticker"] for e in estado(hoy)["hoy"]]
