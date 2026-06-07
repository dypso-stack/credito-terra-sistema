"""
Módulo: Modelo de Estimación Preliminar
Crédito Terra - Banco Guayaquil

QUÉ HACE ESTE MÓDULO
--------------------
Es el motor del Flujo 2 (estimación preliminar). Con unos pocos datos que el
analista obtiene en una primera conversación, estima los indicadores
ambientales y la PROBABILIDAD de que el proyecto sea elegible — antes de
levantar la ficha formal. Lo usa la interfaz web (app.py).

IMPORTANTE — QUÉ ES Y QUÉ NO ES
-------------------------------
El ML (Random Forest) es una DEMOSTRACIÓN METODOLÓGICA, no el mecanismo oficial
de decisión (ese es el sistema experto de motor_elegibilidad). Aquí solo
ORIENTA al analista. Por eso:
- Requiere mínimo 200 casos para entrenar (Riley et al., 2019). Si no los hay,
  la estimación cae a indicadores físicos y la parte de probabilidad se omite.
- Re-entrenar cada 150 casos nuevos o si la precisión baja del 80%, SIEMPRE con
  validación humana (nunca automático: sería incompatible con la auditabilidad).

TRES MODELOS DENTRO DE UN MISMO .pkl
------------------------------------
- clasificador     : probabilidad de elegibilidad (Random Forest classifier).
- regresor_gei     : GEI evitadas/año (Random Forest regressor).
- regresor_cobertura: cobertura energética % (Random Forest regressor).

CONTENIDO
---------
- SECTORES_RIESGO / ETAPAS_NUM / TIPOS_NUM / SEGMENTOS_NUM : codificación de
  variables categóricas a números (el modelo no entiende texto).
- preparar_features() : crea las columnas que consume el modelo.
- entrenar_modelos()  : entrena y guarda los 3 modelos en disco (.pkl).
- cargar_modelos()    : carga el .pkl entrenado.
- estimar_proyecto()  : función que usa la web; calcula indicadores + predicción.

Basado en: Riley et al. (2019) - mínimo 200 casos para primer entrenamiento.
Re-entrenamiento: cada 150 casos nuevos o cuando precisión baje del 80%.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import warnings
warnings.filterwarnings('ignore')

MODEL_PATH = "models/modelo_estimacion.pkl"

FACTOR_EMISION = 0.4567

# Variables de entrada para el modelo
FEATURES_REGRESION = [
    'capacidad_instalada_mwp',
    'consumo_cliente_mwh_anio',
    'vida_util_anios',
    'capex_usd',
    'tarifa_electrica_usd_kwh',
]

FEATURES_CLASIFICACION = [
    'capacidad_instalada_mwp',
    'cobertura_energetica_pct',
    'capex_usd',
    'monto_credito_usd',
    'vida_util_anios',
    'tarifa_electrica_usd_kwh',
    'ahorro_anual_usd',
]

# --- Codificación de variables categóricas a número ---
# El Random Forest no entiende texto, así que cada categoría se mapea a un entero.
# SECTORES_RIESGO: nivel de riesgo socioambiental del sector (0 = menor, 3 = mayor).
# Un sector más riesgoso tiende a fallar más criterios de exclusión (SARAS, IFC, etc.).
SECTORES_RIESGO = {
    'INDUSTRIA ALIMENTICIA': 0,
    'AGROPECUARIO': 0,
    'BANANO': 0,
    'CACAO': 0,
    'CAMARÓN': 1,
    'CONSTRUCCIÓN': 2,
    'COMERCIO EN GENERAL': 0,
    'LOGÍSTICA Y TRANSPORTE': 1,
    'INDUSTRIA FLORÍCOLA': 0,
    'INDUSTRIAS MANUFACTURERAS': 2,
    'SERVICIOS ESENCIALES': 0,
    'INDUSTRIA DE LA PESCA': 2,
    'INDUSTRIA FARMACÉUTICA': 1,
    'TELECOMUNICACIONES': 3,
    'SERVICIOS FINANCIEROS': 3,
}

ETAPAS_NUM = {
    'Prefactibilidad': 0,
    'Factibilidad': 1,
    'Ejecución': 2,
    'Operación': 3,
}

TIPOS_NUM = {
    'Conectado a la red (SFCR)': 0,
    'Autónomo (SFA)': 1,
    'Híbrido (SFH)': 2,
}

SEGMENTOS_NUM = {
    'PYME': 0,
    'Empresarial': 1,
    'Corporativo': 2,
}


def preparar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte un DataFrame crudo en las columnas numéricas que consume el modelo.

    Hace dos cosas:
    1. Codifica las categóricas (sector, etapa, tipo, segmento) a número usando
       los diccionarios de mapeo de arriba. fillna() asigna un valor neutro si
       aparece una categoría no listada, para que el modelo nunca reciba NaN.
    2. Crea dos variables derivadas que aportan señal extra al modelo.

    El "+1" en los denominadores es una guarda anti división por cero.
    """
    df = df.copy()

    # Codificar variables categóricas (texto -> entero, vía los mapas SECTORES_RIESGO, etc.)
    df['sector_riesgo'] = df['sector_bg'].map(SECTORES_RIESGO).fillna(1)
    df['etapa_num'] = df['etapa'].map(ETAPAS_NUM).fillna(1)
    df['tipo_num'] = df['tipo_sistema'].map(TIPOS_NUM).fillna(0)
    df['segmento_num'] = df['segmento'].map(SEGMENTOS_NUM).fillna(1)

    # Variables derivadas (combinan campos para dar más señal al modelo)
    df['ratio_financiamiento'] = df['monto_credito_usd'] / (df['capex_usd'] + 1)   # fracción del CAPEX cubierta por el crédito
    df['gei_por_kwp'] = df['gei_evitadas_anual_tco2'] / (df['capacidad_instalada_mwp'] * 1000 + 1)  # eficiencia ambiental por kWp

    return df


def entrenar_modelos(db_path: str = "database/credito_terra.db") -> dict:
    """
    Entrena los modelos de estimación con los datos de la BD.

    Nota metodológica: Requiere mínimo 200 casos (Riley et al., 2019).
    Re-entrenar cada 150 casos nuevos o cuando precisión < 80%.
    """
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score
    import sqlite3

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM evaluaciones", conn)
    conn.close()

    # Umbral metodológico: por debajo de 200 casos no se entrena (Riley et al., 2019).
    if len(df) < 200:
        print(f"⚠️  Solo hay {len(df)} casos. Se necesitan al menos 200 para entrenar.")
        print("Los modelos de estimación no estarán disponibles hasta alcanzar ese umbral.")
        return None

    print(f"Entrenando modelos con {len(df)} casos...")
    df = preparar_features(df)   # crea las columnas codificadas y derivadas que usan los modelos

    # Variables que ve el CLASIFICADOR de elegibilidad: técnicas + categóricas codificadas + derivadas.
    features_clf = [
        'capacidad_instalada_mwp', 'cobertura_energetica_pct',
        'capex_usd', 'monto_credito_usd', 'vida_util_anios',
        'tarifa_electrica_usd_kwh', 'ahorro_anual_usd',
        'sector_riesgo', 'etapa_num', 'tipo_num', 'segmento_num',
        'ratio_financiamiento', 'gei_por_kwp'
    ]

    # Variables que ven los REGRESORES (GEI y cobertura): subconjunto técnico reducido.
    features_reg = [
        'capacidad_instalada_mwp', 'vida_util_anios',
        'consumo_cliente_mwh_anio', 'sector_riesgo', 'etapa_num'
    ]

    # Descartar filas con datos faltantes en las columnas que necesitan los modelos (evita errores de entrenamiento).
    df_clean = df.dropna(subset=features_clf + ['cumple_elegibilidad',
                          'gei_evitadas_anual_tco2', 'cobertura_energetica_pct'])

    X_clf = df_clean[features_clf]
    y_clf = df_clean['cumple_elegibilidad'].astype(int)

    X_reg_gei = df_clean[features_reg]
    y_gei = df_clean['gei_evitadas_anual_tco2']

    X_reg_cob = df_clean[features_reg]
    y_cob = df_clean['cobertura_energetica_pct']

    # Modelo clasificador — elegibilidad (CUMPLE / NO CUMPLE).
    #   n_estimators=100        -> número de árboles del bosque.
    #   max_depth=8             -> profundidad máxima por árbol (limita el sobreajuste).
    #   class_weight='balanced' -> compensa el desbalance del portafolio (~31% CUMPLE vs ~69% NO).
    #   random_state=42         -> fija la semilla para que el resultado sea reproducible.
    clf = RandomForestClassifier(n_estimators=100, max_depth=8,
                                  random_state=42, class_weight='balanced')
    clf.fit(X_clf, y_clf)
    # Validación cruzada de 5 particiones: estima la precisión sin depender de un único split.
    scores_clf = cross_val_score(clf, X_clf, y_clf, cv=5, scoring='accuracy')

    # Modelo regresor — GEI evitadas
    reg_gei = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    reg_gei.fit(X_reg_gei, y_gei)
    scores_gei = cross_val_score(reg_gei, X_reg_gei, y_gei, cv=5, scoring='r2')

    # Modelo regresor — cobertura energética
    reg_cob = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    reg_cob.fit(X_reg_cob, y_cob)
    scores_cob = cross_val_score(reg_cob, X_reg_cob, y_cob, cv=5, scoring='r2')

    # Importancia de variables
    importancia = pd.DataFrame({
        'variable': features_clf,
        'importancia': clf.feature_importances_
    }).sort_values('importancia', ascending=False)

    metricas = {
        'n_casos_entrenamiento': len(df_clean),
        'precision_elegibilidad': round(scores_clf.mean() * 100, 1),
        'r2_gei': round(scores_gei.mean(), 3),
        'r2_cobertura': round(scores_cob.mean(), 3),
        'importancia_variables': importancia,
    }

    modelos = {
        'clasificador': clf,
        'regresor_gei': reg_gei,
        'regresor_cobertura': reg_cob,
        'features_clf': features_clf,
        'features_reg': features_reg,
        'metricas': metricas,
    }

    # Guardar modelos
    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(modelos, f)

    print(f"\n✅ Modelos entrenados:")
    print(f"   Precisión elegibilidad: {metricas['precision_elegibilidad']}%")
    print(f"   R² GEI evitadas:        {metricas['r2_gei']}")
    print(f"   R² Cobertura:           {metricas['r2_cobertura']}")
    print(f"\n   Variables más importantes:")
    for _, row in importancia.head(5).iterrows():
        print(f"   - {row['variable']}: {row['importancia']:.3f}")

    return modelos


def cargar_modelos() -> dict:
    """Carga los modelos entrenados desde disco."""
    if not Path(MODEL_PATH).exists():
        return None
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)


def estimar_proyecto(
    sector: str,
    segmento: str,
    tipo_sistema: str,
    etapa: str,
    capacidad_mwp: float,
    consumo_cliente_mwh: float,
    monto_aproximado: float,
) -> dict:
    """
    Estima los indicadores ambientales y probabilidad de elegibilidad
    para un cliente interesado, antes del levantamiento formal.

    Parámetros básicos que el analista puede obtener en una primera conversación.
    """
    modelos = cargar_modelos()

    # Cálculo de indicadores físicos (sin ML): fórmulas con parámetros típicos de Ecuador.
    irradiacion_promedio = 1400  # horas equivalentes/año (factor de planta solar típico en Ecuador)
    energia_estimada = round(capacidad_mwp * irradiacion_promedio, 2)
    cobertura_estimada = round(energia_estimada / consumo_cliente_mwh * 100, 2) if consumo_cliente_mwh > 0 else 0
    gei_anual_estimado = round(energia_estimada * FACTOR_EMISION, 4)
    vida_util_tipica = 25  # años de vida útil típica de un sistema fotovoltaico
    gei_total_estimado = round(gei_anual_estimado * vida_util_tipica, 4)
    cap_kwp = round(capacidad_mwp * 1000, 2)
    capex_estimado = round(cap_kwp * 1000, 2)  # ~1000 USD/kWp, costo referencial promedio en Ecuador
    tarifa_promedio = 0.10  # USD/kWh, tarifa eléctrica referencial
    ahorro_estimado = round(energia_estimada * 1000 * tarifa_promedio, 2)

    # Predicción ML SOLO si el modelo ya está entrenado y disponible en disco.
    # Si no, la estimación queda únicamente en los indicadores físicos de arriba.
    prob_elegible = None
    precision_modelo = None

    if modelos:
        input_data = pd.DataFrame([{
            'capacidad_instalada_mwp': capacidad_mwp,
            'cobertura_energetica_pct': cobertura_estimada,
            'capex_usd': capex_estimado,
            'monto_credito_usd': monto_aproximado,
            'vida_util_anios': vida_util_tipica,
            'tarifa_electrica_usd_kwh': tarifa_promedio,
            'ahorro_anual_usd': ahorro_estimado,
            'sector_bg': sector,
            'etapa': etapa,
            'tipo_sistema': tipo_sistema,
            'segmento': segmento,
            'gei_evitadas_anual_tco2': gei_anual_estimado,
            'consumo_cliente_mwh_anio': consumo_cliente_mwh,
        }])

        input_prep = preparar_features(input_data)
        features_clf = modelos['features_clf']
        features_disponibles = [f for f in features_clf if f in input_prep.columns]

        # Solo predecir si están TODAS las variables que el modelo espera (si falta alguna, se omite).
        if len(features_disponibles) == len(features_clf):
            # predict_proba devuelve [P(NO CUMPLE), P(CUMPLE)]; tomamos la segunda y la pasamos a %.
            prob = modelos['clasificador'].predict_proba(input_prep[features_clf])[0]
            prob_elegible = round(prob[1] * 100, 1)
            precision_modelo = modelos['metricas']['precision_elegibilidad']

    # Recomendación según la probabilidad estimada (umbrales: >=70% alto, >=40% medio, resto bajo).
    if prob_elegible is not None:
        if prob_elegible >= 70:
            recomendacion = "FAVORABLE — Proceder con levantamiento formal de ficha"
            nivel = "ALTO"
        elif prob_elegible >= 40:
            recomendacion = "MODERADO — Revisar criterios críticos antes del levantamiento"
            nivel = "MEDIO"
        else:
            recomendacion = "BAJO — Analizar barreras de elegibilidad antes de continuar"
            nivel = "BAJO"
    else:
        recomendacion = "Estimación basada en indicadores físicos — modelo ML pendiente de entrenamiento"
        nivel = "N/D"

    return {
        'sector': sector,
        'segmento': segmento,
        'tipo_sistema': tipo_sistema,
        'etapa': etapa,
        'capacidad_mwp': capacidad_mwp,
        'capacidad_kwp': cap_kwp,
        'energia_estimada_mwh': energia_estimada,
        'cobertura_estimada_pct': cobertura_estimada,
        'gei_anual_estimado_tco2': gei_anual_estimado,
        'gei_total_estimado_tco2': gei_total_estimado,
        'capex_referencial_usd': capex_estimado,
        'ahorro_anual_estimado_usd': ahorro_estimado,
        'probabilidad_elegible_pct': prob_elegible,
        'precision_modelo_pct': precision_modelo,
        'nivel_viabilidad': nivel,
        'recomendacion': recomendacion,
        'nota': (
            "Estimación preliminar basada en parámetros típicos del mercado ecuatoriano. "
            "Los valores reales dependen del estudio técnico detallado. "
            f"Modelo ML entrenado con {modelos['metricas']['n_casos_entrenamiento']} casos."
            if modelos else
            "Estimación basada en indicadores físicos. El modelo ML se activará "
            "cuando la BD alcance 200 casos evaluados (Riley et al., 2019)."
        )
    }


if __name__ == "__main__":
    print("=== ENTRENAMIENTO DEL MODELO DE ESTIMACIÓN ===\n")
    modelos = entrenar_modelos()

    if modelos:
        print("\n=== PRUEBA DE ESTIMACIÓN PRELIMINAR ===\n")
        resultado = estimar_proyecto(
            sector="INDUSTRIA ALIMENTICIA",
            segmento="Empresarial",
            tipo_sistema="Conectado a la red (SFCR)",
            etapa="Factibilidad",
            capacidad_mwp=1.5,
            consumo_cliente_mwh=3000,
            monto_aproximado=800000,
        )

        print(f"Sector:                    {resultado['sector']}")
        print(f"Capacidad:                 {resultado['capacidad_mwp']} MWp")
        print(f"Energía estimada:          {resultado['energia_estimada_mwh']} MWh/año")
        print(f"Cobertura estimada:        {resultado['cobertura_estimada_pct']}%")
        print(f"GEI evitadas/año:          {resultado['gei_anual_estimado_tco2']} tCO₂")
        print(f"GEI evitadas totales:      {resultado['gei_total_estimado_tco2']} tCO₂")
        print(f"Probabilidad elegible:     {resultado['probabilidad_elegible_pct']}%")
        print(f"Nivel de viabilidad:       {resultado['nivel_viabilidad']}")
        print(f"Recomendación:             {resultado['recomendacion']}")
