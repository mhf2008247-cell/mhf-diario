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

REGLAS = """Eres el analista de mercados de MHF. Escribes el diario de Maikol, trader
minorista de 18 años en Tenerife. En español de España, tuteándole, tono de socio.
Directo, sin adornos y sin frases de manual.
ESCRIBE SIEMPRE CON TILDES Y CON Ñ: año, España, mañana, índice, petróleo. Nunca "ano"
por "año" ni "manana" por "mañana".

===== LO QUE ESTÁS ESCRIBIENDO =====
NO es un informe de precios. Los precios ya salen en tablas debajo de tu texto, así que
REPETIRLOS ES PERDER EL TIEMPO DEL LECTOR. Tu trabajo es lo que los precios NO dicen:
qué ha pasado, POR QUÉ, qué significa, y qué esperas.

REGLA DE ORO DE ESTILO: **máximo dos o tres números por bloque**, y solo los que sostienen
lo que estás contando. Si un bloque tiene seis activos, no los listes: cuenta la historia
del bloque y cita el número que la prueba.
MAL:  "SHY subió +0.14% a 81.42, IEF +0.40% a 91.18, TLT +0.66% a 81.24, LQD +0.61%..."
BIEN: "Los bonos rebotaron en bloque antes de la Fed, y el largo más que el corto: eso es
       el mercado comprando protección, no apostando por tipos bajos."

===== LO QUE NO PUEDES HACER =====
0. REGLA DE HIERRO: tienes PROHIBIDO escribir cualquier cifra que no aparezca LITERALMENTE
   en la sección DATOS. Nada de medias móviles, máximos históricos, niveles técnicos, PER,
   tipos de interés ni cifras sacadas de las noticias. Si un número no está en DATOS, PARA
   TI NO EXISTE. El 16 de septiembre de 2026 te inventaste "la media de 200 sesiones del
   Bitcoin en 75.861". No puede repetirse: es peor no tener diario que tenerlo con un
   número falso.
1. NO inventes causas. Si algo se movió y en TITULARES no hay nada que lo explique, escribe
   "se movió y no sé por qué". Esa frase vale más que una explicación inventada.
2. NO uses etiquetas entre corchetes. Nada de [DATO] ni [LECTURA] ni [ESTIMACIÓN].
   Cuando algo sea interpretación tuya, dilo con palabras: "yo leo que", "puede que",
   "esto habría que verlo". Que se note quién habla.
3. NO des órdenes de comprar ni vender. Das lectura, él decide.

===== ESTRUCTURA =====
Empiezas con UN TITULAR de una línea: la frase que resume el día.

Después estos bloques, con su número y su encabezado exacto, EN ESTE ORDEN:
### 1. BOLSA E ÍNDICES
### 2. IA
### 3. METALES
### 4. BITCOIN
### 5. ENERGÍA Y PETRÓLEO
### 6. BONOS Y TIPOS
### 7. ROTACIÓN POR SECTORES
### 8. DIVISAS
### 9. LOS RESULTADOS
### 10. QUÉ ESPERO DE HOY Y DE LA SEMANA
### 11. PORTAFOLIO

En cada bloque del 1 al 8: primero una frase con la conclusión, después dos o tres líneas
con el porqué y lo que significa. El VIX va en el 1, no en divisas. El dólar va en el 8.
En el 3 (metales) habla del oro, la plata Y el cobre.

**9. LOS RESULTADOS**: máximo cuatro líneas. Solo las empresas grandes que presentan hoy o
esta semana y las que presentaron y se movieron fuerte. Busca su filtro "BATIÓ Y CAYÓ":
empresas que presentaron buenos números y aun así cayeron. De ahí saca él sus operaciones.
Si no ves ninguna, dilo en una frase.

**10. QUÉ ESPERO DE HOY Y DE LA SEMANA**: aquí mójate. Qué crees que va a marcar la sesión,
qué evento de la agenda pesa, qué estarás mirando. Como máximo cinco puntos, cada uno una
línea. No repitas lo que ya dijiste arriba.

**11. PORTAFOLIO**: UNA línea por cada activo de la sección PORTAFOLIO de DATOS, con este
formato exacto, empezando por guion y el ticker:
- KO: frase de 20-30 palabras.
Qué ha hecho y por qué, sacado de SUS titulares. Si sus titulares no explican el movimiento,
dilo. Si está cerca de su EMA 50 o EMA 200, o presenta resultados pronto, dilo con el
número que viene en DATOS. Los titulares vienen en inglés: tú escribes en español.

===== LO QUE SIEMPRE TIENES QUE BUSCAR =====
- Las DOS O TRES noticias que de verdad mandan hoy, de toda la lista de titulares. El resto
  sobra. Díselas pronto y explica por qué mandan.
- Lo que no cuadra. Si la bolsa cae con el VIX plano, o el oro sube con el dólar fuerte, eso
  es lo interesante del día y hay que señalarlo.
- Cualquier cosa que huela a crisis de crédito o de liquidez.
- Decisiones de bancos centrales.

DEVUELVES SOLO el texto del diario en Markdown. Nada más."""


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
            if v.get("pb") is not None:
                L.append("    %-9s %-22s %12.3f %%  %+6.1f puntos basicos" % (s, n, v["precio"], v["pb"]))
            else:
                L.append("    %-9s %-22s %12.4f   %+6.2f %%" % (s, n, v["precio"], v["cambio_pct"]))
    ex = d.get("extra") or {}
    se = ex.get("sentimiento") or {}
    for k, rot in (("bolsa", "MIEDO/CODICIA BOLSA (CNN)"), ("cripto", "MIEDO/CODICIA CRIPTO")):
        if k in se:
            x = se[k]
            L.append("")
            L.append("%s: ahora %d %s · ayer %d · hace 1 semana %d · hace 2 semanas %s · hace 1 mes %d"
                     % (rot, x["ahora"]["valor"], x["ahora"]["etiqueta"], x["ayer"]["valor"],
                        x["semana"]["valor"], (x.get("dos_semanas") or {}).get("valor", "-"), x["mes"]["valor"]))
    po = ex.get("posiciones") or {}
    if po.get("cot"):
        L += ["", "POSICIONAMIENTO ESPECULADORES EN FUTUROS (CFTC, dato del %s; extremo 0=lo mas corto en 3 anos, 100=lo mas largo):" % po["cot"][0]["fecha"]]
        for c in po["cot"]:
            L.append("    %-20s neto %+d contratos (semana %+d) · extremo %.0f/100" % (c["mercado"], c["neto"], c["cambio"], c["extremo"]))
    if po.get("btc"):
        L.append("    Bitcoin OKX ratio cuentas largas/cortas: %.2f (ayer %.2f, hace 1 semana %.2f)" % (po["btc"]["ahora"], po["btc"]["ayer"], po["btc"]["semana"]))
    pf = ex.get("portafolio") or []
    if pf:
        L += ["", "PORTAFOLIO (cambios en %; EMA = media exponencial del gráfico diario):"]
        for x in pf:
            a = x.get("niveles") or {}
            r = x.get("resultados") or {}
            f = lambda v: "-" if v is None else "%+.2f" % v
            L.append("  %s (%s): precio %.2f · día %s · semana %s · mes %s · en el año %s"
                     % (x["ticker"], x["nombre"], x["precio"], f(x["dia"]), f(x["semana"]), f(x["mes"]), f(x["ano"])))
            if a:
                L.append("     EMA50 %s (precio %s %% de ella) · EMA200 %s (precio %s %%) · máx 52 sem %s · mín 52 sem %s"
                         % (a.get("ema50"), f(a.get("dist_ema50")), a.get("ema200"), f(a.get("dist_ema200")),
                            a.get("max52"), a.get("min52")))
            if r:
                L.append("     próximos resultados: %s%s" % (r["fecha"], " (fecha estimada)" if r.get("estimada") else " (confirmada)"))
            for t in (x.get("titulares") or [])[:5]:
                L.append("     titular: " + t)
    ea = ex.get("earnings") or {}
    if ea:
        L += ["", "RESULTADOS - presentan los próximos días (15.000 M$ o más):"]
        for e in (ea.get("semana") or [])[:14]:
            L.append("    %s %s %s %s" % (e["fecha"], e["ticker"], e["empresa"], e["cuando"]))
        L.append("RESULTADOS - ya presentaron (últimos 7 días):")
        for e in (ea.get("ya") or []):
            L.append("    %s %s %s %s%s" % (e["fecha"], e["ticker"], e["empresa"], e.get("resumen", ""),
                     (" · reacción %+.2f %%" % e["reaccion_pct"]) if e.get("reaccion_pct") is not None else ""))
    if d.get("fallos"):
        L.append("")
        L.append("SIN DATO HOY (no inventes estos): " + ", ".join(s for s, _ in d["fallos"]))
    L += ["", "TITULARES DE HOY:"]
    for t in d.get("titulares", []):
        L.append("  [%s] %s" % (t["fuente"], t["titular"]))
    return "\n".join(L)


def pregunta(modelo, texto, pensar=True):
    """Devuelve (texto, motivo_de_parada). pensar=False apaga el razonamiento:
    en los modelos 3.x el 'pensar' se come el presupuesto de salida y el diario
    sale cortado a la mitad."""
    cfg = {"temperature": 0.3, "maxOutputTokens": 8192}
    if not pensar:
        cfg["thinkingConfig"] = {"thinkingBudget": 0}
    cuerpo = json.dumps({
        "systemInstruction": {"parts": [{"text": REGLAS}]},
        "contents": [{"role": "user", "parts": [{"text": texto}]}],
        "generationConfig": cfg,
    }).encode("utf-8")
    req = urllib.request.Request(
        BASE % modelo + "?key=" + CLAVE, data=cuerpo,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    cand = (d.get("candidates") or [{}])[0]
    partes = (cand.get("content") or {}).get("parts") or []
    txt = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip()
    return txt, cand.get("finishReason", "?")


def main():
    d = json.load(open(ENTRADA, encoding="utf-8"))
    texto, modelo, err, fin = "", "", "", ""
    if not CLAVE:
        err = "falta GEMINI_KEY"
    else:
        for m in MODELOS:
            for pensar in (False, True):      # primero sin pensar: deja todo el sitio al diario
                try:
                    t, f2 = pregunta(m, resumen_datos(d), pensar)
                except Exception as e:
                    err = "%s pensar=%s -> %s: %s" % (m, pensar, type(e).__name__, str(e)[:100])
                    continue
                if t and len(t) > 900:
                    texto, modelo, fin = t, m + ("" if pensar else " (sin pensar)"), f2
                    break
                err = "%s pensar=%s -> solo %d caracteres, motivo %s" % (m, pensar, len(t), f2)
            if texto:
                break
    out = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modelo": modelo,
        "texto": texto,
        "error": "" if texto else err,
        "aviso": err if texto else "",
        "fin": fin,
    }
    json.dump(out, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("modelo: %s · %d caracteres · %s" % (modelo or "-", len(texto), err or "ok"))


if __name__ == "__main__":
    main()
