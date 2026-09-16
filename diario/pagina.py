# -*- coding: utf-8 -*-
"""MHF DIARIO - construye docs/index.html a partir de datos.json y lectura.json."""
import json, os, re, html
from datetime import datetime, timezone

DATOS, LECTURA, SALIDA = "diario/datos.json", "diario/lectura.json", "docs/index.html"
LOGO = "diario/logo.txt"

ORDEN = [("bolsa","Bolsa"),("sectores","Rotacion por sectores"),("semis","Semis e IA"),
         ("bonos","Bonos y credito"),("metales","Metales"),("energia","Energia"),
         ("divisas","Divisas"),("cripto","Cripto"),("miedo","Miedo"),("mundo","Mundo")]

CSS = """
:root{--fondo:#0B0B0C;--panel:#141416;--linea:#26262A;--tinta:#F4F4F5;
--tinta2:#A1A1A6;--tinta3:#6B6B72;--rojo:#C8102E;--sube:#3FA66A;--baja:#D1495B}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--fondo);color:var(--tinta);
 font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased}
.envoltorio{max-width:1080px;margin:0 auto;padding:0 16px 72px}
header{border-bottom:1px solid var(--linea);padding:28px 0 22px;margin-bottom:28px;
 display:flex;align-items:center;gap:18px;flex-wrap:wrap}
header img{height:46px;width:auto;display:block}
.marca{font-weight:700;letter-spacing:.24em;font-size:13px;text-transform:uppercase}
.fecha{color:var(--tinta3);font-size:13px;margin-left:auto;letter-spacing:.04em}
h2{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--tinta2);
 font-weight:600;margin:34px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--linea)}
.titular{font-size:clamp(20px,3.4vw,28px);line-height:1.3;font-weight:600;
 border-left:3px solid var(--rojo);padding:4px 0 4px 16px;margin:6px 0 26px}
.rejilla{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(168px,1fr))}
.ficha{background:var(--panel);border:1px solid var(--linea);border-radius:10px;padding:12px 13px}
.ficha .n{font-size:11px;color:var(--tinta2);letter-spacing:.06em;text-transform:uppercase;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ficha .p{font-size:20px;font-weight:650;margin-top:5px;font-variant-numeric:tabular-nums}
.ficha .v{font-size:13px;margin-top:2px;font-variant-numeric:tabular-nums}
.sube{color:var(--sube)} .baja{color:var(--baja)} .plano{color:var(--tinta3)}
.lectura{background:var(--panel);border:1px solid var(--linea);border-radius:12px;
 padding:22px 24px;margin-top:6px}
.lectura h3{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--tinta2);
 margin:22px 0 8px} .lectura h3:first-child{margin-top:0}
.lectura p{margin:0 0 12px;color:#E4E4E7} .lectura ul{margin:0 0 12px 20px}
.lectura li{margin-bottom:5px;color:#E4E4E7}
.lectura strong{color:#fff}
.tit{list-style:none;display:grid;gap:7px}
.tit li{display:flex;gap:10px;align-items:baseline;font-size:14px;color:var(--tinta2);
 border-bottom:1px solid var(--linea);padding-bottom:7px}
.tit .f{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--tinta3);
 min-width:96px;flex-shrink:0}
footer{margin-top:44px;padding-top:18px;border-top:1px solid var(--linea);
 color:var(--tinta3);font-size:12.5px;line-height:1.7}
.aviso{background:var(--panel);border:1px solid var(--linea);border-left:3px solid var(--rojo);
 border-radius:8px;padding:13px 16px;color:var(--tinta2);font-size:13.5px;margin-top:14px}
.semaforo{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin:0 0 26px}
.luz{background:var(--panel);border:1px solid var(--linea);border-radius:10px;padding:11px 13px;
 display:flex;gap:10px;align-items:flex-start}
.bola{width:10px;height:10px;border-radius:50%;margin-top:5px;flex-shrink:0}
.v-ok{background:var(--sube)} .v-mal{background:var(--baja)} .v-nd{background:var(--tinta3)}
.luz .t{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--tinta2)}
.luz .d{display:block;font-size:13px;color:var(--tinta);margin-top:2px}
.lectura{font-size:16.5px}
.lectura h3{font-size:12.5px;letter-spacing:.16em;color:#fff;border-bottom:1px solid var(--linea);padding-bottom:7px}
.numeros{margin-top:10px}
@media(max-width:560px){.rejilla{grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}
 .lectura{padding:18px 16px}.tit li{flex-direction:column;gap:2px}}
"""


def md(t):
    """Markdown minimo: encabezados, negrita, listas, parrafos."""
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    fuera, lista = [], False
    for ln in t.split("\n"):
        s = ln.strip()
        if not s:
            if lista: fuera.append("</ul>"); lista = False
            continue
        if s.startswith("#"):
            if lista: fuera.append("</ul>"); lista = False
            fuera.append("<h3>%s</h3>" % s.lstrip("# ").strip())
        elif s[:2] in ("- ", "* ") or re.match(r"^\d+\.\s", s):
            if not lista: fuera.append("<ul>"); lista = True
            fuera.append("<li>%s</li>" % re.sub(r"^(?:[-*]\s|\d+\.\s)", "", s))
        else:
            if lista: fuera.append("</ul>"); lista = False
            fuera.append("<p>%s</p>" % s)
    if lista: fuera.append("</ul>")
    return "\n".join(fuera)


def semaforo(px):
    """Descriptivo, NO es una senal de trading. Sale de los precios de HOY."""
    def c(s):
        v = px.get(s)
        return None if not v else v["cambio_pct"]
    L = []
    b = [c(x) for x in ("SPY", "QQQ", "DIA", "IWM") if c(x) is not None]
    if b:
        m = sum(b) / len(b)
        L.append(("Bolsa EEUU", "ok" if m > 0 else "mal",
                  "media %+.2f %% en los cuatro indices" % m))
    vix = c("VIXY")
    if vix is not None:
        L.append(("Miedo", "mal" if vix > 3 else "ok",
                  "la volatilidad %s %+.2f %%" % ("sube" if vix > 0 else "baja", vix)))
    hyg, ief = c("HYG"), c("IEF")
    if hyg is not None and ief is not None:
        d = hyg - ief
        L.append(("Credito", "mal" if d < -0.3 else "ok",
                  "la deuda basura va %+.2f %% contra el bono" % d))
    gld, tlt, spy = c("GLD"), c("TLT"), c("SPY")
    if None not in (gld, tlt, spy):
        huida = gld > spy and tlt > spy
        L.append(("Refugio", "mal" if huida else "ok",
                  "oro y bono %s a la bolsa" % ("ganan" if huida else "no ganan")))
    uup = c("UUP")
    if uup is not None:
        L.append(("Dolar", "mal" if uup > 0.4 else "ok",
                  "%s %+.2f %%" % ("se fortalece" if uup > 0 else "se afloja", uup)))
    return L


def ficha(simbolo, nombre, v):
    c = v["cambio_pct"]
    cls = "sube" if c > 0.05 else ("baja" if c < -0.05 else "plano")
    flecha = "▲" if c > 0.05 else ("▼" if c < -0.05 else "—")
    p = v["precio"]
    fmt = "%.4f" % p if p < 10 else ("%.2f" % p)
    return ('<div class="ficha"><div class="n">%s</div><div class="p">%s</div>'
            '<div class="v %s">%s %+.2f %%</div></div>'
            % (html.escape(nombre), fmt, cls, flecha, c))


def main():
    d = json.load(open(DATOS, encoding="utf-8"))
    try:
        L = json.load(open(LECTURA, encoding="utf-8"))
    except Exception:
        L = {"texto": "", "error": "sin lectura", "modelo": ""}

    nom = {u["simbolo"]: (u["nombre"], u["bloque"]) for u in d["universo"]}
    grupos = {}
    for s, v in d["precios"].items():
        n, b = nom.get(s, (s, "otros"))
        grupos.setdefault(b, []).append((s, n, v))

    texto = L.get("texto") or ""
    titular, cuerpo = "", texto
    for ln in texto.split("\n"):
        if ln.strip():
            titular = re.sub(r"^#+\s*|\*\*", "", ln.strip())
            cuerpo = texto.replace(ln, "", 1)
            break

    logo = open(LOGO).read().strip() if os.path.exists(LOGO) else ""
    P = ['<!doctype html><html lang="es"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>MHF Diario</title><style>%s</style></head><body>' % CSS,
         '<div class="envoltorio"><header>']
    if logo:
        P.append('<img src="%s" alt="MHF">' % logo)
    P.append('<span class="marca">Diario</span>')
    P.append('<span class="fecha">%s UTC</span></header>'
             % d["generado"].replace("T", " ")[:16])

    if titular:
        P.append('<div class="titular">%s</div>' % html.escape(titular))

    luces = semaforo(d["precios"])
    if luces:
        P.append("<h2>Como esta el dia</h2><div class='semaforo'>")
        for t, e, txt in luces:
            P.append("<div class='luz'><span class='bola v-%s'></span>"
                     "<span><span class='t'>%s</span><span class='d'>%s</span></span></div>"
                     % (e, html.escape(t), html.escape(txt)))
        P.append("</div>")

    if cuerpo.strip():
        P.append("<h2>El diario</h2><div class='lectura'>%s</div>" % md(cuerpo))
    elif L.get("error"):
        P.append("<h2>El diario</h2><div class='aviso'>Hoy no hay lectura: %s</div>"
                 % html.escape(L["error"]))

    P.append("<h2>Los numeros</h2><div class='numeros'>")
    for clave, rotulo in ORDEN:
        if clave not in grupos:
            continue
        P.append("<h2>%s</h2><div class='rejilla'>" % rotulo)
        for s, n, v in sorted(grupos[clave], key=lambda x: -abs(x[2]["cambio_pct"])):
            P.append(ficha(s, n, v))
        P.append("</div>")
    P.append("</div>")

    if d.get("titulares"):
        P.append("<h2>Las noticias del dia</h2><ul class='tit'>")
        for t in d["titulares"]:
            P.append("<li><span class='f'>%s</span><span>%s</span></li>"
                     % (html.escape(t["fuente"]), html.escape(t["titular"])))
        P.append("</ul>")

    P.append('<div class="aviso">Los precios son <strong>DATO</strong>: cierres de Twelve Data. '
             'La lectura la escribe un modelo a partir de esos numeros y de los titulares de arriba, '
             'y <strong>puede equivocarse</strong>. No es consejo de inversion: '
             'son datos para que decidas tu.</div>')
    P.append('<footer>MHF · Diario automatico · precios %d de %d · fallos %d%s<br>'
             'Se genera solo cada dia. No sustituye tu criterio.</footer>'
             % (len(d["precios"]), len(d["universo"]), len(d.get("fallos") or []),
                (" · modelo " + L["modelo"]) if L.get("modelo") else ""))
    P.append("</div></body></html>")

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    open(SALIDA, "w", encoding="utf-8").write("\n".join(P))
    print("escrito %s (%d bytes)" % (SALIDA, os.path.getsize(SALIDA)))


if __name__ == "__main__":
    main()
