"""
Portal Hidrico Chaco - Dashboard (Streamlit).

Consume el MISMO backend que usa el bot de Telegram (@cuencas_chaco_bot),
para que ambas herramientas muestren siempre la misma informacion sobre
las 4 cuencas y las 12 localidades monitoreadas.

Backend: https://github.com/mariaelena30/cuencas-bot (main.py)
"""

import streamlit as st
import requests
import folium
import pandas as pd
from streamlit_folium import st_folium
from datetime import datetime

st.set_page_config(page_title="Portal Hidrico Chaco", layout="wide", page_icon="🌊")

BACKEND_URL = "https://cuencas-bot.onrender.com"

COORDENADAS = {
    "resistencia": (-27.4511, -58.9866),
    "barranqueras": (-27.4815, -58.9324),
    "corrientes": (-27.4698, -58.8306),
    "formosa": (-26.1775, -58.1781),
    "puerto_bermejo": (-26.8667, -58.6333),
    "el_sauzalito": (-24.4236, -61.6842),
    "isla_del_cerrito": (-27.3667, -58.6333),
    "puerto_vilelas": (-27.4967, -58.9394),
    "la_leonesa": (-27.0500, -58.6833),
    "pampa_del_indio": (-25.9167, -59.9333),
    "villa_rio_bermejito": (-25.6167, -60.1667),
    "fuerte_esperanza": (-24.5333, -61.7500),
}

# ---------------------------------------------------------------------
# TOKENS VISUALES
# ---------------------------------------------------------------------
COLOR_ESTADO = {
    "NORMAL": {"hex": "#2ED573", "folium": "green", "label": "Normal"},
    "ALERTA": {"hex": "#FFC93C", "folium": "orange", "label": "Alerta"},
    "EVACUACION": {"hex": "#FF4D6D", "folium": "red", "label": "Evacuación"},
}
ACENTO_RIO_CLARO = "#38BDF8"
ACENTO_RIO_MEDIO = "#0EA5B7"
ACENTO_ALERTA = "#F59E0B"
ACENTO_CRITICO = "#F43F5E"

# ---------------------------------------------------------------------
# Confirmado contra tu main.py real (cuencas: parana, paraguay, bermejo,
# pilcomayo). El orden de localidades ya NO se hardcodea a mano — se
# calcula dinámicamente usando el campo "cuenca_clave" que ya viene en
# cada localidad del backend, así nunca queda desactualizado.
# ---------------------------------------------------------------------
ORDEN_CUENCAS_PRIORIDAD = ["parana", "paraguay", "bermejo", "pilcomayo"]

# Color FIJO por cuenca (no rota por posición): así la tarjeta de
# Paraná siempre es la misma, sin importar en qué orden se dibuje.
ACENTO_POR_CUENCA = {
    "parana": "#38BDF8",     # celeste
    "paraguay": "#0EA5B7",   # verde-azulado
    "bermejo": "#F59E0B",    # ambar
    "pilcomayo": "#10B981",  # verde
}
ACENTO_CUENCA_DEFAULT = "#7C5CFC"

# ---------------------------------------------------------------------
# DATOS MORFOMETRICOS DE CUENCA (area, coeficiente de Gravelius) y bbox
# aproximado para dibujar el rectangulo de cada cuenca en el mapa.
#
# Extraidos de tu prototipo Monitoreo--main (chacoData.ts), que a su vez
# los saco del trabajo de Gomez (2025) IIGHI-CONICET/UNNE mencionado en
# tu roadmap. Kc (Gravelius) mas alto = cuenca mas alargada = modera el
# pico de crecida pero la sostiene mas tiempo en vez de picos subitos.
# bbox_aprox es una caja rectangular orientativa, NO el contorno real
# de la cuenca (eso todavia esta pendiente en QGIS con el DEM de SRTM).
# ---------------------------------------------------------------------
CUENCA_MORFOMETRIA = {
    "parana": {
        "area_km2": 1_980_000.0, "gravelius": 2.85,
        "bbox": {"lat_min": -28.0, "lat_max": -26.5, "lon_min": -59.5, "lon_max": -58.5},
    },
    "paraguay": {
        "area_km2": 1_095_000.0, "gravelius": 2.65,
        "bbox": {"lat_min": -27.3, "lat_max": -25.5, "lon_min": -59.2, "lon_max": -57.8},
    },
    "bermejo": {
        "area_km2": 14_492.0, "gravelius": 2.98,
        "bbox": {"lat_min": -27.0, "lat_max": -24.0, "lon_min": -62.5, "lon_max": -58.5},
    },
    "pilcomayo": {
        "area_km2": 272_000.0, "gravelius": 2.45,
        "bbox": {"lat_min": -24.8, "lat_max": -23.5, "lon_min": -62.8, "lon_max": -60.0},
    },
}

# ---------------------------------------------------------------------
# GRAFICO DE TENDENCIA HISTORICA
#
# El pipeline de niveles_rios.json usa nombres de ESTACION (Barranqueras,
# Corrientes, Formosa...) que no son 1 a 1 con las 12 localidades. Este
# mapeo conecta cada localidad con la estacion que mejor la representa
# (mismo tramo de rio). Las localidades que no tienen ninguna estacion
# con historico disponible (interior chaqueño, sin cobertura CIM-UNL)
# simplemente no aparecen aca, y el dashboard lo indica con claridad
# en vez de mostrar un grafico vacio o inventado.
# ---------------------------------------------------------------------
ESTACION_HISTORICO_POR_LOCALIDAD = {
    "resistencia": "Barranqueras",       # mismo tramo, ~8km
    "barranqueras": "Barranqueras",      # medicion directa
    "puerto_vilelas": "Barranqueras",    # mismo tramo, ~5km
    "corrientes": "Corrientes",          # medicion directa
    "formosa": "Formosa",                # medicion directa
    "puerto_bermejo": "Bermejo",         # zona de confluencia, aproximado
}


@st.cache_data(ttl=300)
def cargar_historico(estacion: str, dias: int = 60):
    try:
        r = requests.get(f"{BACKEND_URL}/historico/{estacion}", params={"dias": dias}, timeout=8.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"estacion": estacion, "lecturas": [], "n_lecturas": 0}


def mostrar_grafico_tendencia(clave_localidad: str, umbral_alerta: float, umbral_evacuacion: float):
    """Grafico de linea con el historico de nivel + lineas de umbral, o un aviso claro si todavia no hay suficientes datos."""
    estacion = ESTACION_HISTORICO_POR_LOCALIDAD.get(clave_localidad)

    if estacion is None:
        st.caption(
            "📈 Esta localidad todavía no tiene una estación con histórico disponible "
            "para graficar tendencia (sin cobertura del pipeline automático)."
        )
        return

    datos = cargar_historico(estacion)
    lecturas = datos.get("lecturas", [])

    if len(lecturas) < 2:
        st.caption(
            f"📈 Recién empezó a acumularse el histórico de la estación {estacion} "
            f"({len(lecturas)} lectura{'s' if len(lecturas) != 1 else ''} hasta ahora). "
            "El gráfico de tendencia va a aparecer solo en cuanto haya un par de días de datos."
        )
        return

    df = pd.DataFrame(lecturas)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.set_index("fecha")
    df["Umbral de alerta"] = umbral_alerta
    df["Umbral de evacuación"] = umbral_evacuacion
    df = df.rename(columns={"altura_m": "Nivel (m)"})

    st.markdown(
        f'<div class="analisis-label" style="color:#38BDF8;">📈 Tendencia — estación {estacion}</div>',
        unsafe_allow_html=True,
    )
    st.line_chart(
        df[["Nivel (m)", "Umbral de alerta", "Umbral de evacuación"]],
        color=["#38BDF8", "#FFC93C", "#FF4D6D"],
        height=260,
    )


def ordenar_por_prioridad(diccionario: dict, orden_claves: list) -> dict:
    """
    Devuelve una copia de `diccionario` reordenada según `orden_claves`.
    Las claves que no aparecen en `orden_claves` quedan al final,
    respetando su orden original.
    """
    ordenado = {}
    for clave in orden_claves:
        if clave in diccionario:
            ordenado[clave] = diccionario[clave]
    for clave, valor in diccionario.items():
        if clave not in ordenado:
            ordenado[clave] = valor
    return ordenado


def ordenar_localidades_por_cuenca(localidades_dict: dict, orden_cuencas: list) -> dict:
    """
    Ordena las localidades usando su propio campo "cuenca_clave"
    (viene del backend), en vez de una lista de nombres a mano.
    Dentro de una misma cuenca, mantiene el orden original (sort
    estable) y las localidades sin cuenca_clave reconocida van al final.
    """
    def prioridad(item):
        _, loc = item
        cuenca = loc.get("cuenca_clave")
        try:
            return orden_cuencas.index(cuenca)
        except ValueError:
            return len(orden_cuencas)

    return dict(sorted(localidades_dict.items(), key=prioridad))

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

.stApp {
    background: #090D1A;
    color: #F5F6FA;
}

/* ---------- Hero ---------- */
.hero-wrap { padding: 1.8rem 0 .9rem 0; }
.hero-eyebrow {
    font-family: 'JetBrains Mono', monospace; font-weight: 600; letter-spacing: .14em;
    text-transform: uppercase; font-size: .72rem; color: #7C5CFC;
    margin-bottom: .7rem; display:flex; align-items:center; gap:.5rem;
}
.hero-eyebrow .dot {
    width: 7px; height: 7px; border-radius: 50%; background: #3DDC84;
    box-shadow: 0 0 0 3px rgba(61,220,132,0.18);
    display:inline-block;
    @keyframes pulso-vivo {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 3px rgba(61,220,132,0.18); }
  50% { opacity: 0.5; box-shadow: 0 0 0 6px rgba(61,220,132,0.05); }
}
.hero-eyebrow .dot {
    width: 7px; height: 7px; border-radius: 50%; background: #3DDC84;
    box-shadow: 0 0 0 3px rgba(61,220,132,0.18);
    display:inline-block;
    animation: pulso-vivo 2s ease-in-out infinite;
}
}
.hero-title {
    font-family: 'Fraunces', serif; font-weight: 700; font-size: 2.85rem;
    line-height: 1.05; color: #FFFFFF; margin: 0 0 .55rem 0;
}
.hero-sub {
    font-family: 'Inter', sans-serif; font-size: 1rem; color: #A8AFC2;
    max-width: 660px; line-height: 1.55;
}
@keyframes fluir-linea {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
.accent-line {
    width: 100%; height: 4px; margin: 1.3rem 0 1.7rem 0; border-radius: 999px;
    background: linear-gradient(90deg, #38BDF8 0%, #0EA5B7 45%, #F59E0B 100%);
    background-size: 200% 100%;
    animation: fluir-linea 6s linear infinite;
}
/* ---------- Section headers ---------- */
.section-eyebrow {
    font-family: 'JetBrains Mono', monospace; font-weight: 600; letter-spacing: .1em;
    text-transform: uppercase; font-size: .7rem; color: #7C5CFC; margin-bottom: .2rem;
}
.section-title {
    font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.55rem;
    color: #FFFFFF; margin: 0 0 1.1rem 0;
}

/* ---------- Contexto de hoy ---------- */
.contexto-banner {
    background: #10152A; border: 1px solid rgba(124,92,252,0.35);
    border-left: 4px solid #7C5CFC; border-radius: 10px;
    padding: .9rem 1.1rem; margin: 0 0 1.4rem 0; font-size: .92rem; color: #D3D7E8;
}

/* ---------- Banda de alertas y avisos activos ---------- */
.alertas-banner {
    border-radius: 12px; padding: 1rem 1.2rem; margin: 0 0 1.4rem 0;
}
.alertas-banner.hay-alertas {
    background: rgba(244,63,94,0.08); border: 1px solid rgba(244,63,94,0.4);
    border-left: 4px solid #FF4D6D;
}
.alertas-banner.sin-alertas {
    background: rgba(46,213,115,0.06); border: 1px solid rgba(46,213,115,0.3);
    border-left: 4px solid #2ED573;
}
.alertas-banner-titulo {
    font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.05rem;
    color: #FFFFFF; margin-bottom: .5rem; display:flex; align-items:center; gap:.5rem;
}
.alertas-item {
    display:flex; align-items:center; gap:.5rem; font-size: .88rem;
    color: #F5F6FA; padding: .3rem 0;
}
.alertas-item-badge {
    font-weight:700; font-size:.62rem; text-transform:uppercase; letter-spacing:.05em;
    padding:.12rem .5rem; border-radius:999px; color:#090D1A; flex-shrink:0;
}

/* ---------- Gauge card (resumen de cuenca) ---------- */
.gauge-card {
    background: #10152A;
    border: 1px solid rgba(255,255,255,0.06);
    border-top: 3px solid var(--gauge-accent, #7C5CFC);
    border-radius: 14px; padding: 1.15rem 1.25rem 1.3rem 1.25rem;
    margin-bottom: .9rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.gauge-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.35); }
}
.gauge-top { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:.3rem; }
.gauge-name { font-family:'Fraunces', serif; font-weight:600; font-size:1.1rem; color:#FFFFFF; }
.gauge-badge {
    font-family:'Inter', sans-serif; font-weight:700; font-size:.64rem; letter-spacing:.06em;
    text-transform: uppercase; padding: .2rem .6rem; border-radius: 999px; color:#090D1A;
}
.gauge-station { font-size:.78rem; color:#A6ADC4; margin-bottom:1rem; }
.gauge-value-row { display:flex; align-items:baseline; gap:.4rem; margin-bottom:.55rem; }
.gauge-value { font-family:'Fraunces', serif; font-weight:700; font-size:1.75rem; color:#FFFFFF; }
.gauge-value-unit { font-size:.85rem; color:#9BA3BD; }
.gauge-foot { font-size:.7rem; color:#8790A8; margin-top:.7rem; }

/* ---------- Barra de umbrales (el elemento visual central) ----------
   Separa claramente TRES cosas: la zona normal, la zona de alerta y la
   zona de evacuacion, y marca con un pin donde esta el nivel actual. */
.umbral-wrap { margin: .3rem 0 .2rem 0; }
.umbral-barra {
    position: relative; width: 100%; height: 10px; border-radius: 999px;
    display: flex; overflow: visible; margin-bottom: 1.6rem;
}
.umbral-zona { height: 100%; }
.umbral-zona.normal { background: linear-gradient(90deg, #1a4d33, #2ED573); border-radius: 999px 0 0 999px; }
.umbral-zona.alerta { background: #FFC93C; }
.umbral-zona.evacuacion { background: linear-gradient(90deg, #FF4D6D, #c92c47); border-radius: 0 999px 999px 0; }
.umbral-pin {
    position: absolute; top: -9px; width: 3px; height: 28px;
    background: #FFFFFF; border-radius: 2px;
    box-shadow: 0 0 0 2px #090D1A, 0 0 8px rgba(255,255,255,0.5);
}
.umbral-pin-label {
    position: absolute; top: -30px; transform: translateX(-50%);
    font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: .68rem;
    color: #FFFFFF; background: rgba(0,0,0,0.55); padding: .12rem .4rem; border-radius: 5px;
    white-space: nowrap;
}
.umbral-marca {
    position: absolute; top: 14px; transform: translateX(-50%);
    font-size: .62rem; color: #9BA3BD; white-space: nowrap; text-align: center;
}
.umbral-marca .valor { color: #A8AFC2; font-weight: 600; }

/* ---------- Chips de metadata (fuente, precipitacion, etc) ---------- */
.meta-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: .6rem; margin: 1rem 0 1.1rem 0;
}
.meta-chip {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px; padding: .65rem .8rem;
}
.meta-chip-label {
    font-family: 'JetBrains Mono', monospace; font-size: .62rem; letter-spacing: .05em;
    text-transform: uppercase; color: #9BA3BD; margin-bottom: .25rem;
}
.meta-chip-value { font-size: .86rem; color: #F5F6FA; font-weight: 500; line-height: 1.35; }

/* ---------- Bloque de analisis ---------- */
.analisis-label {
    font-family: 'JetBrains Mono', monospace; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; font-size: .68rem; color: #3DDC84;
    margin: 1.1rem 0 .5rem 0; display:flex; align-items:center; gap:.4rem;
}

/* ---------- Localidad chip list (mapa) ---------- */
.loc-chip {
    display:inline-flex; align-items:center; gap:.4rem;
    background: #10152A; border:1px solid rgba(255,255,255,0.08);
    border-radius: 999px; padding:.3rem .7rem; margin: .15rem .3rem .15rem 0;
    font-size:.8rem; color:#D3D7E8;
}
.loc-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }

/* ---------- Tarjetas chicas de barrios vulnerables ---------- */
.barrio-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: .7rem; margin: 1rem 0 .5rem 0;
}
.barrio-card {
    background: #10152A; border: 1px solid rgba(255,255,255,0.07);
    border-left: 3px solid var(--barrio-accent, #7C5CFC);
    border-radius: 10px; padding: .75rem .85rem;
}
.barrio-card-top { display:flex; justify-content:space-between; align-items:flex-start; gap:.4rem; margin-bottom:.3rem; }
.barrio-card-nombre { font-family:'Fraunces', serif; font-weight:600; font-size:.92rem; color:#FFFFFF; line-height:1.25; }
.barrio-card-badge {
    font-family:'Inter', sans-serif; font-weight:700; font-size:.58rem; letter-spacing:.05em;
    text-transform: uppercase; padding: .12rem .45rem; border-radius: 999px; color:#090D1A;
    white-space: nowrap; flex-shrink: 0;
}
.barrio-card-padre { font-size:.72rem; color:#9BA3BD; margin-bottom:.4rem; }
.barrio-card-motivo { font-size:.76rem; color:#B8BED1; line-height:1.4; }
.barrio-card-aprox { font-size:.66rem; color:#F59E0B; margin-top:.35rem; }

.footer-note { font-size:.76rem; color:#7B8299; text-align:center; padding: 1.4rem 0 .6rem 0; }

hr { border-color: rgba(255,255,255,0.08) !important; }
[data-testid="stExpander"] {
    background: #10152A; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
}
/* El icono de flecha de Streamlit y el texto del titulo comparten fila;
   sin estas reglas, en pantallas angostas el texto largo se envuelve
   en 2 lineas y la flecha (que queda centrada verticalmente por
   defecto) termina tapando la primera letra. flex-start + flex-shrink:0
   en el icono evita la superposicion. */
[data-testid="stExpander"] summary {
    font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.02rem;
    display: flex !important;
    align-items: flex-start !important;
    gap: .55rem;
    line-height: 1.4;
    padding: .7rem .6rem;
}
[data-testid="stExpander"] summary svg {
    flex-shrink: 0;
    margin-top: .2rem;
}
[data-testid="stExpander"] summary p {
    margin: 0;
    word-break: break-word;
}
[data-testid="stMetricValue"] { color: #FFFFFF; }
[data-testid="stAlert"] { border-radius: 10px; }

/* ---------- Ajustes para pantallas chicas (celular) ---------- */
@media (max-width: 600px) {
    .hero-title { font-size: 2.05rem; }
    .hero-sub { font-size: .92rem; }
    .section-title { font-size: 1.28rem; }
    .gauge-value { font-size: 1.45rem; }
    .gauge-name { font-size: 1rem; }
    [data-testid="stExpander"] summary { font-size: .9rem; }
    .meta-grid { grid-template-columns: 1fr 1fr; }
    .umbral-marca { font-size: .68rem; }
    .umbral-pin-label { font-size: .68rem; }
    .barrio-card-motivo, .barrio-card-padre { font-size: .8rem; }
}

/* ---------- Accesibilidad: foco visible al navegar con Tab ----------
   Sin esto, en varios navegadores/temas el foco de teclado en botones,
   selectbox y el mapa casi no se nota sobre fondo oscuro. Un anillo
   celeste bien contrastado deja clarisimo donde esta el foco. */
*:focus-visible {
    outline: 3px solid #38BDF8 !important;
    outline-offset: 2px !important;
    border-radius: 4px;
}
[data-testid="stButton"] button:focus-visible,
[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
    outline: 3px solid #38BDF8 !important;
    outline-offset: 2px !important;
}

/* ---------- Zoom del navegador: todo en rem/%, nada en px fijo para
   texto, asi escala bien con Ctrl+/Ctrl- y con el tamaño de fuente
   del sistema. Este bloque solo refuerza un piso legible para que
   ningun texto quede microscopico. */
.umbral-marca, .meta-chip-label, .barrio-card-aprox {
    font-size: .68rem;
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# PWA: conecta el manifest.json e iconos para que "Agregar a pantalla
# de inicio" desde el celular use el icono propio y abra en pantalla
# completa. Streamlit no permite tocar el <head> directamente, asi que
# se inyecta con un poco de JS apuntando al documento padre.
# Requiere: carpeta static/ (manifest.json, icon-192.png, icon-512.png)
# y .streamlit/config.toml con enableStaticServing = true.
# ---------------------------------------------------------------------
import streamlit.components.v1 as components

components.html(
    """
    <script>
    (function() {
        const head = window.parent.document.head;
        if (head.querySelector('link[rel="manifest"]')) return;  // no duplicar

        const manifest = document.createElement('link');
        manifest.rel = 'manifest';
        manifest.href = './static/manifest.json';
        head.appendChild(manifest);

        const icono = document.createElement('link');
        icono.rel = 'apple-touch-icon';
        icono.href = './static/icon-192.png';
        head.appendChild(icono);

        const temaColor = document.createElement('meta');
        temaColor.name = 'theme-color';
        temaColor.content = '#090D1A';
        head.appendChild(temaColor);

        const appleCapable = document.createElement('meta');
        appleCapable.name = 'apple-mobile-web-app-capable';
        appleCapable.content = 'yes';
        head.appendChild(appleCapable);
    })();
    </script>
    """,
    height=0,
    width=0,
)

ACENTO_POR_INDICE = [ACENTO_RIO_CLARO, ACENTO_RIO_MEDIO, ACENTO_ALERTA, ACENTO_CRITICO]

# ---------------------------------------------------------------------
# BARRA DE UMBRALES: el elemento visual que separa nivel actual de
# los umbrales de alerta/evacuacion. Se usa tanto en el resumen de
# cuencas como en el detalle de cada localidad.
# ---------------------------------------------------------------------
def barra_umbral_html(nivel, umbral_alerta, umbral_evacuacion) -> str:
    tope = max(umbral_evacuacion * 1.15, nivel * 1.05)
    pct_alerta = min(umbral_alerta / tope * 100, 100)
    pct_evac = min(umbral_evacuacion / tope * 100, 100)
    pct_nivel = min(nivel / tope * 100, 100)

    ancho_normal = pct_alerta
    ancho_alerta = pct_evac - pct_alerta
    ancho_evac = 100 - pct_evac

    # BUG que reportaste ("solo se ve la alerta"): cuando el umbral de
    # alerta y el de evacuacion estan cerca (ej. 6.00 m y 6.50 m), las
    # dos etiquetas de texto caian en la MISMA altura y una tapaba a la
    # otra visualmente. Si estan a menos de 12% de distancia en la
    # barra, escalonamos la de evacuacion mas abajo para que las dos
    # queden legibles siempre, sin importar que tan juntos esten los
    # umbrales.
    cerca = (pct_evac - pct_alerta) < 12
    top_evac = "42px" if cerca else "14px"

    return f"""
    <div class="umbral-wrap" style="margin-bottom:{'2.2rem' if cerca else '1.6rem'};">
      <div class="umbral-barra">
        <div class="umbral-zona normal" style="width:{ancho_normal:.1f}%"></div>
        <div class="umbral-zona alerta" style="width:{ancho_alerta:.1f}%"></div>
        <div class="umbral-zona evacuacion" style="width:{ancho_evac:.1f}%"></div>
        <div class="umbral-pin" style="left:{pct_nivel:.1f}%"></div>
        <div class="umbral-pin-label" style="left:{pct_nivel:.1f}%">{nivel} m</div>
        <div class="umbral-marca" style="left:{pct_alerta:.1f}%; top:14px;">Alerta<br/><span class="valor">{umbral_alerta} m</span></div>
        <div class="umbral-marca" style="left:{pct_evac:.1f}%; top:{top_evac};">Evacuación<br/><span class="valor">{umbral_evacuacion} m</span></div>
      </div>
    </div>
    """



def gauge_html(nombre, estacion, nivel, umbral_alerta, umbral_evac, estado, fuente,
                conectado, actualizado, acento) -> str:
    estilo = COLOR_ESTADO.get(estado, COLOR_ESTADO["NORMAL"])
    etiqueta_conexion = "✅ En vivo" if conectado else "⚠️ Referencia"
    return f"""
    <div class="gauge-card" style="--gauge-accent:{acento}">
      <div class="gauge-top">
        <span class="gauge-name">{nombre}</span>
        <span class="gauge-badge" style="background:{estilo['hex']}">{estilo['label']}</span>
      </div>
      <div class="gauge-station">{estacion}</div>
      <div class="gauge-value-row">
        <span class="gauge-value">{nivel}</span>
        <span class="gauge-value-unit">metros — nivel actual</span>
      </div>
      {barra_umbral_html(nivel, umbral_alerta, umbral_evac)}
      <div class="gauge-foot">{etiqueta_conexion} · {fuente}<br/>Actualizado: {actualizado}</div>
    </div>
    """


def contexto_estacional(mes: int) -> str:
    if mes in (12, 1, 2, 3):
        return (
            "Estamos en **verano** (dic-mar), la temporada de mayores lluvias en la "
            "región. Es el período del año con más probabilidad de crecidas rápidas."
        )
    if mes in (4, 5, 6):
        return (
            "Estamos en **otoño** (abr-jun). Las lluvias empiezan a disminuir y los "
            "niveles suelen ir estabilizándose o bajando respecto al verano."
        )
    if mes in (7, 8, 9):
        return (
            "Estamos en **invierno** (jul-sep), la temporada típicamente más seca del "
            "año. Es habitual que los niveles estén en su punto más bajo (bajante)."
        )
    return (
        "Estamos en **primavera** (oct-nov). La humedad y las lluvias empiezan a "
        "aumentar de cara al verano, y los niveles suelen empezar a recuperarse."
    )


def interpretar_nivel_relativo(nivel, umbral_alerta, estado) -> str:
    if estado == "EVACUACION":
        return "El nivel ya superó el umbral de evacuación: es la situación más crítica de la escala."
    if estado == "ALERTA":
        return "El nivel ya superó el umbral de alerta, aunque todavía no llega al de evacuación."
    ratio = nivel / umbral_alerta if umbral_alerta else 0
    if ratio < 0.5:
        return f"El nivel actual está muy por debajo del umbral de alerta (~{ratio*100:.0f}%) — típico de bajante."
    if ratio < 0.8:
        return f"El nivel está dentro de un rango considerado normal, en torno al {ratio*100:.0f}% del umbral de alerta."
    return f"El nivel se está acercando al umbral de alerta (ya en el {ratio*100:.0f}%) — conviene monitorear con más frecuencia."


def interpretar_precipitacion(precip_mm) -> str:
    if precip_mm is None:
        return ""
    if precip_mm < 10:
        nivel_txt = "baja"
    elif precip_mm < 30:
        nivel_txt = "moderada"
    elif precip_mm < 60:
        nivel_txt = "alta"
    else:
        nivel_txt = "muy alta"
    return f"Precipitación acumulada reciente: **{precip_mm:.0f} mm** (acumulación {nivel_txt})."


def analizar(nombre, nivel, umbral_alerta, umbral_evacuacion, estado, fase_oni, mes, precip_mm=None) -> str:
    interpretacion = interpretar_nivel_relativo(nivel, umbral_alerta, estado)
    estacional = contexto_estacional(mes)
    if fase_oni == "El Niño":
        nota_oni = "Fase climática actual: **El Niño**, asociada históricamente a más lluvia de lo habitual en la región."
    elif fase_oni == "La Niña":
        nota_oni = "Fase climática actual: **La Niña**, asociada históricamente a menos lluvia de lo habitual en la región."
    else:
        nota_oni = "Fase climática actual: **Neutra**, sin señal fuerte de más o menos lluvia asociada a este factor."
    partes = [interpretacion, estacional, nota_oni]
    nota_precip = interpretar_precipitacion(precip_mm)
    if nota_precip:
        partes.append(nota_precip)
    return "\n\n".join(partes)


@st.cache_data(ttl=60)
def cargar_datos():
    try:
        r_cuencas = requests.get(f"{BACKEND_URL}/cuencas", timeout=8.0)
        r_localidades = requests.get(f"{BACKEND_URL}/localidades", timeout=8.0)
        r_cuencas.raise_for_status()
        r_localidades.raise_for_status()
        fase_oni = "Neutro"
        try:
            r_clima = requests.get(f"{BACKEND_URL}/bot/consultar", timeout=5.0)
            fase_oni = r_clima.json().get("clima", {}).get("fase_oni", "Neutro")
        except Exception:
            pass
        barrios = {}
        try:
            r_barrios = requests.get(f"{BACKEND_URL}/barrios", timeout=5.0)
            barrios = r_barrios.json().get("barrios", {})
        except Exception:
            pass
        return r_cuencas.json(), r_localidades.json(), fase_oni, barrios
    except Exception:
        return None, None, "Neutro", {}


# ---------------------------------------------------------------------
# HERO
# ---------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-wrap">
        <span class="hero-eyebrow"><span class="dot"></span>Monitoreo hidrológico en tiempo real</span>
        <h1 class="hero-title">Portal Hídrico Chaco</h1>
        <p class="hero-sub">Estado de las 4 cuencas principales y 12 localidades de riesgo
        de la provincia, con la misma información que ves en el bot de Telegram
        @cuencas_chaco_bot.</p>
    </div>
    <div class="accent-line"></div>
    """,
    unsafe_allow_html=True,
)

datos_cuencas, datos_localidades, fase_oni_actual, datos_barrios = cargar_datos()

if datos_cuencas is None:
    st.error(
        "⚠️ No se pudo conectar con el backend en este momento. "
        "Si el servicio estaba dormido por inactividad (plan gratuito de Render), "
        "puede tardar hasta 50 segundos en despertar. Volvé a cargar la página en un momento."
    )
    st.stop()

cuencas = ordenar_por_prioridad(datos_cuencas["cuencas"], ORDEN_CUENCAS_PRIORIDAD)
explicaciones = datos_cuencas["explicaciones"]
localidades = ordenar_localidades_por_cuenca(datos_localidades["localidades"], ORDEN_CUENCAS_PRIORIDAD)
mes_actual = datetime.now().month

con_conexion = sum(1 for c in cuencas.values() if c["conectado"])
if con_conexion == 0:
    st.info(
        "ℹ️ **Sobre estos datos:** todos los valores que ves abajo son datos de "
        "*referencia* (semilla), cargados manualmente para poder demostrar el "
        "sistema mientras se integra una fuente en vivo. Ninguno está conectado "
        "todavía a una fuente automática en tiempo real — cada tarjeta lo indica."
    )

# ---------------------------------------------------------------------
# ALERTAS Y AVISOS ACTIVOS
#
# Antes esto solo se veia en el canal de Telegram
# (t.me/Aviso_CuencasHidricas_Chaco2026). Esta banda replica lo mismo
# ACA en el dashboard: junta las cuencas y localidades que estan en
# ALERTA o EVACUACION ahora mismo (se recalcula en cada carga, no es
# texto fijo) y las muestra arriba de todo, bien visible.
# ---------------------------------------------------------------------
avisos_activos = []
for clave, c in cuencas.items():
    if c["estado"] != "NORMAL":
        avisos_activos.append({"tipo": "Cuenca", "nombre": c["nombre"], "estado": c["estado"]})
for clave, loc in localidades.items():
    if loc["estado"] != "NORMAL":
        avisos_activos.append({"tipo": "Localidad", "nombre": loc["nombre"], "estado": loc["estado"]})

if avisos_activos:
    items_html = "".join(
        f'<div class="alertas-item">'
        f'<span class="alertas-item-badge" style="background:{COLOR_ESTADO.get(a["estado"], COLOR_ESTADO["NORMAL"])["hex"]}">{a["estado"]}</span>'
        f'{a["tipo"]}: {a["nombre"]}'
        f'</div>'
        for a in avisos_activos
    )
    st.markdown(
        f'<div class="alertas-banner hay-alertas">'
        f'<div class="alertas-banner-titulo">🚨 {len(avisos_activos)} aviso{"s" if len(avisos_activos) != 1 else ""} activo{"s" if len(avisos_activos) != 1 else ""}</div>'
        f'{items_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="alertas-banner sin-alertas">'
        '<div class="alertas-banner-titulo">✅ Sin avisos activos</div>'
        '<div class="alertas-item">Todas las cuencas y localidades monitoreadas están en estado Normal.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div class="contexto-banner">🗓️ <b>Contexto de hoy:</b> {contexto_estacional(mes_actual)}</div>',
    unsafe_allow_html=True,
)

col_a, col_b = st.columns(2)
with col_a:
    with st.expander("📖 ¿Qué significa cada dato? (para quien no es técnico)"):
        for clave, texto in explicaciones.items():
            st.markdown(f"**{clave.replace('_', ' ').capitalize()}:** {texto}")
    with st.expander("🚨 ¿Qué hacer según el estado? (protocolo general)"):
        st.markdown(
            """
Guía **general y orientativa**, no un protocolo oficial. Ante cualquier
alerta real, la indicación válida es siempre la que emita **Defensa Civil
de tu localidad**.

- 🟢 **NORMAL:** monitoreo pasivo, sin acción especial.
- 🟡 **ALERTA:** revisá lo esencial (documentos, medicamentos, ropa) y
  estate atento a los canales oficiales.
- 🔴 **EVACUACIÓN:** seguí estrictamente las indicaciones de Defensa Civil
  y autoridades locales.
"""
        )
with col_b:
    with st.expander("🌎 Contexto: ¿en qué se basa este sistema de alerta?"):
        st.markdown(
            """
Este portal usa la misma lógica de **3 niveles** (normal, alerta, evacuación)
que emplea el **Sistema de Información y Alerta Hidrológico (SIyAH)** del
Instituto Nacional del Agua (INA), que desde 1983 monitorea la Cuenca del
Plata en cinco países y emite pronósticos usados por Defensa Civil en toda
la región.

Es una **herramienta complementaria y de demostración** — no reemplaza el
reporte oficial de INA, consultable en alerta.ina.gob.ar.

**Fuente:** Instituto Nacional del Agua (INA).
"""
        )
    with st.expander("📊 Nota metodológica sobre el análisis"):
        st.markdown(
            """
Las secciones de "Análisis y contexto" de cada cuenca combinan:
1. Qué tan cerca está el nivel actual del umbral de alerta (en %).
2. La época del año (estación húmeda/seca típica de la región).
3. La fase climática ONI vigente (El Niño / La Niña / Neutro).
4. La precipitación acumulada reciente en la localidad, cuando está disponible.

Es una lectura **orientativa basada en patrones históricos generales**,
no un pronóstico oficial.
"""
        )

# ---------------------------------------------------------------------
# PENDIENTES DEL PROYECTO
#
# Esto es contenido estático (hardcodeado acá, no viene del backend)
# porque es información del roadmap del proyecto, no un dato de
# monitoreo. Actualizalo a mano cuando se resuelva o sume un pendiente.
# ---------------------------------------------------------------------
PENDIENTES = [
    {"item": "Integración WhatsApp Cloud API", "estado": "Bloqueado", "detalle": "Esperando verificación del número en Meta."},
    {"item": "Migración a base de datos persistente (Supabase)", "estado": "En progreso", "detalle": "Reemplaza el almacenamiento en archivo, que se pierde al reiniciar Render."},
    {"item": "Deploy de notificar_cambios.py", "estado": "Pendiente", "detalle": "Falta configurar el secret TFG_BOT_TOKEN en GitHub Actions."},
    {"item": "Modo append en el pipeline de GitHub Actions", "estado": "Pendiente", "detalle": "Necesario para que calcular_tendencia.py tenga histórico real."},
    {"item": "Modelo de inundación en QGIS", "estado": "Pendiente", "detalle": "Modelo de bañera (bathtub) usando DEM de SRTM."},
    {"item": "ID del grupo de Telegram de emergencias", "estado": "Pendiente", "detalle": "Falta obtener ID_CHAT_EMERGENCIAS para las alertas automáticas."},
]

ESTADO_PENDIENTE_COLOR = {
    "Bloqueado": "#F43F5E",
    "En progreso": "#F59E0B",
    "Pendiente": "#9BA3BD",
}

with st.expander(f"🛠️ Pendientes del proyecto ({len(PENDIENTES)})", expanded=False):
    for p in PENDIENTES:
        color = ESTADO_PENDIENTE_COLOR.get(p["estado"], "#9BA3BD")
        st.markdown(
            f'<div style="display:flex; align-items:baseline; gap:.6rem; margin-bottom:.7rem;">'
            f'<span style="background:{color}; color:#090D1A; font-weight:700; font-size:.62rem; '
            f'text-transform:uppercase; letter-spacing:.05em; padding:.15rem .55rem; '
            f'border-radius:999px; white-space:nowrap;">{p["estado"]}</span>'
            f'<div>'
            f'<div style="color:#F5F6FA; font-weight:600; font-size:.88rem;">{p["item"]}</div>'
            f'<div style="color:#A6ADC4; font-size:.78rem;">{p["detalle"]}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------
# GAUGES DE LAS 4 CUENCAS
# ---------------------------------------------------------------------
st.markdown(
    '<div class="section-eyebrow">Panorama general</div>'
    '<div class="section-title">🌊 Estado de las 4 cuencas</div>',
    unsafe_allow_html=True,
)
cols = st.columns(4)
for i, (col, (clave, c)) in enumerate(zip(cols, cuencas.items())):
    with col:
        acento_cuenca = ACENTO_POR_CUENCA.get(clave, ACENTO_CUENCA_DEFAULT)
        st.markdown(
            gauge_html(
                c["nombre"], c["estacion"], c["nivel_metros"], c["umbral_alerta"],
                c["umbral_evacuacion"], c["estado"], c["fuente"], c["conectado"],
                c["ultima_verificacion"], acento_cuenca,
            ),
            unsafe_allow_html=True,
        )
        with st.expander("📊 Análisis y contexto"):
            st.markdown(
                analizar(
                    c["nombre"], c["nivel_metros"], c["umbral_alerta"], c["umbral_evacuacion"],
                    c["estado"], fase_oni_actual, mes_actual,
                )
            )

st.markdown("---")

# ---------------------------------------------------------------------
# MAPA
# ---------------------------------------------------------------------
st.markdown(
    '<div class="section-eyebrow">Vista territorial</div>'
    '<div class="section-title">🗺 Mapa de localidades monitoreadas</div>',
    unsafe_allow_html=True,
)

mapa = folium.Map(
    location=[-26.5, -59.5],
    zoom_start=6,
    # Antes: CartoDB dark_matter (plano, sin geografia visible). Ahora:
    # CartoDB Voyager, que SI dibuja rios, lagos y relieve con tonos
    # reales - resuelve tanto "se ve muy suelto" como "quiero ver los
    # rios", sin inventar coordenadas de rio a mano (que en un sistema
    # de alerta real puede ser peligroso si quedan mal ubicadas).
    tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attr='&copy; <a href="https://carto.com/">CartoDB</a> &copy; OpenStreetMap',
)

# ---- 1. Rectangulos de cuenca (delimitacion aproximada, punteada) ----
# bbox_aprox NO es el contorno real de la cuenca (eso esta pendiente en
# QGIS con el DEM de SRTM) - es una caja orientativa, aclarado en el popup.
for clave_cuenca, c in cuencas.items():
    morfo = CUENCA_MORFOMETRIA.get(clave_cuenca)
    if morfo is None:
        continue
    color_cuenca = ACENTO_POR_CUENCA.get(clave_cuenca, ACENTO_CUENCA_DEFAULT)
    bbox = morfo["bbox"]
    popup_cuenca = (
        f"<b>{c['nombre']}</b><br>"
        f"Área aprox.: {morfo['area_km2']:,.0f} km²<br>"
        f"Coef. compacidad de Gravelius: {morfo['gravelius']}<br>"
        f"<i>Caja orientativa, no el contorno real (pendiente en QGIS)</i>"
    )
    folium.Rectangle(
        bounds=[[bbox["lat_min"], bbox["lon_min"]], [bbox["lat_max"], bbox["lon_max"]]],
        color=color_cuenca,
        weight=2,
        dash_array="5, 8",
        fill=True,
        fill_color=color_cuenca,
        fill_opacity=0.07,
        popup=folium.Popup(popup_cuenca, max_width=260),
        tooltip=c["nombre"],
    ).add_to(mapa)

# ---- 2. Localidades: punto redondo de color solido, borde blanco ----
for clave, loc in localidades.items():
    if clave not in COORDENADAS:
        continue
    lat, lon = COORDENADAS[clave]
    estilo = COLOR_ESTADO.get(loc["estado"], COLOR_ESTADO["NORMAL"])
    etiqueta_conexion = "En vivo" if loc["conectado"] else "Dato de referencia, sin conexión automática aún"
    precip = loc.get("precipitacion_acumulada_mm")
    linea_precip = f"Precipitación acumulada: {precip:.0f} mm<br>" if precip is not None else ""
    popup_html = (
        f"<b>{loc['nombre']}</b><br>"
        f"Nivel: {loc['nivel_metros']} m<br>"
        f"Estado: {loc['estado']}<br>"
        f"{linea_precip}"
        f"Fuente: {loc['fuente']}<br>"
        f"<i>{etiqueta_conexion}</i>"
    )
    icono_localidad = folium.DivIcon(
        html=(
            f'<div style="background-color:{estilo["hex"]}; width:22px; height:22px; '
            f'border-radius:50%; border:2px solid #FFFFFF; box-shadow:0 3px 6px rgba(0,0,0,0.4);"></div>'
        ),
        icon_size=(22, 22), icon_anchor=(11, 11),
    )
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=280),
        tooltip=loc["nombre"],
        icon=icono_localidad,
    ).add_to(mapa)

# ---- 3. Barrios vulnerables: cuadrado ROJO fijo (delimitacion), sin
# depender del estado actual - la vulnerabilidad historica es constante,
# no cambia con el nivel del rio de hoy. Eso era justo lo que pediste:
# marcarlas siempre en rojo para que se distingan de las localidades.
for clave, b in datos_barrios.items():
    aviso_precision = "" if b["precision"] == "confirmada" else f" · ubicación {b['precision']}"
    popup_barrio = (
        f"<b>⚠️ ZONA VULNERABLE — {b['nombre']}</b><br>"
        f"<i>Dentro de {b.get('nombre_localidad_padre', b['localidad_padre'])}</i><br><br>"
        f"{b['motivo']}"
        f"{aviso_precision}"
    )
    icono_barrio = folium.DivIcon(
        html=(
            '<div style="background-color:#F43F5E; width:18px; height:18px; '
            'border-radius:4px; border:2px solid #FFFFFF; box-shadow:0 3px 6px rgba(0,0,0,0.4); '
            'display:flex; align-items:center; justify-content:center; color:#FFFFFF; '
            'font-size:10px; font-weight:900;">▲</div>'
        ),
        icon_size=(18, 18), icon_anchor=(9, 9),
    )
    folium.Marker(
        location=[b["lat"], b["lon"]],
        popup=folium.Popup(popup_barrio, max_width=300),
        tooltip=f"⚠️ {b['nombre']}",
        icon=icono_barrio,
    ).add_to(mapa)

# ---- 4. Leyenda flotante (esquina inferior derecha del mapa) ----
leyenda_html = """
<div style="position:absolute; bottom:14px; right:14px; z-index:1000;
     background:rgba(9,13,26,0.92); border:1px solid rgba(56,189,248,0.35);
     border-radius:10px; padding:.7rem .9rem; font-family:'Inter',sans-serif;
     font-size:.7rem; color:#D3D7E8; max-width:210px; box-shadow:0 8px 20px rgba(0,0,0,0.4);">
  <div style="font-weight:700; color:#FFFFFF; margin-bottom:.4rem; font-size:.68rem;
       text-transform:uppercase; letter-spacing:.05em;">Referencias</div>
  <div style="display:flex; align-items:center; gap:.4rem; margin-bottom:.3rem;">
    <span style="width:10px; height:10px; border-radius:50%; background:#2ED573; display:inline-block; border:1px solid #fff;"></span>
    Localidad — Normal
  </div>
  <div style="display:flex; align-items:center; gap:.4rem; margin-bottom:.3rem;">
    <span style="width:10px; height:10px; border-radius:50%; background:#FFC93C; display:inline-block; border:1px solid #fff;"></span>
    Localidad — Alerta
  </div>
  <div style="display:flex; align-items:center; gap:.4rem; margin-bottom:.3rem;">
    <span style="width:10px; height:10px; border-radius:50%; background:#FF4D6D; display:inline-block; border:1px solid #fff;"></span>
    Localidad — Evacuación
  </div>
  <div style="display:flex; align-items:center; gap:.4rem; margin-bottom:.3rem;">
    <span style="width:10px; height:10px; border-radius:3px; background:#F43F5E; display:inline-block; border:1px solid #fff;"></span>
    Zona vulnerable histórica
  </div>
  <div style="display:flex; align-items:center; gap:.4rem;">
    <span style="width:14px; height:8px; border:1.5px dashed #7C5CFC; display:inline-block;"></span>
    Cuenca (caja orientativa)
  </div>
</div>
"""
mapa.get_root().html.add_child(folium.Element(leyenda_html))

st_folium(mapa, width=1100, height=520)

chips = "".join(
    f'<span class="loc-chip"><span class="loc-dot" style="background:{COLOR_ESTADO.get(l["estado"], COLOR_ESTADO["NORMAL"])["hex"]}"></span>{l["nombre"]}</span>'
    for l in localidades.values()
)
st.markdown(chips, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# BARRIOS Y ZONAS VULNERABLES
# ---------------------------------------------------------------------
if datos_barrios:
    st.markdown("---")
    st.markdown(
        '<div class="section-eyebrow">Detalle histórico</div>'
        '<div class="section-title">⚠️ Barrios y zonas históricamente más vulnerables</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Estos son puntos *dentro* de una localidad que, según registros de crecidas "
        "pasadas (1982, 1998, 2014, 2023), sufren antes y peor que el resto de la "
        "ciudad — no tienen medición propia, comparten el estado de su localidad."
    )

    tarjetas_barrios = ""
    for clave, b in datos_barrios.items():
        estilo_b = COLOR_ESTADO.get(b["estado"], COLOR_ESTADO["NORMAL"])
        es_aproximada = b["precision"] != "confirmada"
        aviso_precision = (
            '<div class="barrio-card-aprox">📍 ubicación aproximada</div>' if es_aproximada else ""
        )
        nombre_padre = b.get("nombre_localidad_padre", b["localidad_padre"])
        # OJO: nada de indentacion ni saltos de linea con espacios adelante
        # dentro de este HTML. Streamlit pasa esto primero por un parser de
        # Markdown antes que por HTML, y Markdown interpreta 4+ espacios de
        # indentacion al arrancar una linea como "bloque de codigo" - ahi
        # es donde se rompian las tarjetas (se veian como texto crudo).
        tarjetas_barrios += (
            f'<div class="barrio-card" style="--barrio-accent:{estilo_b["hex"]}">'
            f'<div class="barrio-card-top">'
            f'<span class="barrio-card-nombre">{b["emoji"]} {b["nombre"]}</span>'
            f'<span class="barrio-card-badge" style="background:{estilo_b["hex"]}">{estilo_b["label"]}</span>'
            f'</div>'
            f'<div class="barrio-card-padre">Dentro de {nombre_padre}</div>'
            f'<div class="barrio-card-motivo">{b["motivo"]}</div>'
            f'{aviso_precision}'
            f'</div>'
        )

    st.markdown(f'<div class="barrio-grid">{tarjetas_barrios}</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    '<div class="section-eyebrow">Detalle</div>'
    '<div class="section-title">📍 Detalle por localidad</div>',
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------
# CARRUSEL: antes se listaban las 12 localidades una debajo de la
# otra (muy largo para scrollear, sobre todo en celular). Ahora se
# muestra una por vez, con botones Anterior/Siguiente y un salto
# directo por nombre. El orden respeta ORDEN_CUENCAS_PRIORIDAD via
# cuenca_clave (Paraná primero), así que "Siguiente" recorre en ese orden.
# -----------------------------------------------------------------
lista_localidades = list(localidades.items())
total_loc = len(lista_localidades)

if "loc_index" not in st.session_state:
    st.session_state.loc_index = 0
# Por si el backend devuelve menos localidades que antes
st.session_state.loc_index = st.session_state.loc_index % total_loc

nombres_localidades = [loc["nombre"] for _, loc in lista_localidades]

col_select, col_prev, col_pos, col_next = st.columns([5, 1, 1.4, 1])
with col_select:
    # La key incluye el indice actual a proposito: asi Streamlit trata
    # el selectbox como un widget NUEVO cada vez que cambia loc_index
    # (por los botones prev/next), y usa el "index=" de abajo en vez
    # de pisarlo con un valor previo guardado bajo la key vieja - eso
    # era lo que hacia que "1 / 12" pareciera no moverse.
    seleccion = st.selectbox(
        "Ir directo a una localidad",
        nombres_localidades,
        index=st.session_state.loc_index,
        key=f"loc_select_{st.session_state.loc_index}",
        label_visibility="collapsed",
    )
    indice_seleccion = nombres_localidades.index(seleccion)
    if indice_seleccion != st.session_state.loc_index:
        st.session_state.loc_index = indice_seleccion
        st.rerun()
with col_prev:
    if st.button("◀", key="loc_prev", use_container_width=True):
        st.session_state.loc_index = (st.session_state.loc_index - 1) % total_loc
        st.rerun()
with col_pos:
    st.markdown(
        f"<div style='text-align:center; padding-top:.5rem; color:#9BA3BD; "
        f"font-family:JetBrains Mono, monospace; font-size:.78rem;'>"
        f"{st.session_state.loc_index + 1} / {total_loc}</div>",
        unsafe_allow_html=True,
    )
with col_next:
    if st.button("▶", key="loc_next", use_container_width=True):
        st.session_state.loc_index = (st.session_state.loc_index + 1) % total_loc
        st.rerun()

clave, loc = lista_localidades[st.session_state.loc_index]
aviso = "" if loc["conectado"] else " · ⚠️ dato de referencia"
estilo = COLOR_ESTADO.get(loc["estado"], COLOR_ESTADO["NORMAL"])
precip = loc.get("precipitacion_acumulada_mm")

st.markdown(
    f'<div class="gauge-card" style="--gauge-accent:{estilo["hex"]}; margin-top:.8rem;">'
    f'<div class="gauge-top">'
    f'<span class="gauge-name">{loc["emoji"]} {loc["nombre"]}{aviso}</span>'
    f'<span class="gauge-badge" style="background:{estilo["hex"]}">{estilo["label"]}</span>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# Valor grande del nivel actual + badge de estado
st.markdown(
    f'<div class="gauge-value-row" style="margin-top:.7rem;">'
    f'<span class="gauge-value">{loc["nivel_metros"]}</span>'
    f'<span class="gauge-value-unit">metros — nivel actual</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# Barra visual que separa nivel actual de los umbrales
st.markdown(barra_umbral_html(loc["nivel_metros"], loc["umbral_alerta"], loc["umbral_evacuacion"]), unsafe_allow_html=True)

mostrar_grafico_tendencia(clave, loc["umbral_alerta"], loc["umbral_evacuacion"])

# Metadata en chips, separada del nivel/umbrales
precip_txt = f"{precip:.0f} mm" if precip is not None else "Sin dato"
conectado_txt = "Sí, en vivo" if loc["conectado"] else "No, dato de referencia"
st.markdown(
    f'<div class="meta-grid">'
    f'<div class="meta-chip">'
    f'<div class="meta-chip-label">Precipitación acumulada</div>'
    f'<div class="meta-chip-value">{precip_txt}</div>'
    f'</div>'
    f'<div class="meta-chip">'
    f'<div class="meta-chip-label">Conectado en vivo</div>'
    f'<div class="meta-chip-value">{conectado_txt}</div>'
    f'</div>'
    f'<div class="meta-chip">'
    f'<div class="meta-chip-label">Última verificación</div>'
    f'<div class="meta-chip-value">{loc["ultima_verificacion"]}</div>'
    f'</div>'
    f'<div class="meta-chip">'
    f'<div class="meta-chip-label">Fuente</div>'
    f'<div class="meta-chip-value">{loc["fuente"]}</div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="analisis-label">📊 Análisis</div>', unsafe_allow_html=True)
st.markdown(
    analizar(
        loc["nombre"], loc["nivel_metros"], loc["umbral_alerta"], loc["umbral_evacuacion"],
        loc["estado"], fase_oni_actual, mes_actual, loc.get("precipitacion_acumulada_mm"),
    )
)

st.markdown(
    '<div class="footer-note">Este portal y el bot de Telegram @cuencas_chaco_bot '
    'comparten el mismo backend, para que la información sea siempre consistente '
    'entre ambas herramientas.</div>',
    unsafe_allow_html=True,
)
