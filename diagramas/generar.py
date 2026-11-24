"""Genera arquitectura-develop.svg (y _render.html para sacar el PNG con Chrome).

Uso:
    python3 generar.py
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
      --hide-scrollbars --force-device-scale-factor=2 --window-size=1600,1130 \
      --screenshot=arquitectura-develop.png "file://$PWD/_render.html"
"""
W, H = 1600, 1130
NAVY = '#1E3A5F'; N4 = '#54769E'; N3 = '#7A95B4'; N1 = '#C5D3E0'; AMB = '#E8A33C'; AMBL = '#FEF3E2'
C = {'compute': '#2F6FDB', 'edge': AMB, 'net': '#0E9F8E', 'data': '#10B981', 'ops': '#7C5CD6',
     'client': N4, 'ext': '#64748B'}
o = []
a = o.append


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;')


def card(x, y, w, h, kind, title, lines, badge=None):
    a(f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="{N1}"/></g>')
    a(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{C[kind]}"/>')
    a(f'<circle cx="{x+30}" cy="{y+27}" r="11" fill="{C[kind]}" opacity=".14"/><circle cx="{x+30}" cy="{y+27}" r="4.5" fill="{C[kind]}"/>')
    a(f'<text x="{x+50}" y="{y+32}" class="t">{esc(title)}</text>')
    for i, l in enumerate(lines):
        a(f'<text x="{x+22}" y="{y+58+i*20}" class="l">{esc(l)}</text>')
    if badge:
        bw = len(badge) * 7.1 + 18
        a(f'<rect x="{x+w-bw-12}" y="{y+13}" width="{bw}" height="22" rx="11" fill="{C[kind]}" opacity=".13"/>'
          f'<text x="{x+w-12-bw/2}" y="{y+28}" class="b" fill="{C[kind]}" text-anchor="middle">{esc(badge)}</text>')


def group(x, y, w, h, label, fill, stroke, sub=None):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
    a(f'<text x="{x+20}" y="{y+29}" class="g">{esc(label)}</text>')
    if sub:
        a(f'<text x="{x+w-20}" y="{y+29}" class="gs" text-anchor="end">{esc(sub)}</text>')


def arrow(pts, label=None, lx=None, ly=None, dash=False, color=NAVY, anchor='start'):
    d = 'M' + ' L'.join(f'{x},{y}' for x, y in pts)
    da = ' stroke-dasharray="6 5"' if dash else ''
    mk = 'ad' if color != NAVY else 'an'
    a(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{da} marker-end="url(#{mk})"/>')
    if label:
        tw = len(label) * 6.7 + 14
        bx = lx - 7 if anchor == 'start' else lx - tw / 2
        a(f'<rect x="{bx}" y="{ly-15}" width="{tw}" height="21" rx="5" fill="#fff" opacity=".95"/>')
        a(f'<text x="{lx}" y="{ly}" class="a" text-anchor="{anchor}" fill="{color}">{esc(label)}</text>')


a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
a(f'''<defs>
<filter id="sh" x="-5%" y="-10%" width="110%" height="130%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="{NAVY}" flood-opacity=".10"/></filter>
<marker id="an" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L9,5 L0,10 z" fill="{NAVY}"/></marker>
<marker id="ad" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L9,5 L0,10 z" fill="{C['ops']}"/></marker>
<style>
text{{font-family:"Plus Jakarta Sans","Helvetica Neue",Helvetica,Arial,sans-serif}}
.h1{{font-size:27px;font-weight:700;fill:{NAVY};letter-spacing:-.4px}}
.h2{{font-size:15px;fill:{N4}}}
.t{{font-size:15.5px;font-weight:700;fill:{NAVY}}}
.l{{font-size:13px;fill:{N4}}}
.b{{font-size:11.5px;font-weight:700}}
.g{{font-size:14px;font-weight:700;fill:{NAVY};letter-spacing:.2px}}
.gs{{font-size:12.5px;fill:{N4}}}
.a{{font-size:12.5px;font-weight:600}}
.k{{font-size:12.5px;fill:{N4}}}
</style></defs>''')
a(f'<rect width="{W}" height="{H}" fill="#F7F9FB"/>')
a(f'<rect x="0" y="0" width="{W}" height="6" fill="{AMB}"/>')
a('<text x="60" y="56" class="h1">TrackVa · ambiente develop en Google Cloud</text>')
a('<text x="60" y="82" class="h2">Arquitectura desplegada el 23 y 24 de noviembre de 2026 · región us-east4 (Virginia del Norte)</text>')

# Clientes
a(f'<text x="60" y="150" class="g" fill="{N4}">Clientes</text>')
for x, (t, l) in zip([250, 490, 730, 970], [('Personal del courier', 'navegador'), ('Mensajero', 'app móvil'),
                                             ('Destinatario', 'rastreo público'), ('Sitio del courier', 'widgets embebidos')]):
    card(x, 108, 222, 72, 'client', t, [l])
arrow([(800, 180), (800, 222)], 'HTTPS · app-dev.trackva.com.co', 816, 206)

# Borde
group(330, 224, 940, 128, 'Borde · único punto de entrada', AMBL, AMB)
card(352, 262, 440, 76, 'edge', 'Balanceador de carga global', ['IP 136.68.113.157 · certificado administrado · HTTP → HTTPS'])
card(810, 262, 440, 76, 'edge', 'Cloud Armor · trackva-armor', ['120 por minuto por IP en rutas públicas · SQLi y XSS en vista previa'])

# Proyecto
group(60, 396, 1210, 518, 'Google Cloud · proyecto trackva-dev', '#FFFFFF', N3, sub='un proyecto por ambiente')
a('<text x="85" y="455" class="gs">Servicios de apoyo</text>')
for i, (t, k, l) in enumerate([('Artifact Registry', 'data', '3 imágenes · etiqueta = commit'),
                               ('Secret Manager', 'edge', '6 secretos · permiso por secreto'),
                               ('Cloud Tasks', 'compute', 'cola notifications · 3 intentos'),
                               ('Cloud Monitoring', 'ops', '2 comprobaciones · 3 alertas')]):
    card(85, 468 + i * 92, 268, 76, k, t, [l])

# Cloud Run
group(380, 436, 866, 206, 'Cloud Run', '#F2F6FE', '#B9CDF3', sub='0 a 3 instancias · escala a cero · ingress cerrado a internet')
card(402, 480, 262, 140, 'compute', 'trackva-web', ['Next.js con renderizado en servidor', '1 CPU · 512 MiB', 'recibe todo lo demás'], badge='web')
card(682, 480, 262, 140, 'compute', 'trackva-api', ['NestJS · lógica de negocio', '1 CPU · 1 GiB · Node 22', 'recibe /api/*'], badge='API')
card(962, 480, 262, 140, 'compute', 'trackva-integrations', ['NestJS · transportadoras', 'solo red interna', '404 desde internet'])
arrow([(944, 566), (962, 566)])
arrow([(533, 338), (533, 480)], 'lo demás', 547, 420)
arrow([(813, 338), (813, 480)], '/api/*', 827, 420)
arrow([(353, 598), (380, 598)])

# VPC
group(380, 690, 866, 196, 'VPC trackva-vpc', '#EFFAF8', '#9EDBD3', sub='subred 10.10.0.0/24 · acceso privado a Google')
card(402, 738, 400, 124, 'net', 'Firewall de salida', ['permite TCP 443, 5432 y 6543', 'rechaza todo lo demás', 'aplica a la etiqueta trackva-run'])
card(862, 738, 362, 124, 'net', 'Cloud NAT', ['IP fija 136.70.79.227', 'única salida a internet', 'de los tres servicios'], badge='IP fija')
arrow([(813, 642), (813, 690)], 'salida directa a la VPC · todo el tráfico', 829, 672)
arrow([(802, 800), (862, 800)])

# Externos
a(f'<text x="60" y="1006" class="g" fill="{N4}">Servicios externos</text>')
card(380, 960, 350, 100, 'data', 'Supabase · us-east-1', ['PostgreSQL · autenticación · archivos', 'PostgreSQL solo acepta la IP del NAT'], badge='datos')
card(746, 960, 140, 100, 'ext', 'Resend', ['correo'])
card(900, 960, 140, 100, 'ext', 'Sentry', ['errores'])
card(1054, 960, 192, 100, 'ext', 'Google Maps', ['mapas y rutas'])
arrow([(1043, 862), (1043, 936), (555, 936), (555, 960)], 'salida por la IP fija', 690, 930, anchor='middle')
arrow([(816, 936), (816, 960)])
arrow([(970, 936), (970, 960)])
arrow([(1043, 936), (1150, 936), (1150, 960)])

# Entrega continua
a(f'<text x="1310" y="430" class="g" fill="{N4}">Entrega continua</text>')
card(1310, 444, 240, 76, 'ops', '3 repositorios', ['api · web · integrations'])
card(1310, 560, 240, 152, 'ops', 'GitHub Actions', ['CI: formato, lint, tipos, pruebas', 'despliega en cada push a main',
                                                    'identidad federada, sin llaves', 'vuelve atrás si falla la prueba'])
arrow([(1430, 520), (1430, 560)], color=C['ops'])
arrow([(1310, 636), (1288, 636), (1288, 536), (1248, 536)], dash=True, color=C['ops'])

# Leyenda
lx, ly = 1310, 750
a(f'<rect x="{lx}" y="{ly}" width="240" height="164" rx="12" fill="#fff" stroke="{N1}"/>')
a(f'<text x="{lx+16}" y="{ly+28}" class="g">Leyenda</text>')
a(f'<path d="M{lx+16},{ly+50} L{lx+62},{ly+50}" stroke="{NAVY}" stroke-width="2" marker-end="url(#an)"/><text x="{lx+74}" y="{ly+54}" class="k">tráfico de la aplicación</text>')
a(f'<path d="M{lx+16},{ly+74} L{lx+62},{ly+74}" stroke="{C["ops"]}" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#ad)"/><text x="{lx+74}" y="{ly+78}" class="k">despliegue</text>')
for i, (k, t) in enumerate([('compute', 'cómputo'), ('edge', 'borde y secretos'), ('net', 'red'), ('data', 'datos')]):
    yy = ly + 98 + i * 17
    a(f'<circle cx="{lx+24}" cy="{yy}" r="5" fill="{C[k]}"/><text x="{lx+40}" y="{yy+4}" class="k">{t}</text>')
a(f'<text x="60" y="{H-24}" class="k">Las URL run.app de los tres servicios responden 404 desde internet: todo el tráfico entra por el balanceador.</text>')
a('</svg>')
svg = '\n'.join(o)
open('arquitectura-develop.svg', 'w').write(svg)
open('_render.html', 'w').write(
    f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#F7F9FB}}svg{{display:block}}</style>{svg}')
