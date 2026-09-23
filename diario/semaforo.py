# -*- coding: utf-8 -*-
"""Semaforo de PELIGRO del dia. No predice el mercado: mira la agenda.
ROJO   = hoy hay un evento que mueve el mercado entero (Fed, IPC, empleo, banco central)
AMARILLO = hay resultados relevantes, un dato de segunda fila, o la volatilidad esta alta
VERDE  = no hay nada en la agenda"""
import json, os, datetime as dt

CAL = "diario/calendario.json"

# Empresas cuyos resultados mueven el mercado entero, no solo su accion
GORDAS = {"NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "JPM"}


def carga():
    try:
        return json.load(open(CAL, encoding="utf-8"))
    except Exception:
        return {"eventos": [], "propios": []}


def de_hoy(hoy=None):
    hoy = hoy or dt.date.today().isoformat()
    d = carga()
    todos = (d.get("eventos") or []) + (d.get("propios") or [])
    return [e for e in todos if e.get("fecha") == hoy]


def semana(desde=None):
    """Los proximos 7 dias, hoy incluido."""
    h = dt.date.fromisoformat(desde) if desde else dt.date.today()
    fin = h + dt.timedelta(days=7)
    d = carga()
    todos = (d.get("eventos") or []) + (d.get("propios") or [])
    out = []
    for e in todos:
        try:
            f = dt.date.fromisoformat(e["fecha"])
        except Exception:
            continue
        if h <= f <= fin:
            out.append(dict(e, dias=(f - h).days))
    return sorted(out, key=lambda x: x["fecha"])


def decide(eventos_hoy, earnings_hoy, vol_pct, vol_p80):
    """Devuelve (nivel, titulo, motivos[])."""
    motivos, nivel = [], "verde"
    for e in eventos_hoy:
        motivos.append((e["nivel"], e["que"]))
        if e["nivel"] == "rojo":
            nivel = "rojo"
        elif nivel != "rojo":
            nivel = "amarillo"
    gordas = [x for x in earnings_hoy if x.upper() in GORDAS]
    if gordas:
        nivel = "rojo"
        motivos.append(("rojo", "resultados de " + ", ".join(gordas)))
    elif earnings_hoy:
        if nivel == "verde":
            nivel = "amarillo"
        motivos.append(("amarillo", "resultados de " + ", ".join(earnings_hoy[:6])))
    if vol_pct is not None and vol_p80 is not None and vol_pct > vol_p80:
        if nivel == "verde":
            nivel = "amarillo"
        motivos.append(("amarillo", "la volatilidad está en el 20 %% más alto del último año (%.1f %%)" % vol_pct))
    titulo = {"rojo": "DÍA DE PELIGRO", "amarillo": "OJO HOY", "verde": "DÍA TRANQUILO"}[nivel]
    if not motivos:
        motivos = [("verde", "no hay nada en la agenda")]
    return nivel, titulo, motivos
