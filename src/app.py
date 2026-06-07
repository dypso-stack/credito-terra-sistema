"""
Interfaz Web — Estimador Preliminar Crédito Terra
Banco Guayaquil

QUÉ HACE ESTE SCRIPT
--------------------
Es la interfaz del Flujo 2 (estimación preliminar). Permite a analistas y
clientes interesados obtener una estimación de indicadores ambientales y de
viabilidad ANTES del levantamiento formal de la ficha. Toda la lógica de
cálculo vive en modelo_estimacion.estimar_proyecto(); este archivo solo arma
la pantalla y muestra los resultados.

CÓMO SE EJECUTA (de arriba hacia abajo)
---------------------------------------
Streamlit re-corre el script completo en cada interacción:
    1. Configura la página y los estilos CSS corporativos.
    2. Muestra el estado del modelo ML (activo, o pendiente de 200 casos).
    3. Pinta el formulario de 7 parámetros.
    4. Al pulsar "Estimar proyecto", llama a estimar_proyecto() y despliega
       indicadores, equivalencias y la recomendación de viabilidad.

Uso:
    streamlit run src/app.py
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import streamlit as st
from modelo_estimacion import estimar_proyecto, cargar_modelos

# Configuración de la página
st.set_page_config(
    page_title="Herramienta de estimación preliminar",
    page_icon="🌱",
    layout="centered",
)

# Estilos CSS corporativos. Las clases .resultado-alto / -medio / -bajo colorean
# el recuadro del dictamen según el nivel de viabilidad (verde / amarillo / rojo).
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #D4007A, #8B0057);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #D4007A;
        margin-bottom: 0.5rem;
    }
    .resultado-alto {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 8px;
    }
    .resultado-medio {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 8px;
    }
    .resultado-bajo {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Encabezado
st.markdown("""
<div class="main-header">
    <h2>🌱 Herramienta de estimación preliminar — Crédito Terra</h2>
    <p>Banco Guayaquil</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
Esta herramienta estima los indicadores ambientales y la viabilidad de elegibilidad
de un proyecto fotovoltaico **antes del levantamiento formal de la ficha**.

> ⚠️ Los resultados son orientativos. La evaluación oficial se realiza con la ficha completa FLI CT-001.
""")

# Estado del modelo
modelos = cargar_modelos()
if modelos:
    st.success(
        f"✅ Modelo ML activo — Entrenado con "
        f"{modelos['metricas']['n_casos_entrenamiento']} casos | "
        f"Precisión: {modelos['metricas']['precision_elegibilidad']}%"
    )
else:
    st.warning(
        "⚠️ Modelo ML no disponible aún. "
        "La estimación se basará en indicadores físicos. "
        "El modelo se activa con 200 casos evaluados (Riley et al., 2019)."
    )

st.divider()

# Formulario de entrada
st.subheader("📋 Datos del Proyecto")

col1, col2 = st.columns(2)

with col1:
    sector = st.selectbox("Sector del cliente", [
        'INDUSTRIA ALIMENTICIA', 'AGROPECUARIO', 'BANANO', 'CACAO', 'CAMARÓN',
        'CONSTRUCCIÓN', 'COMERCIO EN GENERAL', 'LOGÍSTICA Y TRANSPORTE',
        'INDUSTRIA FLORÍCOLA', 'INDUSTRIAS MANUFACTURERAS', 'SERVICIOS ESENCIALES',
        'INDUSTRIA DE LA PESCA', 'INDUSTRIA FARMACÉUTICA',
    ])

    segmento = st.selectbox("Segmento del cliente", [
        'Corporativo', 'Empresarial', 'PYME'
    ])

    tipo_sistema = st.selectbox("Tipo de sistema fotovoltaico", [
        'Conectado a la red (SFCR)',
        'Autónomo (SFA)',
        'Híbrido (SFH)',
    ])

with col2:
    etapa = st.selectbox("Etapa del proyecto", [
        'Prefactibilidad', 'Factibilidad', 'Ejecución', 'Operación'
    ])

    capacidad_mwp = st.number_input(
        "Capacidad instalada (MWp)",
        min_value=0.05, max_value=10.0, value=1.0, step=0.05,
        help="Potencia pico del sistema en megavatios"
    )

    consumo_cliente = st.number_input(
        "Consumo eléctrico anual del cliente (MWh/año)",
        min_value=50.0, max_value=50000.0, value=2000.0, step=100.0,
    )

monto_aproximado = st.number_input(
    "Monto aproximado del crédito solicitado (USD)",
    min_value=10000.0, max_value=10000000.0, value=500000.0, step=10000.0,
    format="%.0f"
)

st.divider()

# Botón de estimación. Todo lo que está dentro de este if solo se ejecuta cuando
# el usuario pulsa el botón (Streamlit re-corre el script completo en cada clic).
if st.button("🔍 Estimar proyecto", type="primary", use_container_width=True):

    with st.spinner("Calculando estimación..."):
        resultado = estimar_proyecto(
            sector=sector,
            segmento=segmento,
            tipo_sistema=tipo_sistema,
            etapa=etapa,
            capacidad_mwp=capacidad_mwp,
            consumo_cliente_mwh=consumo_cliente,
            monto_aproximado=monto_aproximado,
        )

    st.subheader("📊 Resultados de la estimación")

    # Dictamen de viabilidad
    nivel = resultado['nivel_viabilidad']
    clase_css = {
        'ALTO': 'resultado-alto',
        'MEDIO': 'resultado-medio',
        'BAJO': 'resultado-bajo',
        'N/D': 'resultado-medio',
    }.get(nivel, 'resultado-medio')

    icono = {'ALTO': '✅', 'MEDIO': '⚠️', 'BAJO': '❌', 'N/D': 'ℹ️'}.get(nivel, 'ℹ️')

    st.markdown(f"""
    <div class="{clase_css}">
        <h3>{icono} Viabilidad: {nivel}</h3>
        <p><strong>{resultado['recomendacion']}</strong></p>
        {f"<p>Probabilidad estimada de elegibilidad: <strong>{resultado['probabilidad_elegible_pct']}%</strong></p>" 
         if resultado['probabilidad_elegible_pct'] else ""}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ─── Indicadores ambientales ─────────────────────────────────────
    st.subheader("🌿 Indicadores ambientales estimados")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Energía renovable/año",
            f"{resultado['energia_estimada_mwh']:,.0f} MWh",
        )
        st.metric(
            "Capacidad instalada",
            f"{resultado['capacidad_kwp']:,.0f} kWp",
        )
    with col2:
        st.metric(
            "GEI evitadas/año",
            f"{resultado['gei_anual_estimado_tco2']:,.1f} tCO₂",
        )
        st.metric(
            "GEI evitadas (vida útil)",
            f"{resultado['gei_total_estimado_tco2']:,.1f} tCO₂",
        )
    with col3:
        st.metric(
            "Cobertura energética",
            f"{resultado['cobertura_estimada_pct']:.1f}%",
        )
        st.metric(
            "Ahorro estimado/año",
            f"${resultado['ahorro_anual_estimado_usd']:,.0f}",
        )

    # Equivalencias
    st.divider()
    st.subheader("🌳 Equivalencias de impactos positivos")
    gei_total = resultado['gei_total_estimado_tco2']
    energia_anual = resultado['energia_estimada_mwh']

    # Equivalencias divulgativas: 45 árboles ≈ 1 tCO₂ capturada al año;
    # 1,2 MWh ≈ consumo eléctrico anual de un hogar promedio.
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"🌳 **{int(gei_total * 45):,} árboles** plantados")
    with col2:
        st.info(f"🏠 **{int(energia_anual / 1.2):,} hogares** con electricidad abastecidos en un año")

    # Nota metodológica
    st.divider()
    st.caption(f"ℹ️ {resultado['nota']}")
    st.caption(
        "Esta estimación no reemplaza el levantamiento formal de información. "
        "Para iniciar el proceso oficial, contacte a Banco Guayaquil."
    )
