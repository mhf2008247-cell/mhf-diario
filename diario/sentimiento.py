# -*- coding: utf-8 -*-
"""MHF DIARIO - miedo y codicia. Dos indices publicos, sin clave:
 - Cripto: alternative.me (el clasico de bitcoin, 0-100, uno al dia).
 - Bolsa: CNN Fear & Greed (siete indicadores de la bolsa de EE.UU., 0-100).
Se muestra ahora / ayer / hace una semana / hace un mes, como las webs de cripto."""
import json, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def etiqueta(v):
    v = float(v)
    if v < 25: return "Miedo extremo"
    if v < 45: return "Miedo"
    if v <= 55: return "Neutral"
    if v <= 75: return "Codicia"
    return "Codicia extrema"


def _json(url, extra=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(extra or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
        return json.load(r)


def cripto():
    d = _json("https://api.alternative.me/fng/?limit=31")["data"]
    def f(i):
        v = int(d[i]["value"]); return {"valor": v, "etiqueta": etiqueta(v)}
    return {"ahora": f(0), "ayer": f(1), "semana": f(7), "mes": f(30),
            "fuente": "alternative.me"}


def bolsa():
    j = _json("https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
              {"Referer": "https://edition.cnn.com/", "Origin": "https://edition.cnn.com"})
    g = j["fear_and_greed"]
    def f(k):
        v = round(float(g[k])); return {"valor": v, "etiqueta": etiqueta(v)}
    return {"ahora": f("score"), "ayer": f("previous_close"), "semana": f("previous_1_week"),
            "mes": f("previous_1_month"), "ano": f("previous_1_year"), "fuente": "CNN"}


def estado():
    out, fallos = {}, []
    for k, fn in (("bolsa", bolsa), ("cripto", cripto)):
        try:
            out[k] = fn()
        except Exception as e:
            fallos.append(("sentimiento " + k, "%s: %s" % (type(e).__name__, str(e)[:60])))
    return out, fallos


if __name__ == "__main__":
    print(json.dumps(estado(), ensure_ascii=False, indent=1))
