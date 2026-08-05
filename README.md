# 🌊 Emergencia_fenomeno.PY

## Sistema de Monitoreo Institucional - Contingencia Hídrica (Chaco 2026)

Panel operativo desarrollado para el HackLab + Hackathon 2026 (2HC26), pensado
como herramienta complementaria de alerta temprana para la gestión del riesgo
hídrico en la Provincia del Chaco.

El dashboard consulta en tiempo real el estado de las **4 cuencas principales**
de la provincia (Paraná, Paraguay, Bermejo y Pilcomayo) y **12 localidades de
riesgo** (Resistencia, Barranqueras, Corrientes, Formosa, Puerto Bermejo, El
Sauzalito, Isla del Cerrito, Puerto Vilelas, La Leonesa, Pampa del Indio,
Villa Río Bermejito y Fuerte Esperanza), clasificando automáticamente cada
punto en tres niveles: 🟢 Normal, 🟡 Alerta, 🔴 Evacuación.

## 🏗️ Arquitectura del sistema

Este proyecto **comparte backend** con el bot de Telegram
[@cuencas_chaco_bot](https://t.me/cuencas_chaco_bot), para que ambas
herramientas muestren siempre la misma información, sin datos duplicados
ni desincronizados.

- **Backend (fuente de datos):** repositorio
  [`cuencas-bot`](https://github.com/mariaelena30/cuencas-bot), desplegado en
  producción en `https://cuencas-bot.onrender.com`. Desarrollado con FastAPI,
  centraliza los datos de las 4 cuencas y las 12 localidades.
- **Frontend (este repo):** `app_dashboard.py`, desarrollado con Streamlit.
  Consume los endpoints `/cuencas` y `/localidades` del backend para generar
  tarjetas métricas y un mapa interactivo con Folium, coloreando los
  marcadores según los umbrales de alerta de cada punto.
- `main.py` en este repo es una **copia de referencia** del backend (mismo
  código que `cuencas-bot`), guardada por prolijidad — no se ejecuta en el
  despliegue de Streamlit Cloud, que solo corre `app_dashboard.py`.

## ⚠️ Sobre los datos

Los valores que muestra el dashboard son, por el momento, **datos de
referencia** (semilla), cargados para poder demostrar el sistema mientras se
integra una fuente en vivo (INA, Prefectura Naval, Defensa Civil provincial).
Cada tarjeta y cada marcador del mapa lo indica explícitamente — nunca se
etiquetan como datos oficiales confirmados sin serlo.

## 🛠️ Tecnologías utilizadas

- Python 3.11+
- Streamlit — panel operativo
- Folium & streamlit-folium — mapa interactivo geoespacial
- Requests — consumo del backend

## 🚀 Instalación y ejecución local

```bash
pip install -r requirements.txt
streamlit run app_dashboard.py
```

El dashboard se conecta directo al backend en producción
(`https://cuencas-bot.onrender.com`), así que no hace falta levantar nada
más en local para probarlo.

## 🗺️ Umbrales operativos de alerta

Cada cuenca y localidad tiene su propio umbral, definido en metros. La
clasificación sigue la misma lógica de tres niveles que usa el Sistema de
Información y Alerta Hidrológico (SIyAH) del Instituto Nacional del Agua
(INA), vigente desde 1983 para el monitoreo de la Cuenca del Plata:

- 🟢 **NORMAL** — por debajo del umbral de alerta. Monitoreo pasivo.
- 🟡 **ALERTA** — nivel igual o superior al umbral de alerta de esa
  cuenca/localidad. Momento de prestar atención y estar informado.
- 🔴 **EVACUACIÓN** — nivel igual o superior al umbral de evacuación. Seguir
  las indicaciones de Defensa Civil.

Esta es una guía orientativa del sistema; ante cualquier alerta real, la
indicación válida siempre es la que emita Defensa Civil de tu localidad.

## 🔗 Proyectos relacionados

- Bot de Telegram: [@cuencas_chaco_bot](https://t.me/cuencas_chaco_bot)
- Backend / fuente de datos: [cuencas-bot](https://github.com/mariaelena30/cuencas-bot)

---

Desarrollado para la Iniciativa Tecnológica Local - Chaco 2026 🚀
