import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Portal Hídrico Chaco", layout="wide")

# URL directa al endpoint de consulta del bot
BACKEND_URL = "http://127.0.0"

st.title("🌊 Portal Operativo de Riesgo Hídrico - Barranqueras")
st.markdown("### HackLab + Hackathon 2026 (2HC26) | Monitoreo en Tiempo Real")

# Consumo de datos desde el backend local
try:
    respuesta = requests.get(BACKEND_URL, timeout=5.0)
    datos = respuesta.json()
    clima = datos["clima"]
    hidro = datos["hidrologia"]
    sat = datos["satelital_ndvi"]
except Exception as e:
    st.error(f"❌ No se pudo recibir información del backend en el puerto 8000. Error: {e}")
    st.stop()

# Fila superior de indicadores métricos
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label=f"🌊 Nivel ({hidro['estacion']})", value=f"{hidro['nivel_metros']} m", delta=hidro["estado"])
with col2:
    st.metric(label="🛰️ NDVI Promedio (Sentinel-2)", value=sat["ndvi_promedio"], delta=sat["condicion_vegetacion"])
with col3:
    st.metric(label="🌍 Índice ONI Pacífico (NOAA)", value=f"{clima['ultimo_valor_oni']} °C", delta=clima["fase_oni"])

st.markdown("---")
st.markdown("### 🗺️ Estado Geográfico de Alerta en Cuenca")

# Coordenadas geográficas exactas de Barranqueras
lat_barranqueras = -27.4815
lon_barranqueras = -58.9324

mapa = folium.Map(location=[lat_barranqueras, lon_barranqueras], zoom_start=13)

# Clasificación lógica de alertas para el color del marcador
if hidro["nivel_metros"] >= hidro["umbral_evacuacion"]:
    color_marcador = "red"
elif hidro["nivel_metros"] >= hidro["umbral_alerta"]:
    color_marcador = "orange"
else:
    color_marcador = "green"

folium.Marker(
    location=[lat_barranqueras, lon_barranqueras],
    popup=f"<b>{hidro['estacion']}</b><br>Nivel: {hidro['nivel_metros']}m<br>Estado: {hidro['estado']}",
    tooltip="Clic para ver detalles",
    icon=folium.Icon(color=color_marcador, icon="tint")
).add_to(mapa)

st_folium(mapa, width=1100, height=450)
