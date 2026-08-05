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

st.set_page_config(page_title="Portal Hidrico Chaco", layout="wide")

# URL publica y correcta del backend en produccion (Render).
BACKEND_URL = "https://cuencas-bot.onrender.com"

# Coordenadas de cada localidad monitoreada, para pintarlas en el mapa.
# Nota: algunas (El Sauzalito, Fuerte Esperanza, Villa Rio Bermejito,
# Pampa del Indio, Puerto Bermejo) son aproximadas, tomadas de fuentes
# publicas generales; conviene verificarlas con GPS si se van a usar
# para algo mas preciso que la ubicacion aproximada en el mapa.
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

COLOR_POR_ESTADO = {"NORMAL": "green", "ALERTA": "orange", "EVACUACION": "red"}
EMOJI_POR_ESTADO = {"NORMAL": "🟢", "ALERTA": "🟡", "EVACUACION": "🔴"}


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


st.title("🌊 Portal Hidrico Chaco")
st.markdown(
    "#### Monitoreo de las 4 cuencas y 12 localidades de riesgo de la provincia | "
    "HackLab + Hackathon 2026 (2HC26)"
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
# DE DONDE SALEN ESTOS DATOS (transparencia, nada de "oficial" sin serlo)
# ---------------------------------------------------------------------
con_conexion = sum(1 for c in cuencas.values() if c["conectado"])
if con_conexion == 0:
    st.info(
        "ℹ️ **Sobre estos datos:** todos los valores que ves abajo son datos de "
        "*referencia* (semilla), cargados manualmente para poder demostrar el "
        "sistema mientras se integra una fuente en vivo. Ninguno esta conectado "
        "todavia a una fuente automatica en tiempo real — cada tarjeta lo indica."
    )

with st.expander("📖 ¿Que significa cada dato? (para quien no es tecnico)"):
    for clave, texto in explicaciones.items():
        st.markdown(f"**{clave.replace('_', ' ').capitalize()}:** {texto}")

with st.expander("🌎 Contexto: ¿en que se basa este sistema de alerta?"):
    st.markdown(
        """
Este portal usa la misma logica de **3 niveles** (normal, alerta, evacuacion)
que emplea el **Sistema de Informacion y Alerta Hidrologico (SIyAH)** del
Instituto Nacional del Agua (INA), que desde 1983 monitorea la Cuenca del
Plata en cinco paises (Argentina, Bolivia, Brasil, Paraguay y Uruguay) y
emite pronosticos usados por Defensa Civil y organismos de emergencia en
toda la region.

En los reportes reales de INA, cada estacion tiene su propio umbral de
alerta y de evacuacion medido en metros -por ejemplo Formosa: alerta 7,80 m,
evacuacion 8,30 m- exactamente el mismo esquema que usamos aca para cada
cuenca y localidad de Chaco. La diferencia es que este proyecto es una
**herramienta complementaria y de demostracion**, pensada para que
cualquier persona -no solo un tecnico- consulte el estado en segundos
desde el celular; no reemplaza al reporte oficial de INA, que se puede
consultar directamente en alerta.ina.gob.ar.

**Fuente:** Instituto Nacional del Agua (INA) - Sistema de Informacion y
Alerta Hidrologico de la Cuenca del Plata.
"""
    )

with st.expander("🚨 ¿Que hacer segun el estado? (protocolo general)"):
    st.markdown(
        """
Esta es una guia **general y orientativa**, no un protocolo oficial. Ante
cualquier alerta real, la indicacion valida es siempre la que emita
**Defensa Civil de tu localidad**.

- 🟢 **NORMAL:** situacion habitual. No se requiere ninguna accion especial,
  mas alla de mantenerse informado si hay pronostico de lluvias fuertes.
- 🟡 **ALERTA:** el nivel del rio supero el umbral de atencion. Es buen
  momento para revisar que tener a mano lo esencial (documentos, medicamentos,
  algo de ropa) y estar atento a los canales oficiales de tu municipio o
  Defensa Civil.
- 🔴 **EVACUACION:** el nivel supero el umbral critico. Seguir estrictamente
  las indicaciones de Defensa Civil y autoridades locales; no esperar a
  confirmar el dato por una segunda fuente antes de actuar.
"""
    )

st.markdown("---")

# ---------------------------------------------------------------------
# ESTADO DE LAS 4 CUENCAS
# ---------------------------------------------------------------------
st.markdown("### 🌊 Estado de las 4 cuencas")
cols = st.columns(4)
for col, (clave, c) in zip(cols, cuencas.items()):
    with col:
        etiqueta_conexion = "✅ En vivo" if c["conectado"] else "⚠️ Dato de referencia"
        st.metric(
            label=f"{c['emoji']} {c['nombre']}",
            value=f"{c['nivel_metros']} m",
            delta=c["estado"],
        )
        st.caption(f"{c['estacion']} · {etiqueta_conexion}")
        st.caption(f"Fuente: {c['fuente']} · Actualizado: {c['ultima_verificacion']}")

st.markdown("---")

# ---------------------------------------------------------------------
# MAPA CON LAS 12 LOCALIDADES
# ---------------------------------------------------------------------
st.markdown("### 🗺 Mapa de localidades monitoreadas")

mapa = folium.Map(location=[-26.5, -59.5], zoom_start=6)

for clave, loc in localidades.items():
    if clave not in COORDENADAS:
        continue
    lat, lon = COORDENADAS[clave]
    color = COLOR_POR_ESTADO.get(loc["estado"], "gray")
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
        icon=folium.Icon(color=color, icon="tint"),
    ).add_to(mapa)

st_folium(mapa, width=1100, height=500)

st.caption(
    "🟢 Normal · 🟡 Alerta · 🔴 Evacuacion — clasificacion automatica segun umbrales "
    "de cada localidad. Hace clic en un marcador para ver el detalle."
)

# ---------------------------------------------------------------------
# DETALLE POR LOCALIDAD (tabla expandible)
# ---------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📍 Detalle por localidad")

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

st.markdown("---")
st.caption(
    "Este portal y el bot de Telegram @cuencas_chaco_bot comparten el mismo backend, "
    "para que la informacion sea siempre consistente entre ambas herramientas."
)
