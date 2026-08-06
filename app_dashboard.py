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
# TOKENS VISUALES — paleta propia: marino casi negro + acentos vivos
# rosa/violeta/verde, minimalista y de buen contraste.
# ---------------------------------------------------------------------
COLOR_ESTADO = {
    "NORMAL": {"hex": "#2ED573", "folium": "green", "label": "Normal"},
    "ALERTA": {"hex": "#FFC93C", "folium": "orange", "label": "Alerta"},
    "EVACUACION": {"hex": "#FF4D6D", "folium": "red", "label": "Evacuación"},
}
ACENTO_ROSA = "#EC4899"
ACENTO_VIOLETA = "#7C5CFC"
ACENTO_VERDE = "#3DDC84"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

.stApp {
    background: #090D1A;
    color: #F5F6FA;
}

/* Hero */
.hero-wrap { padding: 1.6rem 0 .8rem 0; }
.hero-eyebrow {
    font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: .16em;
    text-transform: uppercase; font-size: .72rem; color: #FF4FA3;
    margin-bottom: .6rem; display:block;
}
.hero-title {
    font-family: 'Fraunces', serif; font-weight: 700; font-size: 2.9rem;
    line-height: 1.05; color: #FFFFFF; margin: 0 0 .5rem 0;
}
.hero-sub {
    font-family: 'Inter', sans-serif; font-size: 1rem; color: #A8AFC2;
    max-width: 640px; line-height: 1.5;
}
.accent-line {
    width: 100%; height: 5px; margin: 1.2rem 0 1.6rem 0; border-radius: 999px;
    background: linear-gradient(90deg, #EC4899 0%, #7C5CFC 45%, #3DDC84 100%);
}

/* Section headers */
.section-eyebrow {
    font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; font-size: .72rem; color: #7C5CFC; margin-bottom: .15rem;
}
.section-title {
    font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.55rem;
    color: #FFFFFF; margin: 0 0 1rem 0;
}

/* Contexto de hoy */
.contexto-banner {
    background: #10152A; border: 1px solid rgba(124,92,252,0.35);
    border-left: 4px solid #7C5CFC; border-radius: 10px;
    padding: .9rem 1.1rem; margin: 0 0 1.4rem 0; font-size: .92rem; color: #D3D7E8;
}

/* Gauge card por cuenca */
.gauge-card {
    background: #10152A;
    border: 1px solid rgba(255,255,255,0.06);
    border-top: 3px solid var(--gauge-accent, #7C5CFC);
    border-radius: 14px; padding: 1.1rem 1.2rem 1.2rem 1.2rem;
    margin-bottom: .9rem;
}
.gauge-top { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:.3rem; }
.gauge-name { font-family:'Fraunces', serif; font-weight:600; font-size:1.1rem; color:#FFFFFF; }
.gauge-badge {
    font-family:'Inter', sans-serif; font-weight:700; font-size:.66rem; letter-spacing:.06em;
    text-transform: uppercase; padding: .18rem .55rem; border-radius: 999px; color:#090D1A;
}
.gauge-station { font-size:.78rem; color:#8890A6; margin-bottom:.7rem; }
.gauge-track {
    position: relative; width:100%; height:12px; border-radius:999px;
    background: rgba(255,255,255,0.07); overflow: visible; margin-bottom: .3rem;
}
.gauge-fill { position:absolute; left:0; top:0; height:100%; border-radius:999px; }
.gauge-tick {
    position:absolute; top:-3px; width:2px; height:18px; background: rgba(255,255,255,0.35);
}
.gauge-tick-label {
    position:absolute; top:14px; font-size:.6rem; color:#7A8296; transform: translateX(-50%);
    white-space: nowrap;
}
.gauge-value { font-family:'Fraunces', serif; font-weight:700; font-size:1.35rem; color:#FFFFFF; margin-top:1.5rem; }
.gauge-foot { font-size:.7rem; color:#6E7690; margin-top:.4rem; }

/* Localidad chip list */
.loc-chip {
    display:inline-flex; align-items:center; gap:.4rem;
    background: #10152A; border:1px solid rgba(255,255,255,0.08);
    border-radius: 999px; padding:.3rem .7rem; margin: .15rem .3rem .15rem 0;
    font-size:.8rem; color:#D3D7E8;
}
.loc-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }

.footer-note { font-size:.76rem; color:#565D75; text-align:center; padding: 1.4rem 0 .6rem 0; }

hr { border-color: rgba(255,255,255,0.08) !important; }
[data-testid="stExpander"] {
    background: #10152A; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
}
[data-testid="stMetricValue"] { color: #FFFFFF; }
[data-testid="stAlert"] { border-radius: 10px; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

ACENTO_POR_INDICE = [ACENTO_ROSA, ACENTO_VIOLETA, ACENTO_VERDE, "#38BDF8"]


def gauge_html(nombre, estacion, nivel, umbral_alerta, umbral_evac, estado, fuente,
                conectado, actualizado, acento) -> str:
    estilo = COLOR_ESTADO.get(estado, COLOR_ESTADO["NORMAL"])
    tope = max(umbral_evac * 1.18, nivel * 1.05)
    pct_nivel = min(nivel / tope * 100, 100)
    pct_alerta = min(umbral_alerta / tope * 100, 100)
    pct_evac = min(umbral_evac / tope * 100, 100)
    etiqueta_conexion = "✅ En vivo" if conectado else "⚠️ Dato de referencia"
    return f"""
    <div class="gauge-card" style="--gauge-accent:{acento}">
      <div class="gauge-top">
        <span class="gauge-name">{nombre}</span>
        <span class="gauge-badge" style="background:{estilo['hex']}">{estilo['label']}</span>
      </div>
      <div class="gauge-station">{estacion}</div>
      <div class="gauge-track">
        <div class="gauge-fill" style="width:{pct_nivel:.1f}%; background:{estilo['hex']};"></div>
        <div class="gauge-tick" style="left:{pct_alerta:.1f}%; background:#FFC93C;"></div>
        <div class="gauge-tick-label" style="left:{pct_alerta:.1f}%;">Alerta {umbral_alerta}m</div>
        <div class="gauge-tick" style="left:{pct_evac:.1f}%; background:#FF4D6D;"></div>
        <div class="gauge-tick-label" style="left:{pct_evac:.1f}%;">Evac. {umbral_evac}m</div>
      </div>
      <div class="gauge-value">{nivel} m</div>
      <div class="gauge-foot">{etiqueta_conexion} · {fuente}<br/>Actualizado: {actualizado}</div>
    </div>
    """


# ---------------------------------------------------------------------
# ANALISIS: interpretacion del valor + contexto estacional.
# Orientativo, basado en patrones climaticos generales de la region —
# no es un pronostico oficial ni reemplaza el reporte de INA o el SMN.
# ---------------------------------------------------------------------
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


def analizar(nombre, nivel, umbral_alerta, umbral_evacuacion, estado, fase_oni, mes) -> str:
    interpretacion = interpretar_nivel_relativo(nivel, umbral_alerta, estado)
    estacional = contexto_estacional(mes)
    if fase_oni == "El Niño":
        nota_oni = "Fase climática actual: **El Niño**, asociada históricamente a más lluvia de lo habitual en la región."
    elif fase_oni == "La Niña":
        nota_oni = "Fase climática actual: **La Niña**, asociada históricamente a menos lluvia de lo habitual en la región."
    else:
        nota_oni = "Fase climática actual: **Neutra**, sin señal fuerte de más o menos lluvia asociada a este factor."
    return f"{interpretacion}\n\n{estacional}\n\n{nota_oni}"


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
        return r_cuencas.json(), r_localidades.json(), fase_oni
    except Exception:
        return None, None, "Neutro"


# ---------------------------------------------------------------------
# HERO
# ---------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-wrap">
        <span class="hero-eyebrow">HackLab + Hackathon 2026 · 2HC26</span>
        <h1 class="hero-title">Portal Hídrico Chaco</h1>
        <p class="hero-sub">Monitoreo de las 4 cuencas principales y 12 localidades
        de riesgo de la provincia, con la misma información que ves en el bot de
        Telegram @cuencas_chaco_bot.</p>
    </div>
    <div class="accent-line"></div>
    """,
    unsafe_allow_html=True,
)

datos_cuencas, datos_localidades, fase_oni_actual = cargar_datos()

if datos_cuencas is None:
    st.error(
        "⚠️ No se pudo conectar con el backend en este momento. "
        "Si el servicio estaba dormido por inactividad (plan gratuito de Render), "
        "puede tardar hasta 50 segundos en despertar. Volvé a cargar la página en un momento."
    )
    st.stop()

cuencas = datos_cuencas["cuencas"]
explicaciones = datos_cuencas["explicaciones"]
localidades = datos_localidades["localidades"]
mes_actual = datetime.now().month

# ---------------------------------------------------------------------
# TRANSPARENCIA SOBRE LOS DATOS + CONTEXTO DE HOY
# ---------------------------------------------------------------------
con_conexion = sum(1 for c in cuencas.values() if c["conectado"])
if con_conexion == 0:
    st.info(
        "ℹ️ **Sobre estos datos:** todos los valores que ves abajo son datos de "
        "*referencia* (semilla), cargados manualmente para poder demostrar el "
        "sistema mientras se integra una fuente en vivo. Ninguno está conectado "
        "todavía a una fuente automática en tiempo real — cada tarjeta lo indica."
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

Es una lectura **orientativa basada en patrones históricos generales**,
no un pronóstico oficial.
"""
        )

st.markdown("---")

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
        st.markdown(
            gauge_html(
                c["nombre"], c["estacion"], c["nivel_metros"], c["umbral_alerta"],
                c["umbral_evacuacion"], c["estado"], c["fuente"], c["conectado"],
                c["ultima_verificacion"], ACENTO_POR_INDICE[i % len(ACENTO_POR_INDICE)],
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

mapa = folium.Map(location=[-26.5, -59.5], zoom_start=6, tiles="CartoDB dark_matter")

for clave, loc in localidades.items():
    if clave not in COORDENADAS:
        continue
    lat, lon = COORDENADAS[clave]
    estilo = COLOR_ESTADO.get(loc["estado"], COLOR_ESTADO["NORMAL"])
    etiqueta_conexion = "En vivo" if loc["conectado"] else "Dato de referencia, sin conexión automática aún"
    popup_html = (
        f"<b>{loc['nombre']}</b><br>"
        f"Nivel: {loc['nivel_metros']} m<br>"
        f"Estado: {loc['estado']}<br>"
        f"Fuente: {loc['fuente']}<br>"
        f"<i>{etiqueta_conexion}</i>"
    )
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=280),
        tooltip=loc["nombre"],
        icon=folium.Icon(color=estilo["folium"], icon="tint"),
    ).add_to(mapa)

st_folium(mapa, width=1100, height=500)

chips = "".join(
    f'<span class="loc-chip"><span class="loc-dot" style="background:{COLOR_ESTADO.get(l["estado"], COLOR_ESTADO["NORMAL"])["hex"]}"></span>{l["nombre"]}</span>'
    for l in localidades.values()
)
st.markdown(chips, unsafe_allow_html=True)

# ---------------------------------------------------------------------
# DETALLE POR LOCALIDAD
# ---------------------------------------------------------------------
st.markdown("---")
st.markdown(
    '<div class="section-eyebrow">Detalle</div>'
    '<div class="section-title">📍 Detalle por localidad</div>',
    unsafe_allow_html=True,
)

for clave, loc in localidades.items():
    aviso = "" if loc["conectado"] else " · ⚠️ dato de referencia"
    with st.expander(f"{loc['emoji']} {loc['nombre']} — {loc['estado']}{aviso}"):
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Nivel actual:** {loc['nivel_metros']} m")
            st.write(f"**Umbral de alerta:** {loc['umbral_alerta']} m")
            st.write(f"**Umbral de evacuación:** {loc['umbral_evacuacion']} m")
        with c2:
            st.write(f"**Fuente:** {loc['fuente']}")
            st.write(f"**Última verificación:** {loc['ultima_verificacion']}")
            st.write(f"**Conectado en vivo:** {'Sí' if loc['conectado'] else 'No'}")
        st.markdown("**📊 Análisis:**")
        st.markdown(
            analizar(
                loc["nombre"], loc["nivel_metros"], loc["umbral_alerta"], loc["umbral_evacuacion"],
                loc["estado"], fase_oni_actual, mes_actual,
            )
        )

st.markdown(
    '<div class="footer-note">Este portal y el bot de Telegram @cuencas_chaco_bot '
    'comparten el mismo backend, para que la información sea siempre consistente '
    'entre ambas herramientas.</div>',
    unsafe_allow_html=True,
)
