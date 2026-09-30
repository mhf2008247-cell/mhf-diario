# -*- coding: utf-8 -*-
"""Niveles de un valor, a partir de sus velas diarias. Todo son DATOS calculados:
EMA50, EMA200, máximo y mínimo de 52 semanas, y las ZONAS de soporte y resistencia.
No dice si comprar.

30-sep-2026, él: "las zonas de soportes y resistencias me las está marcando mal; revisé
uno o dos activos y no hay nada en ese precio". Tenía razón. La versión anterior:
  - daba por "zona" cualquier pico de 5 velas, aunque fuera ruido (salía "se giró 1 vez");
  - encadenaba pivotes a 1,5 % unos de otros, así que la zona se iba corriendo;
  - solo miraba 8 meses.
Ahora:
  - solo cuentan los giros de verdad: el precio se aleja al menos 1,5 ATR del pivote
    antes y después (un giro que se ve en el gráfico, no un dientecito);
  - las zonas se agrupan con un ancho fijo de 0,6 ATR (no se corren);
  - una zona necesita al menos 2 giros; el máximo y el mínimo de 52 semanas entran siempre;
  - se miran 2 años de velas y se da la zona como RANGO (desde-hasta), no un número suelto."""


def ema(v, n):
    k = 2.0 / (n + 1.0)
    e = None
    for x in v:
        e = x if e is None else x * k + e * (1 - k)
    return e


def atr(altos, bajos, cie, n=14):
    tr = [altos[0] - bajos[0]]
    for i in range(1, len(cie)):
        tr.append(max(altos[i] - bajos[i], abs(altos[i] - cie[i - 1]), abs(bajos[i] - cie[i - 1])))
    return sum(tr[-n:]) / min(n, len(tr))


def pivotes(altos, bajos, a, lado=5, alcance=20, giro=1.5):
    """Giros de verdad: máximo (o mínimo) de las 'lado' velas de cada costado Y el precio
    se aleja 'giro' ATR de él en las 'alcance' velas de antes y de después."""
    out = []
    n = len(altos)
    for i in range(lado, n - lado):
        ini, fin = max(0, i - alcance), min(n, i + alcance + 1)
        v = altos[i]
        if v == max(altos[i - lado:i + lado + 1]):
            if v - min(bajos[ini:i]) >= giro * a and v - min(bajos[i + 1:fin]) >= giro * a:
                out.append(("techo", v, i))
        v = bajos[i]
        if v == min(bajos[i - lado:i + lado + 1]):
            if max(altos[ini:i]) - v >= giro * a and max(altos[i + 1:fin]) - v >= giro * a:
                out.append(("suelo", v, i))
    return out


def agrupa(pv, ancho):
    """Zonas de ancho fijo: un pivote entra si cae a menos de 'ancho' del más bajo de la zona."""
    zonas = []
    for tipo, p, i in sorted(pv, key=lambda x: x[1]):
        if zonas and p - zonas[-1]["desde"] <= ancho:
            z = zonas[-1]
        else:
            z = {"desde": p, "precios": [], "tipos": set(), "idx": []}
            zonas.append(z)
        z["precios"].append(p); z["tipos"].add(tipo); z["idx"].append(i)
    # dos zonas pegadas (hueco < 0,5 ancho) se funden si juntas no pasan de 1,7 anchos (~1 ATR)
    fund = []
    for z in zonas:
        if fund and min(z["precios"]) - max(fund[-1]["precios"]) < 0.5 * ancho \
                and max(z["precios"]) - fund[-1]["desde"] <= 1.7 * ancho:
            f = fund[-1]
            f["precios"] += z["precios"]; f["tipos"] |= z["tipos"]; f["idx"] += z["idx"]
        else:
            fund.append(z)
    zonas = fund
    for z in zonas:
        z["hasta"] = max(z["precios"])
        z["centro"] = sum(z["precios"]) / len(z["precios"])
        z["toques"] = len(z["precios"])
        z["ultimo"] = max(z["idx"])
    return zonas


def analiza(velas, tope=4, anos=2):
    """velas: lista de (alto, bajo, cierre), de la más vieja a la más nueva."""
    if len(velas) < 60:
        return None
    altos = [v[0] for v in velas]; bajos = [v[1] for v in velas]; cie = [v[2] for v in velas]
    p = cie[-1]
    e50 = ema(cie[-250:], 50) if len(cie) >= 50 else None
    e200 = ema(cie, 200) if len(cie) >= 200 else None
    v52 = velas[-252:] if len(velas) >= 252 else velas
    max52 = max(v[0] for v in v52); min52 = min(v[1] for v in v52)

    w = min(len(velas), 252 * anos)
    A, B, C = altos[-w:], bajos[-w:], cie[-w:]
    a = atr(A, B, C)
    ancho = 0.6 * a
    zonas = [z for z in agrupa(pivotes(A, B, a), ancho) if z["toques"] >= 2]
    # el máximo y el mínimo de 52 semanas siempre son nivel (si no están ya dentro de una zona)
    for ext, tipo in ((max52, "techo"), (min52, "suelo")):
        if not any(z["desde"] - ancho / 2 <= ext <= z["hasta"] + ancho / 2 for z in zonas):
            zonas.append({"desde": ext, "hasta": ext, "centro": ext, "toques": 1,
                          "tipos": {tipo}, "ultimo": None, "extremo": True})
    for z in zonas:
        # una zona muy fina se ensancha a 0,3 ATR para que se vea como zona en el gráfico
        if z["hasta"] - z["desde"] < 0.3 * a:
            m = (z["hasta"] + z["desde"]) / 2
            z["desde"], z["hasta"] = m - 0.15 * a, m + 0.15 * a
        z["dist"] = (z["centro"] - p) / p * 100

    # por encima: la zona entera por encima del precio; por debajo: la zona entera por debajo
    encima = sorted([z for z in zonas if z["desde"] > p], key=lambda z: z["desde"])[:2]
    debajo = sorted([z for z in zonas if z["hasta"] < p], key=lambda z: -z["hasta"])[:2]
    dentro = [z for z in zonas if z["desde"] <= p <= z["hasta"]]
    rel = sorted(zonas, key=lambda z: (-z["toques"], abs(z["dist"])))[:tope]

    def limpia(z):
        d = {"precio": round(z["centro"], 2), "desde": round(z["desde"], 2), "hasta": round(z["hasta"], 2),
             "toques": z["toques"], "dist_pct": round(z["dist"], 2),
             "tipo": "techo" if z["tipos"] == {"techo"} else ("suelo" if z["tipos"] == {"suelo"} else "los dos")}
        if z.get("extremo"):
            d["extremo"] = "máximo 52 sem" if z["tipos"] == {"techo"} else "mínimo 52 sem"
        if z.get("ultimo") is not None:
            d["hace_velas"] = w - 1 - z["ultimo"]
        return d
    return {
        "precio": round(p, 2),
        "ema50": None if e50 is None else round(e50, 2),
        "ema200": None if e200 is None else round(e200, 2),
        "dist_ema50": None if e50 is None else round((p - e50) / e50 * 100, 2),
        "dist_ema200": None if e200 is None else round((p - e200) / e200 * 100, 2),
        "max52": round(max52, 2),
        "min52": round(min52, 2),
        "atr": round(a, 2),
        "resistencias": [limpia(z) for z in encima],
        "soportes": [limpia(z) for z in debajo],
        "en_zona": [limpia(z) for z in dentro],
        "mas_tocados": [limpia(z) for z in rel],
    }
