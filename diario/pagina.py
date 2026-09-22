# -*- coding: utf-8 -*-
"""MHF DIARIO - construye docs/index.html. Tarjetas numeradas, todo en negro."""
import json, os, re, html, datetime as dt

DATOS, LECTURA, SALIDA = "diario/datos.json", "diario/lectura.json", "docs/index.html"
LOGO = "diario/logo.txt"

# bloque -> (numero, rotulo, icono, simbolos)
BLOQUES = [
    ("bolsa",    "Bolsa e indices",          "▲"),
    ("bonos",    "Bonos y tipos",            "▦"),
    ("energia",  "Energia y petroleo",       "◉"),
    ("metales",  "Metales",                  "◆"),
    ("cripto",   "Bitcoin",                  "₿"),
    ("sectores", "Rotacion por sectores",    "▤"),
    ("ia",       "IA",                       "⬢"),
    ("divisas",  "Divisas",                  "⇄"),
]

CSS = """
:root{--fondo:#09090A;--panel:#131315;--panel2:#1A1A1D;--linea:#26262B;--tinta:#F5F5F6;
--tinta2:#9C9CA4;--tinta3:#63636B;--rojo:#C8102E;--sube:#3FA66A;--baja:#D1495B;--ambar:#D99A2B}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--fondo);color:var(--tinta);-webkit-font-smoothing:antialiased;
 font:15.5px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 padding-bottom:env(safe-area-inset-bottom)}
.env{max-width:780px;margin:0 auto;padding:0 14px 60px}
header{display:flex;align-items:center;gap:14px;padding:22px 0 16px}
header img{height:38px;width:auto;border-radius:6px}
.marca{font-size:11px;letter-spacing:.26em;font-weight:700;text-transform:uppercase;color:var(--tinta2);line-height:1.5}
.marca b{display:block;color:var(--tinta);font-size:13px;letter-spacing:.2em}
.fecha{margin-left:auto;font-size:12px;color:var(--tinta3);text-align:right}

.sem{border-radius:14px;padding:16px 18px;margin:4px 0 18px;border:1px solid var(--linea);background:var(--panel)}
.sem.rojo{border-color:rgba(200,16,46,.55);background:linear-gradient(180deg,rgba(200,16,46,.14),var(--panel))}
.sem.amarillo{border-color:rgba(217,154,43,.5);background:linear-gradient(180deg,rgba(217,154,43,.11),var(--panel))}
.sem.verde{border-color:rgba(63,166,106,.45);background:linear-gradient(180deg,rgba(63,166,106,.09),var(--panel))}
.sem .fila{display:flex;align-items:center;gap:11px}
.sem .bola{width:13px;height:13px;border-radius:50%;flex-shrink:0}
.rojo .bola{background:var(--rojo);box-shadow:0 0 0 5px rgba(200,16,46,.16)}
.amarillo .bola{background:var(--ambar);box-shadow:0 0 0 5px rgba(217,154,43,.14)}
.verde .bola{background:var(--sube);box-shadow:0 0 0 5px rgba(63,166,106,.12)}
.sem h1{font-size:15px;letter-spacing:.14em;text-transform:uppercase;font-weight:700}
.sem ul{list-style:none;margin:11px 0 0;padding:0;display:grid;gap:6px}
.sem li{font-size:14px;color:var(--tinta2);padding-left:15px;position:relative}
.sem li:before{content:"";position:absolute;left:0;top:8px;width:5px;height:5px;border-radius:50%;background:var(--tinta3)}

.titular{font-size:clamp(19px,3.6vw,25px);line-height:1.32;font-weight:650;
 border-left:3px solid var(--rojo);padding:3px 0 3px 15px;margin:0 0 22px}

.tarjeta{background:var(--panel);border:1px solid var(--linea);border-radius:14px;
 padding:15px 16px;margin-bottom:11px}
.cab{display:flex;align-items:center;gap:10px;margin-bottom:4px}
.num{width:25px;height:25px;border-radius:7px;background:var(--panel2);border:1px solid var(--linea);
 display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:var(--tinta2);flex-shrink:0}
.ico{font-size:15px;color:var(--tinta2)}
.cab h2{font-size:16px;font-weight:650;letter-spacing:.005em}
.resumen{font-size:14.5px;color:var(--tinta);font-weight:600;margin:6px 0 12px}

table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th{font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--tinta3);
 font-weight:600;text-align:right;padding:0 0 7px}
th:first-child{text-align:left}
td{padding:8px 0;border-top:1px solid var(--linea);font-size:14px;text-align:right}
td:first-child{text-align:left}
.tk{font-weight:650} .dsc{color:var(--tinta3);font-size:11.5px;display:block;margin-top:1px}
.sube{color:var(--sube)} .baja{color:var(--baja)} .plano{color:var(--tinta3)}

.lec{background:var(--panel2);border-radius:10px;padding:12px 14px;margin-top:12px;
 border-left:2px solid var(--linea)}
.lec .t{font-size:9.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--tinta2);
 font-weight:700;margin-bottom:6px}
.lec p{font-size:14px;color:#DEDEE2;margin:0 0 7px}.lec p:last-child{margin:0}

.niv{margin-top:12px;border-top:1px solid var(--linea);padding-top:11px}
.niv .h{font-size:9.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--tinta2);font-weight:700;margin-bottom:8px}
.niv .g{display:grid;grid-template-columns:1fr 1fr;gap:7px}
.niv .c{background:var(--panel2);border-radius:8px;padding:8px 10px}
.niv .c .k{font-size:9.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--tinta3)}
.niv .c .v{font-size:15px;font-weight:650;margin-top:2px;font-variant-numeric:tabular-nums}
.niv .c .p{font-size:11.5px;margin-top:1px}
.niv .lst{margin-top:9px;display:grid;gap:5px}
.niv .lst div{display:flex;justify-content:space-between;font-size:13px;font-variant-numeric:tabular-nums}
.niv .lst .e{color:var(--tinta3);font-size:11.5px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n.h2b{font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--tinta2);font-weight:700;margin-bottom:5px}\n@media(max-width:430px){.g2{grid-template-columns:1fr;gap:10px}}\n.ev{display:grid;gap:8px}
.ev .it{display:flex;gap:11px;align-items:flex-start;padding:9px 0;border-top:1px solid var(--linea)}
.ev .it:first-child{border-top:0}
.ev .d{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--tinta3);
 min-width:62px;flex-shrink:0;padding-top:2px}
.ev .p{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:6px}
.p-rojo{background:var(--rojo)}.p-amarillo{background:var(--ambar)}.p-verde{background:var(--sube)}
.ev .q{font-size:14px;display:block}.ev .n{display:block;font-size:12.5px;color:var(--tinta3);margin-top:3px;line-height:1.45}

.tit{list-style:none;display:grid;gap:8px}
.tit li{font-size:13.5px;color:var(--tinta2);border-top:1px solid var(--linea);padding-top:8px}
.tit li:first-child{border-top:0}
.tit .f{font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--tinta3);display:block;margin-bottom:2px}
.byc{border-left:2px solid var(--rojo)}
.aviso{font-size:13px;color:var(--tinta2);background:var(--panel);border:1px solid var(--linea);
 border-left:3px solid var(--rojo);border-radius:10px;padding:12px 14px;margin-top:16px}
.viejo{border-left-color:var(--ambar);margin-top:10px}
.fg{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:430px){.fg{grid-template-columns:1fr}}
.fg .caja{background:var(--panel2);border-radius:10px;padding:12px 13px}
.fg .big{display:flex;align-items:baseline;gap:9px;margin:4px 0 8px}
.fg .big b{font-size:30px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}
.fg .big span{font-size:13px;font-weight:650}
.barra{height:6px;border-radius:3px;position:relative;margin:2px 0 10px;
 background:linear-gradient(90deg,#D1495B,#D99A2B 45%,#9C9CA4 50%,#3FA66A 60%,#2E8B57)}
.barra i{position:absolute;top:-4px;width:3px;height:14px;border-radius:2px;background:#F5F5F6;transform:translateX(-50%)}
.fg .r{display:flex;justify-content:space-between;font-size:13px;padding:5px 0;border-top:1px solid var(--linea);font-variant-numeric:tabular-nums}
.fg .r .e{color:var(--tinta3)}
.ext{display:inline-block;width:54px;height:5px;border-radius:3px;background:var(--linea);position:relative;vertical-align:middle;margin-left:6px}
.ext i{position:absolute;top:-3px;width:3px;height:11px;border-radius:2px;background:var(--tinta);transform:translateX(-50%)}
.nota{font-size:12px;color:var(--tinta3);margin-top:10px;line-height:1.5}
.miedo{color:var(--baja)}.neutral{color:var(--ambar)}.codicia{color:var(--sube)}
footer{margin-top:26px;padding-top:15px;border-top:1px solid var(--linea);
 color:var(--tinta3);font-size:11.5px;line-height:1.7}
@media(max-width:480px){.env{padding:0 11px 52px}.tarjeta{padding:13px 13px}
 .ev .d{min-width:54px}td,.lec p{font-size:13.5px}}
"""


def fnum(p):
    if p < 10:
        return "%.4f" % p
    return "{:,.2f}".format(p).replace(",", "@").replace(".", ",").replace("@", ".")


def cambio(c):
    cl = "sube" if c > 0.05 else ("baja" if c < -0.05 else "plano")
    fl = "▲" if c > 0.05 else ("▼" if c < -0.05 else "—")
    return '<td class="%s">%+.2f %%</td><td class="%s">%s</td>' % (cl, c, cl, fl)


ET = re.compile(r"[\[`(]*\s*\b(DATO|Dato|DATOS|LECTURA|Lectura|ESTIMACION|Estimacion|Estimación)\b\s*[\]`)]*\s*:?", re.I)


def sin_etiquetas(t):
    """Quita [DATO], `[LECTURA]`, DATO:, (ESTIMACION)... en cualquier forma."""
    t = ET.sub(" ", t)
    return re.sub(r"\s{2,}", " ", t).strip(" -·:")


def trozos(texto):
    """Parte la lectura de Gemini en {numero: [parrafos]} usando sus encabezados."""
    out, act = {}, None
    for ln in (texto or "").split("\n"):
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^#+\s*(\d+)[\.\)]?\s+(.*)$", s)
        if m:
            act = int(m.group(1)); out[act] = []
            continue
        if s.startswith("#"):
            act = None; continue
        if act:
            s = sin_etiquetas(s)
            if not s: continue
            out[act].append(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(s)))
    return out




def nota_oro(px):
    """Solo con los movimientos de HOY. Un dia no define un regimen y se dice."""
    def c(k):
        v = px.get(k); return None if not v else v["cambio_pct"]
    oro = c("ORO") if c("ORO") is not None else c("GLD")
    bolsa = c("SPX") if c("SPX") is not None else c("SPY")
    dol = c("DXY") if c("DXY") is not None else c("UUP")
    if oro is None or bolsa is None:
        return None
    if oro > 0.1 and bolsa < -0.1:
        t = "Hoy SI se comporta como refugio: el oro sube %+.2f %% con la bolsa %+.2f %%." % (oro, bolsa)
    elif oro < -0.1 and bolsa < -0.1:
        t = "Hoy NO es refugio: cae %+.2f %% con la bolsa tambien cayendo %+.2f %%. Cuando pasa esto suele mandar el dolar o los tipos reales, no el miedo." % (oro, bolsa)
    elif oro > 0.1 and bolsa > 0.1:
        t = "Hoy sube %+.2f %% CON la bolsa (%+.2f %%). Eso no es refugio: es liquidez o inflacion, los dos suben a la vez." % (oro, bolsa)
    else:
        t = "Hoy va plano (%+.2f %%) con la bolsa en %+.2f %%. Nada que leer." % (oro, bolsa)
    if dol is not None:
        t += " El dolar %+.2f %%." % dol
    return t + " Es un dia suelto, no un regimen."


def celda_cambio(v):
    """Rentabilidades de bonos en puntos basicos; todo lo demas en %."""
    if v.get("pb") is not None:
        c = v["pb"]
        cl = "sube" if c > 0.05 else ("baja" if c < -0.05 else "plano")
        fl = "▲" if c > 0.05 else ("▼" if c < -0.05 else "—")
        return '<td class="%s">%+.1f pb</td><td class="%s">%s</td>' % (cl, c, cl, fl)
    return cambio(v["cambio_pct"])


def tono(v):
    return "miedo" if v < 45 else ("neutral" if v <= 55 else "codicia")


def tarjeta_sentimiento(se):
    P = ['<div class="tarjeta"><div class="cab"><span class="num">☯</span>'
         '<span class="ico">◐</span><h2>Miedo y codicia</h2></div><div class="fg">']
    for k, rot in (("bolsa", "Bolsa EE.UU. (CNN)"), ("cripto", "Cripto")):
        x = se.get(k)
        if not x:
            continue
        a = x["ahora"]
        P.append('<div class="caja"><div class="h2b">%s</div>'
                 '<div class="big"><b class="%s">%d</b><span class="%s">%s</span></div>'
                 '<div class="barra"><i style="left:%d%%"></i></div>'
                 % (rot, tono(a["valor"]), a["valor"], tono(a["valor"]), a["etiqueta"], a["valor"]))
        for kk, rr in (("ayer", "Ayer"), ("semana", "Hace una semana"), ("mes", "Hace un mes"), ("ano", "Hace un ano")):
            if kk in x:
                P.append('<div class="r"><span class="e">%s</span><span class="%s">%d · %s</span></div>'
                         % (rr, tono(x[kk]["valor"]), x[kk]["valor"], x[kk]["etiqueta"]))
        P.append("</div>")
    P.append('</div><div class="nota">0 = miedo extremo, 100 = codicia extrema. '
             'Mide el animo de la gente, no dice hacia donde va el precio.</div></div>')
    return "".join(P)


def tarjeta_posiciones(po):
    P = ['<div class="tarjeta"><div class="cab"><span class="num">⚖</span>'
         '<span class="ico">▥</span><h2>Posicionamiento en futuros</h2></div>']
    cot = po.get("cot") or []
    if cot:
        P.append('<div class="resumen">Especuladores grandes (CFTC) · datos del %s</div>' % cot[0]["fecha"])
        P.append('<table><tr><th>Mercado</th><th>Neto</th><th>Semana</th><th>Extremo 3 a</th></tr>')
        for c in sorted(cot, key=lambda z: -abs(z["extremo"] - 50)):
            cl = "sube" if c["neto"] > 0 else "baja"
            cc = "sube" if c["cambio"] > 0 else ("baja" if c["cambio"] < 0 else "plano")
            P.append('<tr><td><span class="tk">%s</span><span class="dsc">%s</span></td>'
                     '<td class="%s">%s</td><td class="%s">%s</td>'
                     '<td>%d<span class="ext"><i style="left:%d%%"></i></span></td></tr>'
                     % (html.escape(c["mercado"]), "largos" if c["neto"] > 0 else "cortos",
                        cl, "{:+,}".format(c["neto"]).replace(",", "."),
                        cc, "{:+,}".format(c["cambio"]).replace(",", "."),
                        round(c["extremo"]), max(0, min(100, c["extremo"]))))
        P.append("</table>")
    b = po.get("btc")
    if b:
        P.append('<div class="lec"><div class="t">Bitcoin · cuentas largas / cortas (OKX)</div>'
                 '<p>Ahora <strong>%.2f</strong> · ayer %.2f · hace una semana %.2f. '
                 'Por encima de 1 hay mas cuentas en largo que en corto.</p></div>'
                 % (b["ahora"], b["ayer"], b["semana"]))
    P.append('<div class="nota">Neto = contratos largos menos cortos de los especuladores. '
             'Extremo: 0 = lo mas cortos que han estado en 3 anos, 100 = lo mas largos. '
             'El informe sale los viernes con datos del martes. Un extremo por si solo no es senal de entrada.</div></div>')
    return "".join(P)


def ganadores(px, nom, n=5):
    """Los que mas suben y los que mas bajan del dia, de todo el panel (sin bonos: van en pb)."""
    L = [(s, nom.get(s, (s, ""))[0], v["cambio_pct"]) for s, v in px.items() if v.get("pb") is None]
    L.sort(key=lambda x: -x[2])
    return L[:n], L[-n:][::-1]


def bloque_niveles(t, a):
    """Tarjeta de niveles de una empresa. Todo calculado de sus velas diarias."""
    def cl(x):
        return "sube" if x > 0 else ("baja" if x < 0 else "plano")
    P = ['<div class="niv"><div class="h">%s &middot; niveles del grafico diario</div>' % html.escape(t)]
    P.append('<div class="g">')
    for k, val, dist in (("EMA 50", a.get("ema50"), a.get("dist_ema50")),
                         ("EMA 200", a.get("ema200"), a.get("dist_ema200"))):
        if val is None:
            continue
        P.append('<div class="c"><div class="k">%s</div><div class="v">%s</div>'
                 '<div class="p %s">el precio esta %+.2f %%</div></div>'
                 % (k, fnum(val), cl(dist), dist))
    P.append('<div class="c"><div class="k">Maximo 52 sem</div><div class="v">%s</div></div>' % fnum(a["max52"]))
    P.append('<div class="c"><div class="k">Minimo 52 sem</div><div class="v">%s</div></div>' % fnum(a["min52"]))
    P.append("</div>")
    for rot, lst in (("Por encima", a.get("resistencias") or []),
                     ("Por debajo", a.get("soportes") or [])):
        if not lst:
            continue
        P.append('<div class="lst"><div><span class="e">%s</span></div>' % rot)
        for z in lst:
            P.append('<div><span>%s</span><span class="e">%+.1f %% &middot; se giro %d veces</span></div>'
                     % (fnum(z["precio"]), z["dist_pct"], z["toques"]))
        P.append("</div>")
    P.append("</div>")
    return "".join(P)


def main():
    d = json.load(open(DATOS, encoding="utf-8"))
    try:
        L = json.load(open(LECTURA, encoding="utf-8"))
    except Exception:
        L = {"texto": "", "error": "sin lectura", "modelo": ""}
    extra = d.get("extra") or {}
    sem = extra.get("semaforo") or {}
    ear = extra.get("earnings") or {}
    cal = extra.get("semana") or []

    nom = {u["simbolo"]: (u["nombre"], u["bloque"]) for u in d["universo"]}
    grupos = {}
    for s, v in d["precios"].items():
        n, b = nom.get(s, (s, "otros"))
        grupos.setdefault(b, []).append((s, n, v))

    texto = L.get("texto") or ""
    titular = ""
    for ln in texto.split("\n"):
        if ln.strip():
            titular = sin_etiquetas(re.sub(r"^#+\s*|\*\*", "", ln.strip())); break
    partes = trozos(texto)

    logo = open(LOGO).read().strip() if os.path.exists(LOGO) else ""
    P = ['<!doctype html><html lang="es"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
         '<meta name="theme-color" content="#09090A">',
         '<link rel="manifest" href="manifest.webmanifest">',
         '<link rel="apple-touch-icon" href="icono-192.png">',
         '<meta name="apple-mobile-web-app-capable" content="yes">',
         '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">',
         '<meta name="apple-mobile-web-app-title" content="MHF Diario">',
         '<title>MHF Diario</title><style>%s</style></head><body><div class="env">' % CSS]

    P.append('<header>')
    if logo:
        P.append('<img src="%s" alt="MHF">' % logo)
    P.append('<span class="marca"><b>MHF</b>Diario de mercados</span>')
    P.append('<span class="fecha">%s<br>UTC</span></header>' % d["generado"].replace("T", " ")[:16])

    # --- semaforo de peligro
    if sem:
        P.append('<div class="sem %s"><div class="fila"><span class="bola"></span>'
                 '<h1>%s</h1></div><ul>' % (sem.get("nivel", "verde"), html.escape(sem.get("titulo", ""))))
        for niv, txt in sem.get("motivos", []):
            P.append("<li>%s</li>" % html.escape(txt))
        P.append("</ul></div>")

    if titular:
        P.append('<div class="titular">%s</div>' % html.escape(titular))

    sube, baja = ganadores(d["precios"], nom)
    if sube:
        P.append('<div class="tarjeta"><div class="cab"><span class="num">↕</span>'
                 '<span class="ico">◈</span><h2>Lo que mas se ha movido hoy</h2></div>'
                 '<div class="g2">')
        for rot, lst in (("Arriba", sube), ("Abajo", baja)):
            P.append('<div><div class="h2b">%s</div><table>' % rot)
            for sy, nb, cb in lst:
                P.append('<tr><td><span class="tk">%s</span><span class="dsc">%s</span></td>%s</tr>'
                         % (html.escape(sy), html.escape(nb[:18]), cambio(cb)))
            P.append("</table></div>")
        P.append("</div></div>")

    # --- earnings: primero, que es lo que mas le importa
    if ear:
        P.append('<div class="tarjeta"><div class="cab"><span class="num">★</span>'
                 '<span class="ico">◈</span><h2>Escaneo de resultados</h2></div>')
        if ear.get("hoy"):
            P.append('<div class="resumen">Hoy presentan: %s</div>'
                     % html.escape(", ".join("%s (%s)" % (e["ticker"], e["cuando"]) for e in ear["hoy"])))
        else:
            P.append('<div class="resumen">Hoy no presenta nadie de la lista.</div>')
        if ear.get("batio_y_cayo"):
            P.append('<div class="lec byc"><div class="t">Batio y cayo</div>')
            for e in ear["batio_y_cayo"]:
                P.append("<p><strong>%s (%s)</strong> %s %s</p>"
                         % (html.escape(e["empresa"]), html.escape(e["ticker"]),
                            ("%+.2f %% ·" % e["reaccion_pct"]) if e.get("reaccion_pct") is not None else "",
                            html.escape(e.get("resumen", ""))))
            P.append("</div>")
        if ear.get("semana"):
            P.append('<div class="ev" style="margin-top:12px">')
            for e in ear["semana"]:
                P.append('<div class="it"><span class="d">%s</span><span class="p p-amarillo"></span>'
                         '<span><span class="q"><strong>%s</strong> %s · %s</span>%s</span></div>'
                         % (e["fecha"][5:], html.escape(e["ticker"]), html.escape(e["empresa"]),
                            html.escape(e["cuando"]),
                            '<span class="n">%s</span>' % html.escape(e["nota"]) if e.get("nota") else ""))
            P.append("</div>")
        niv = extra.get("niveles") or {}
        for t in [e["ticker"] for e in (ear.get("hoy") or [])] + \
                 [e["ticker"] for e in (ear.get("semana") or [])]:
            if t in niv:
                P.append(bloque_niveles(t, niv.pop(t)))
        if ear.get("caducada"):
            P.append('<div class="aviso viejo">Esta lista lleva %d dias sin revisar. '
                     'Puede faltar alguna empresa.</div>' % ear.get("dias_sin_revisar", 0))
        P.append("</div>")

    # --- calendario de la semana
    if cal:
        P.append('<div class="tarjeta"><div class="cab"><span class="num">▣</span>'
                 '<span class="ico">◷</span><h2>La semana que viene</h2></div><div class="ev">')
        for e in cal:
            dias = e.get("dias", 0)
            eti = "HOY" if dias == 0 else ("manana" if dias == 1 else "+%d dias" % dias)
            P.append('<div class="it"><span class="d">%s</span><span class="p p-%s"></span>'
                     '<span><span class="q">%s</span>%s</span></div>'
                     % (eti, e.get("nivel", "verde"), html.escape(e["que"]),
                        '<span class="n">%s</span>' % html.escape(e["nota"]) if e.get("nota") else ""))
        P.append("</div></div>")

    # --- sentimiento y posicionamiento
    if extra.get("sentimiento"):
        P.append(tarjeta_sentimiento(extra["sentimiento"]))
    if extra.get("posiciones"):
        P.append(tarjeta_posiciones(extra["posiciones"]))

    # --- bloques de mercado
    n = 0
    for clave, rotulo, ico in BLOQUES:
        if clave not in grupos:
            continue
        n += 1
        filas = sorted(grupos[clave], key=lambda x: (x[2].get("pb") is None, -abs(x[2]["cambio_pct"])))
        P.append('<div class="tarjeta"><div class="cab"><span class="num">%d</span>'
                 '<span class="ico">%s</span><h2>%s</h2></div>' % (n, ico, rotulo))
        trozo = partes.get(n) or []
        if trozo:
            P.append('<div class="resumen">%s</div>' % trozo[0])
        P.append('<table><tr><th>Activo</th><th>Precio</th><th>Cambio</th><th></th></tr>')
        for s, nb, v in filas:
            P.append('<tr><td><span class="tk">%s</span><span class="dsc">%s</span></td>'
                     '<td>%s</td>%s</tr>'
                     % (html.escape(s), html.escape(nb),
                        ("%.3f %%" % v["precio"]).replace(".", ",") if v.get("pb") is not None else fnum(v["precio"]),
                        celda_cambio(v)))
        P.append("</table>")
        if clave == "metales":
            no = nota_oro(d["precios"])
            if no:
                P.append('<div class="lec"><div class="t">El oro, ¿refugio?</div><p>%s</p></div>'
                         % html.escape(no))
        if clave == "cripto":
            nb = (extra.get("niveles") or {}).get("BTC/USD")
            if nb:
                P.append(bloque_niveles("BTC", nb))
        if len(trozo) > 1:
            P.append('<div class="lec"><div class="t">Lectura de mercado</div>')
            for p in trozo[1:]:
                P.append("<p>%s</p>" % p)
            P.append("</div>")
        P.append("</div>")

    # --- lo que no encajo en ningun bloque (p.ej. "que mirar manana")
    sobra = [k for k in partes if k > n]
    if sobra:
        P.append('<div class="tarjeta"><div class="cab"><span class="num">→</span>'
                 '<span class="ico">◎</span><h2>Que mirar</h2></div><div class="lec">')
        for k in sorted(sobra):
            for p in partes[k]:
                P.append("<p>%s</p>" % p)
        P.append("</div></div>")

    if not texto and L.get("error"):
        P.append('<div class="aviso">Hoy no hay lectura: %s</div>' % html.escape(L["error"]))

    if d.get("titulares"):
        P.append('<div class="tarjeta"><div class="cab"><span class="num">≡</span>'
                 '<span class="ico">◫</span><h2>Las noticias del dia</h2></div><ul class="tit">')
        for t in d["titulares"][:28]:
            P.append('<li><span class="f">%s</span>%s</li>'
                     % (html.escape(t["fuente"]), html.escape(t["titular"])))
        P.append("</ul></div>")

    P.append('<div class="aviso">Fuentes: indices, futuros y bonos de Yahoo; acciones, ETF, divisas y bitcoin de Twelve Data. '
             'Miedo y codicia: CNN y alternative.me. Posiciones: CFTC y OKX. '
             'La lectura la escribe un modelo con esos numeros y los titulares de arriba, '
             'y <strong>puede equivocarse</strong>. Esto no es consejo de inversion.</div>')
    P.append('<footer>MHF · Diario automatico · %d de %d precios · %d fallos%s<br>'
             'Se genera solo cada dia a las 7:00. No sustituye tu criterio.</footer>'
             % (len(d["precios"]), len(d["universo"]), len(d.get("fallos") or []),
                (" · " + L["modelo"]) if L.get("modelo") else ""))
    P.append("<script>if('serviceWorker' in navigator){window.addEventListener('load',"
             "function(){navigator.serviceWorker.register('sw.js').catch(function(){});});}</script>")
    P.append("</div></body></html>")

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    open(SALIDA, "w", encoding="utf-8").write("\n".join(P))
    print("escrito %s (%d bytes)" % (SALIDA, os.path.getsize(SALIDA)))


if __name__ == "__main__":
    main()
