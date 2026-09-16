# -*- coding: utf-8 -*-
"""MHF DIARIO - redactor. Manda los datos y los titulares a Gemini y guarda la lectura.
NO inventa datos: el modelo solo puede usar los numeros que le llegan."""
import json, os, urllib.request, urllib.error
from datetime import datetime, timezone

CLAVE  = os.environ.get("GEMINI_KEY", "")
ENTRADA = "diario/datos.json"
SALIDA  = "diario/lectura.json"
BASE   = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
MODELOS = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite",
           "gemini-2.5-flash", "gemini-2.0-flash"]

REGLAS = """Eres el analista de mercados de MHF. Escribes para Maikol, trader minorista
de 18 anos en Tenerife, en espanol de Espana, tuteandole, tono de socio, directo y sin adornos.

LO QUE NO PUEDES HACER, y es lo mas importante:
1. NO inventes ni un solo numero. Solo puedes usar los numeros de la seccion DATOS.
   Si te falta un dato para decir algo, escribe: "no tengo ese dato".
2. NO inventes causas. Si un precio se movio y en TITULARES no hay nada que lo explique,
   escribe: "se movio y no se por que". Eso vale mas que una explicacion inventada.
3. NO des recomendaciones de comprar o vender. Das datos y lecturas, el decide.
4. Cada afirmacion con numero llevala marcada como DATO. Lo que sea interpretacion tuya,
   marcalo como LECTURA. Si es una suposicion, ESTIMACION y di el supuesto.

COMO ESCRIBES:
- Empiezas con UN TITULAR: la frase que resume el dia, una sola linea.
- Despues los bloques. En cada bloque, primero la conclusion, luego los numeros.
- Nada de relleno ni de frases de manual. Si un bloque no tiene nada que contar,
  una linea diciendo que esta tranquilo y a otra cosa.

BLOQUES OBLIGATORIOS, todos, en este orden:
1. BONOS Y TIPOS
2. ENERGIA Y GEOPOLITICA
3. METALES (oro, plata Y cobre)
4. CRIPTO (BTC, ETH, SOL)
5. BOLSA Y ROTACION POR SECTORES (di que sectores suben y cuales bajan, y que significa)
6. SEMIS E IA (incluye SMH y MRVL, que es una posicion suya)
7. DIVISAS (dolar, euro/dolar, dolar/yen)
8. VIX
9. EUROPA, JAPON Y HONG KONG
10. QUE MIRAR MANANA (maximo 5 puntos)

COSAS QUE LE IMPORTAN Y TIENES QUE BUSCAR EN LOS TITULARES:
- "BATIO Y CAYO": empresas que presentaron buenos resultados y aun asi cayeron.
  De ahi saca el sus operaciones. Si ves alguna en los titulares, dilo y destacalo.
- Cualquier cosa que suene a crisis de liquidez o de credito.
- Decisiones de bancos centrales.

DEVUELVES SOLO el texto del diario en Markdown. Nada mas."""


def resumen_datos(d):
    L = ["FECHA DE GENERACION: " + d["generado"], "", "DATOS (precios de cierre y cambio del dia):"]
    nom = {u["simbolo"]: (u["nombre"], u["bloque"]) for u in d["universo"]}
    por_bloque = {}
    for s, v in d["precios"].items():
        n, b = nom.get(s, (s, "otros"))
        por_bloque.setdefault(b, []).append((s, n, v))
    for b in sorted(por_bloque):
        L.append("  [%s]" % b.upper())
        for s, n, v in por_bloque[b]:
            L.append("    %-9s %-22s %12.4f   %+6.2f %%" % (s, n, v["precio"], v["cambio_pct"]))
    if d.get("fallos"):
        L.append("")
        L.append("SIN DATO HOY (no inventes estos): " + ", ".join(s for s, _ in d["fallos"]))
    L += ["", "TITULARES DE HOY:"]
    for t in d.get("titulares", []):
        L.append("  [%s] %s" % (t["fuente"], t["titular"]))
    return "\n".join(L)


def pregunta(modelo, texto):
    cuerpo = json.dumps({
        "systemInstruction": {"parts": [{"text": REGLAS}]},
        "contents": [{"role": "user", "parts": [{"text": texto}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 24000},
    }).encode("utf-8")
    req = urllib.request.Request(
        BASE % modelo + "?key=" + CLAVE, data=cuerpo,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    cand = (d.get("candidates") or [{}])[0]
    partes = (cand.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in partes).strip()


def main():
    d = json.load(open(ENTRADA, encoding="utf-8"))
    if not CLAVE:
        texto, modelo, err = "", "", "falta GEMINI_KEY"
    else:
        texto, modelo, err = "", "", ""
        for m in MODELOS:
            try:
                texto = pregunta(m, resumen_datos(d))
                if texto:
                    modelo = m
                    break
            except Exception as e:
                err = "%s -> %s: %s" % (m, type(e).__name__, str(e)[:120])
    out = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modelo": modelo,
        "texto": texto,
        "error": "" if texto else err,
    }
    json.dump(out, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("modelo: %s · %d caracteres · %s" % (modelo or "-", len(texto), err or "ok"))


if __name__ == "__main__":
    main()
