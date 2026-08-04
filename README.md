# Emergencia_fenomeno.PY
# 🌊 Sistema de Monitoreo Institucional - Contingencia Hídrica (Barranqueras 2026)

Este proyecto es una arquitectura de software *end-to-end* diseñada para el **HackLab + Hackathon 2026 (2HC26)**. Consiste en una plataforma de contingencia para la gestión del riesgo de inundaciones en la cuenca de Barranqueras (Chaco), combinando un motor de datos de alta velocidad en **FastAPI** con un panel operativo geoespacial e interactivo desarrollado en **Streamlit**.

La plataforma unifica lecturas hidrométricas oficiales en tiempo real, análisis satelital preliminar de índices de vegetación (NDVI/Sentinel-2) y anomalías macroclimáticas globales (Índice ONI de la NOAA) para actuar como una herramienta clave en la toma de decisiones de Defensa Civil.

---

## 🏗️ Arquitectura del Sistema

El ecosistema se divide en dos componentes independientes que se comunican de forma asincrónica mediante peticiones HTTP REST:

1. **Backend (`main.py`):** Desarrollado con FastAPI. Actúa como una base de datos en memoria (RAM) de alta velocidad que centraliza la caché de respaldo institucional. Implementa validación estricta de datos mediante Pydantic y un ciclo de vida (`lifespan`) asincrónico para sincronizarse con servicios meteorológicos internacionales.
2. **Frontend (`app_dashboard.py`):** Desarrollado con Streamlit. Consume los endpoints del backend en tiempo real para generar tarjetas métricas operativas y un mapa interactivo geoespacial utilizando **Folium**, automatizando el cambio de color en los marcadores según los umbrales de alerta del Instituto Nacional del Agua (INA).

---

## 🛠️ Tecnologías Utilizadas

* **Python 3.14+** como lenguaje base del ecosistema.
* **FastAPI** para el ruteo y exposición de la API de contingencia.
* **Pydantic** para garantizar la integridad y validación de tipos de datos.
* **Streamlit** para la construcción ágil del entorno gráfico para los tomadores de decisiones.
* **Folium & Streamlit-Folium** para el renderizado dinámico de mapas y capas espaciales.
* **Httpx & Requests** para el consumo de servicios web y comunicación entre componentes.

---

## 🚀 Instrucciones de Instalación y Despliegue Local

### 1. Clonar el repositorio e instalar dependencias
Asegúrese de contar con Python instalado en su sistema operativo. Ejecute el siguiente comando para forzar la instalación correcta de las librerías necesarias:

```bash
python -m pip install fastapi uvicorn httpx pydantic streamlit streamlit-folium folium requests
```

### 2. Iniciar el Servidor de Datos (Backend)
Abra una terminal dentro de la carpeta del proyecto y encienda el motor de FastAPI mediante Uvicorn:

```bash
python -m uvicorn main:app --reload
```
*El servidor estará disponible en la dirección local: `http://127.0.0.1:8000`*
*Puede acceder a la documentación interactiva autogenerada en: `http://127.0.0`*

### 3. Iniciar el Panel Operativo (Frontend)
Abra una **segunda terminal** en VS Code sin apagar el backend y ponga en marcha la interfaz gráfica:

```bash
python -m streamlit run app_dashboard.py
```
*El sistema compilará los módulos y abrirá automáticamente su navegador web en la dirección: `http://localhost:8501`*

---

## 🗺️ Umbrales Operativos de Alerta (Estación Barranqueras)

El sistema clasifica automáticamente el estado de la cuenca según las lecturas del hidrómetro oficial en base a los parámetros de Prefectura Naval Argentina:

*   🟢 **Estado NORMAL (< 6.00 metros):** Marcador Verde. Operación habitual y monitoreo pasivo.
*   🟡 **Estado de ALERTA (≥ 6.00 metros):** Marcador Naranja. Despliegue preventivo de cuadrillas.
*   🔴 **Estado de EVACUACIÓN (≥ 6.50 metros):** Marcador Rojo. Activación automática del protocolo de contingencia y rescate institucional.

---
**Desarrollado para la Iniciativa Tecnológica Local - Chaco 2026** 🚀
