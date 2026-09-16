# -*- coding: utf-8 -*-
"""Niveles de un valor, a partir de sus velas diarias. Todo son DATOS calculados:
EMA50, EMA200, maximo y minimo de 52 semanas, y los niveles donde el precio se ha
dado la vuelta mas veces (pivotes agrupados). No dice si comprar."""


def ema(v, n):
    k = 2.0 / (n + 1.0)
    e = None
    for x in v:
        e = x if e is None else x * k + e * (1 - k)
    return e


def pivotes(altos, bajos, lado=5):
    """Maximos y minimos locales: una vela mas alta (o baja) que las 'lado' de cada costado."""
    out = []
    for i in range(lado, len(altos) - lado):
        v = altos[i]
        if v == max(altos[i - lado:i + lado + 1]):
            out.append(("techo", v))
        v = bajos[i]
        if v == min(bajos[i - lado:i + lado + 1]):
            out.append(("suelo", v))
    return out


def agrupa(pv, tol=0.015):
    """Junta pivotes que estan a menos de tol (1,5 %) unos de otros.
       Los que mas pivotes juntan son los niveles donde el precio se ha girado mas veces."""
    zonas = []
    for tipo, p in sorted(pv, key=lambda x: x[1]):
        if zonas and abs(p - zonas[-1]["centro"]) / zonas[-1]["centro"] <= tol:
            z = zonas[-1]
            z["precios"].append(p); z["toques"] += 1
            z["centro"] = sum(z["precios"]) / len(z["precios"])
            z["tipos"].add(tipo)
        else:
            zonas.append({"centro": p, "precios": [p], "toques": 1, "tipos": {tipo}})
    return zonas


def analiza(velas, tope=4):
    """velas: lista de (alto, bajo, cierre), de la mas vieja a la mas nueva."""
    if len(velas) < 60:
        return None
    altos = [v[0] for v in velas]; bajos = [v[1] for v in velas]; cie = [v[2] for v in velas]
    p = cie[-1]
    e50 = ema(cie[-250:], 50) if len(cie) >= 50 else None
    e200 = ema(cie, 200) if len(cie) >= 200 else None
    v52 = velas[-252:] if len(velas) >= 252 else velas
    zonas = agrupa(pivotes(altos[-160:], bajos[-160:]))
    for z in zonas:
        z["dist"] = (z["centro"] - p) / p * 100
    # los mas relevantes: primero por toques, luego por cercania al precio de hoy
    rel = sorted(zonas, key=lambda z: (-z["toques"], abs(z["dist"])))[:tope]
    encima = sorted([z for z in zonas if z["dist"] > 0.3], key=lambda z: z["dist"])[:2]
    debajo = sorted([z for z in zonas if z["dist"] < -0.3], key=lambda z: -z["dist"])[:2]

    def limpia(z):
        return {"precio": round(z["centro"], 2), "toques": z["toques"],
                "dist_pct": round(z["dist"], 2),
                "tipo": "techo" if z["tipos"] == {"techo"} else ("suelo" if z["tipos"] == {"suelo"} else "los dos")}
    return {
        "precio": round(p, 2),
        "ema50": None if e50 is None else round(e50, 2),
        "ema200": None if e200 is None else round(e200, 2),
        "dist_ema50": None if e50 is None else round((p - e50) / e50 * 100, 2),
        "dist_ema200": None if e200 is None else round((p - e200) / e200 * 100, 2),
        "max52": round(max(v[0] for v in v52), 2),
        "min52": round(min(v[1] for v in v52), 2),
        "resistencias": [limpia(z) for z in encima],
        "soportes": [limpia(z) for z in debajo],
        "mas_tocados": [limpia(z) for z in rel],
    }
