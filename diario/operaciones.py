# -*- coding: utf-8 -*-
"""MHF DIARIO - operaciones abiertas (7-oct-2026, pedido por él: "pon de primero lo del euro y GLE").
Los niveles se mantienen a mano en diario/operaciones.json. Aquí solo se baja el precio
de cada una (Yahoo, mismas velas que el portafolio) y se calcula a qué distancia está
de la entrada, del stop y de cada objetivo."""
import json, os
import portafolio

FICHERO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "operaciones.json")


def _situacion(op, px):
    """Dónde está el precio respecto al plan. Para un corto: arriba es malo, abajo es bueno."""
    e, s, t = op["entrada"], op["stop"], op["targets"]
    corto = op.get("lado", "corto") == "corto"
    if corto:
        if px >= s:
            return "baja", "Precio en el stop o por encima: plan invalidado"
        tocados = sum(1 for x in t if px <= x)
        if tocados:
            return "sube", "T%d alcanzado" % tocados
        if px >= e:
            return "ambar", "En zona de entrada"
        return "plano", "Esperando rebote a la entrada"
    if px <= s:
        return "baja", "Precio en el stop o por debajo: plan invalidado"
    tocados = sum(1 for x in t if px >= x)
    if tocados:
        return "sube", "T%d alcanzado" % tocados
    if px <= e:
        return "ambar", "En zona de entrada"
    return "plano", "Esperando retroceso a la entrada"


def estado():
    cfg = json.load(open(FICHERO, encoding="utf-8"))
    ops = [o for o in cfg.get("operaciones", []) if o.get("estado", "abierta") != "cerrada"]
    out, fallos = [], []
    for op in ops:
        r = dict(op)
        try:
            v = portafolio.velas(op["yahoo"])
            px, prev = v[-1][3], v[-2][3]
            r["precio"], r["cambio_pct"], r["fecha"] = px, (px / prev - 1) * 100, v[-1][0]
            r["dist"] = {k: (lv / px - 1) * 100 for k, lv in
                         [("entrada", op["entrada"]), ("stop", op["stop"])] +
                         [("T%d" % (i + 1), x) for i, x in enumerate(op["targets"])]}
            r["tono"], r["situacion"] = _situacion(op, px)
        except Exception as e:
            fallos.append(("operación " + op["nombre"], "%s: %s" % (type(e).__name__, str(e)[:60])))
        out.append(r)
    if not out:
        return None, fallos
    return {"titulo": cfg.get("titulo", "Operaciones abiertas"), "tesis": cfg.get("tesis", ""),
            "gestion": cfg.get("gestion", ""), "vigilar": cfg.get("vigilar", []),
            "operaciones": out}, fallos


if __name__ == "__main__":
    print(json.dumps(estado(), ensure_ascii=False, indent=1))
