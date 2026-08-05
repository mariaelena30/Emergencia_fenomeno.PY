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
    "NORMAL": {"hex": "#3FBF83", "folium": "green", "label": "Normal"},
    "ALERTA": {"hex": "#F5A623", "folium": "orange", "label": "Alerta"},
    "EVACUACION": {"hex": "#E4543A", "folium": "red", "label": "Evacuación"},
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

.stApp {
    background: radial-gradient(circle at 15% 0%, #123B47 0%, #0B2E38 45%, #081F27 100%);
    color: #F4F7F5;
}

/* Hero */
.hero-wrap { padding: 2.2rem 0 1.2rem 0; }
.hero-eyebrow {
    font-family: 'Inter', sans-serif; font-weight: 600; letter-spacing: .14em;
    text-transform: uppercase; font-size: .72rem; color: #7FD4E8;
    margin-bottom: .6rem; display:block;
}
.hero-title {
    font-family: 'Fraunces', serif; font-weight: 700; font-size: 3rem;
    line-height: 1.05; color: #F4F7F5; margin: 0 0 .5rem 0;
}
.hero-sub {
    font-family: 'Inter', sans-serif; font-size: 1.02rem; color: #9FBFC4;
    max-width: 640px; line-height: 1.5;
}
.wave-divider {
    width: 100%; height: 34px; margin: 1.4rem 0 .4rem 0; opacity: .55;
}

/* Section headers */
.section-eyebrow {
    font-family: 'Inter', sans-serif; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; font-size: .72rem; color: #35A7C4; margin-bottom: .15rem;
}
.section-title {
    font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.6rem;
    color: #F4F7F5; margin: 0 0 1rem 0;
}

/* Gauge card por cuenca */
.gauge-card {
    background: linear-gradient(160deg, #16424F 0%, #113440 100%);
    border: 1px solid rgba(127, 212, 232, 0.12);
    border-radius: 16px; padding: 1.1rem 1.2rem 1.3rem 1.2rem;
    margin-bottom: .9rem;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}
.gauge-top { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:.35rem; }
.gauge-name { font-family:'Fraunces', serif; font-weight:600; font-size:1.15rem; color:#F4F7F5; }
.gauge-badge {
    font-family:'Inter', sans-serif; font-weight:700; font-size:.68rem; letter-spacing:.06em;
    text-transform: uppercase; padding: .18rem .55rem; border-radius: 999px; color:#0B2E38;
}
.gauge-station { font-size:.8rem; color:#8FB4BA; margin-bottom:.7rem; }
.gauge-track {
    position: relative; width:100%; height:14px; border-radius:999px;
    background: rgba(255,255,255,0.08); overflow: visible; margin-bottom: .35rem;
}
.gauge-fill { position:absolute; left:0; top:0; height:100%; border-radius:999px; transition: width .3s ease; }
.gauge-tick {
    position:absolute; top:-4px; width:2px; height:22px; background: rgba(244,247,245,0.5);
}
.gauge-tick-label {
    position:absolute; top:16px; font-size:.62rem; color:#8FB4BA; transform: translateX(-50%);
    white-space: nowrap;
}
.gauge-value { font-family:'Fraunces', serif; font-weight:700; font-size:1.4rem; color:#F4F7F5; margin-top:1.6rem; }
.gauge-foot { font-size:.72rem; color:#7C9EA4; margin-top:.5rem; }

/* Localidad chip list */
.loc-chip {
    display:inline-flex; align-items:center; gap:.4rem;
    background: rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08);
    border-radius: 999px; padding:.3rem .7rem; margin: .15rem .3rem .15rem 0;
    font-size:.82rem; color:#E7F1F2;
}
.loc-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }

.footer-note { font-size:.78rem; color:#6E9297; text-align:center; padding: 1.4rem 0 .6rem 0; }

hr { border-color: rgba(255,255,255,0.08) !important; }
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


def gauge_html(nombre: str, estacion: str, nivel: float, umbral_alerta: float,
                umbral_evac: float, estado: str, fuente: str, conectado: bool,
                actualizado: str) -> str:
    estilo = COLOR_ESTADO.get(estado, COLOR_ESTADO["NORMAL"])
    tope = max(umbral_evac * 1.18, nivel * 1.05)
    pct_nivel = min(nivel / tope * 100, 100)
    pct_alerta = min(umbral_alerta / tope * 100, 100)
    pct_evac = min(umbral_evac / tope * 100, 100)
    etiqueta_conexion = "✅ En vivo" if conectado else "⚠️ Dato de referencia"
    return f"""
    <div class="gauge-card">
      <div class="gauge-top">
        <span class="gauge-name">{nombre}</span>
        <span class="gauge-badge" style="background:{estilo['hex']}">{estilo['label']}</span>
      </div>
      <div class="gauge-station">{estacion}</div>
      <div class="gauge-track">
        <div class="gauge-fill" style="width:{pct_nivel:.1f}%; background:{estilo['hex']};"></div>
        <div class="gauge-tick" style="left:{pct_alerta:.1f}%; background:#F5A623;"></div>
        <div class="gauge-tick-label" style="left:{pct_alerta:.1f}%;">Alerta {umbral_alerta}m</div>
        <div class="gauge-tick" style="left:{pct_evac:.1f}%; background:#E4543A;"></div>
        <div class="gauge-tick-label" style="left:{pct_evac:.1f}%;">Evac. {umbral_evac}m</div>
      </div>
      <div class="gauge-value">{nivel} m</div>
      <div class="gauge-foot">{etiqueta_conexion} · {fuente}<br/>Actualizado: {actualizado}</div>
    </div>
    """


@st.cache_data(ttl=60)
def cargar_datos():
    """
    Trae cuencas y localidades del backend. Si falla, devuelve None y
    el dashboard lo va a decir con todas las letras -no va a mostrar
    numeros inventados disfrazados de datos reales.
    """
    try:
        r_cuencas = requests.get(f"{BACKEND_URL}/cuencas", timeout=8.0)
        r_localidades = requests.get(f"{BACKEND_URL}/localidades", timeout=8.0)
        r_cuencas.raise_for_status()
        r_localidades.raise_for_status()
        return r_cuencas.json(), r_localidades.json()
    except Exception:
        return None, None


# ---------------------------------------------------------------------
# HERO
# ---------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-wrap">
        <span class="hero-eyebrow">HackLab + Hackathon 2026 · 2HC26</span>
        <h1 class="hero-title">Portal Hídrico Chaco</h1>
        <p class="hero-sub">Monitoreo en vivo de las 4 cuencas principales y 12 localidades
        de riesgo de la provincia, con la misma información que ves en el bot de Telegram
        @cuencas_chaco_bot.</p>
    </div>
    <svg class="wave-divider" viewBox="0 0 1200 40" preserveAspectRatio="none">
        <path d="M0,20 C150,40 350,0 600,20 C850,40 1050,0 1200,20 L1200,40 L0,40 Z" fill="#35A7C4"/>
    </svg>
    """,
    unsafe_allow_html=True,
)

datos_cuencas, datos_localidades = cargar_datos()

if datos_cuencas is None:
    st.error(
        "⚠️ No se pudo conectar con el backend en este momento. "
        "Si el servicio estaba dormido por inactividad (plan gratuito de Render), "
        "puede tardar hasta 50 segundos en despertar. Volve a cargar la pagina en un momento."
    )
    st.stop()

cuencas = datos_cuencas["cuencas"]
explicaciones = datos_cuencas["explicaciones"]
localidades = datos_localidades["localidades"]

# ---------------------------------------------------------------------
# TRANSPARENCIA SOBRE LOS DATOS
# ---------------------------------------------------------------------
con_conexion = sum(1 for c in cuencas.values() if c["conectado"])
if con_conexion == 0:
    st.info(
        "ℹ️ **Sobre estos datos:** todos los valores que ves abajo son datos de "
        "*referencia* (semilla), cargados manualmente para poder demostrar el "
        "sistema mientras se integra una fuente en vivo. Ninguno esta conectado "
        "todavia a una fuente automatica en tiempo real — cada tarjeta lo indica."
    )

col_a, col_b = st.columns(2)
with col_a:
    with st.expander("📖 ¿Que significa cada dato? (para quien no es tecnico)"):
        for clave, texto in explicaciones.items():
            st.markdown(f"**{clave.replace('_', ' ').capitalize()}:** {texto}")
    with st.expander("🚨 ¿Que hacer segun el estado? (protocolo general)"):
        st.markdown(
            """
Guia **general y orientativa**, no un protocolo oficial. Ante cualquier
alerta real, la indicacion valida es siempre la que emita **Defensa Civil
de tu localidad**.

- 🟢 **NORMAL:** monitoreo pasivo, sin accion especial.
- 🟡 **ALERTA:** revisa lo esencial (documentos, medicamentos, ropa) y
  estate atento a los canales oficiales.
- 🔴 **EVACUACION:** segui estrictamente las indicaciones de Defensa Civil
  y autoridades locales.
"""
        )
with col_b:
    with st.expander("🌎 Contexto: ¿en que se basa este sistema de alerta?"):
        st.markdown(
            """
Este portal usa la misma logica de **3 niveles** (normal, alerta, evacuacion)
que emplea el **Sistema de Informacion y Alerta Hidrologico (SIyAH)** del
Instituto Nacional del Agua (INA), que desde 1983 monitorea la Cuenca del
Plata en cinco paises y emite pronosticos usados por Defensa Civil en toda
la region.

Es una **herramienta complementaria y de demostracion** -no reemplaza el
reporte oficial de INA, consultable en alerta.ina.gob.ar.

**Fuente:** Instituto Nacional del Agua (INA).
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
for col, (clave, c) in zip(cols, cuencas.items()):
    with col:
        st.markdown(
            gauge_html(
                c["nombre"], c["estacion"], c["nivel_metros"], c["umbral_alerta"],
                c["umbral_evacuacion"], c["estado"], c["fuente"], c["conectado"],
                c["ultima_verificacion"],
            ),
            unsafe_allow_html=True,
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
    etiqueta_conexion = "En vivo" if loc["conectado"] else "Dato de referencia, sin conexion automatica aun"
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
            st.write(f"**Umbral de evacuacion:** {loc['umbral_evacuacion']} m")
        with c2:
            st.write(f"**Fuente:** {loc['fuente']}")
            st.write(f"**Ultima verificacion:** {loc['ultima_verificacion']}")
            st.write(f"**Conectado en vivo:** {'Si' if loc['conectado'] else 'No'}")

st.markdown(
    '<div class="footer-note">Este portal y el bot de Telegram @cuencas_chaco_bot '
    'comparten el mismo backend, para que la informacion sea siempre consistente '
    'entre ambas herramientas.</div>',
    unsafe_allow_html=True,
)
