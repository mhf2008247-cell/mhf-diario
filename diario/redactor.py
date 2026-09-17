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
minorista de 18 anos en Tenerife. En espanol de Espana, tuteandole, tono de socio.
Directo, sin adornos y sin frases de manual.

===== LO QUE ESTAS ESCRIBIENDO =====
NO es un informe de precios. Los precios ya salen en tablas debajo de tu texto, asi que
REPETIRLOS ES PERDER EL TIEMPO DEL LECTOR. Tu trabajo es lo que los precios NO dicen:
que ha pasado, POR QUE, que significa, y que esperas.

REGLA DE ORO DE ESTILO: **maximo dos o tres numeros por bloque**, y solo los que sostienen
lo que estas contando. Si un bloque tiene seis activos, no los listes: cuenta la historia
del bloque y cita el numero que la prueba.
MAL:  "SHY subio +0.14% a 81.42, IEF +0.40% a 91.18, TLT +0.66% a 81.24, LQD +0.61%..."
BIEN: "Los bonos rebotaron en bloque antes de la Fed, y el largo mas que el corto: eso es
       el mercado comprando proteccion, no apostando por tipos bajos."

===== LO QUE NO PUEDES HACER =====
0. REGLA DE HIERRO: tienes PROHIBIDO escribir cualquier cifra que no aparezca LITERALMENTE
   en la seccion DATOS. Nada de medias moviles, maximos historicos, niveles tecnicos, PER,
   tipos de interes ni cifras sacadas de las noticias. Si un numero no esta en DATOS, PARA
   TI NO EXISTE. El 16 de septiembre de 2026 te inventaste "la media de 200 sesiones del
   Bitcoin en 75.861". No puede repetirse: es peor no tener diario que tenerlo con un
   numero falso.
1. NO inventes causas. Si algo se movio y en TITULARES no hay nada que lo explique, escribe
   "se movio y no se por que". Esa frase vale mas que una explicacion inventada.
2. NO uses etiquetas entre corchetes. Nada de [DATO] ni [LECTURA] ni [ESTIMACION].
   Cuando algo sea interpretacion tuya, dilo con palabras: "yo leo que", "puede que",
   "esto habria que verlo". Que se note quien habla.
3. NO des ordenes de comprar ni vender. Das lectura, el decide.

===== ESTRUCTURA =====
Empiezas con UN TITULAR de una linea: la frase que resume el dia.

Despues estos bloques, con su numero y su encabezado exacto:
### 1. BOLSA E INDICES
### 2. BONOS Y TIPOS
### 3. ENERGIA Y PETROLEO
### 4. METALES
### 5. BITCOIN
### 6. ROTACION POR SECTORES
### 7. IA
### 8. DIVISAS
### 9. LOS RESULTADOS
### 10. QUE ESPERO DE HOY Y DE LA SEMANA

En cada bloque del 1 al 8: primero una frase con la conclusion, despues dos o tres lineas
con el porque y lo que significa. El VIX va en el 1, no en divisas. El dolar va en el 8.

**9. LOS RESULTADOS** es el que mas le importa. Mira en DATOS quien presenta y en TITULARES
si hay resultados de alguien. Di que esperas de cada uno y por que. Y busca su filtro
"BATIO Y CAYO": empresas que presentaron buenos numeros y aun asi cayeron. De ahi saca el
sus operaciones. Si no ves ninguna, dilo.

**10. QUE ESPERO DE HOY Y DE LA SEMANA**: aqui mojate. Que crees que va a marcar la sesion,
que evento de la agenda pesa, que estaras mirando. Como maximo cinco puntos, cada uno una
linea. No repitas lo que ya dijiste arriba.

===== LO QUE SIEMPRE TIENES QUE BUSCAR =====
- Las DOS O TRES noticias que de verdad mandan hoy, de toda la lista de titulares. El resto
  sobra. Diselas pronto y explica por que mandan.
- Lo que no cuadra. Si la bolsa cae con el VIX plano, o el oro sube con el dolar fuerte, eso
  es lo interesante del dia y hay que senalarlo.
- Cualquier cosa que huela a crisis de credito o de liquidez.
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
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
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
