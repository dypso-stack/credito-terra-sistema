"""
Módulo: Base de Datos SQLite
Crédito Terra - Banco Guayaquil
Gestión del portafolio: registros, re-evaluación, consultas
"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

DB_PATH = "database/credito_terra.db"


def crear_conexion(db_path: str = DB_PATH) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def crear_tablas(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_caso TEXT UNIQUE NOT NULL,
            fecha_gestion TEXT,
            fecha_evaluacion TEXT,
            responsable TEXT,
            razon_social TEXT,
            ruc TEXT,
            sector_bg TEXT,
            segmento TEXT,
            canal_gestion TEXT,
            no_operacion TEXT,
            asesor_comercial TEXT,
            destino_terra TEXT,
            codigo_terra TEXT,
            monto_credito_usd REAL,
            etapa TEXT,
            tipo_sistema TEXT,
            propietario_sistema TEXT,
            energia_producida_mwh_anio REAL,
            capacidad_instalada_mwp REAL,
            capacidad_kwp REAL,
            consumo_cliente_mwh_anio REAL,
            cobertura_energetica_pct REAL,
            vida_util_anios INTEGER,
            factor_emision_sni REAL,
            gei_evitadas_anual_tco2 REAL,
            gei_evitadas_total_tco2 REAL,
            capex_usd REAL,
            aporte_propio_usd REAL,
            tarifa_electrica_usd_kwh REAL,
            ahorro_anual_usd REAL,
            payback_anios REAL,
            n_criterios_cumplidos INTEGER,
            n_criterios_fallidos INTEGER,
            criterios_fallidos TEXT,
            cumple_elegibilidad INTEGER,
            dictamen TEXT,
            accion_requerida TEXT,
            n_evaluaciones INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_caso TEXT NOT NULL,
            fecha_evaluacion TEXT,
            dictamen TEXT,
            n_criterios_cumplidos INTEGER,
            criterios_fallidos TEXT,
            motivo_reevaluacion TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def caso_existe(conn: sqlite3.Connection, id_caso: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM evaluaciones WHERE id_caso = ?", (id_caso,))
    return cursor.fetchone() is not None


def registrar_evaluacion(conn: sqlite3.Connection, caso: dict, dictamen: dict,
                          motivo_reevaluacion: str = None):
    cursor = conn.cursor()
    es_reevaluacion = caso_existe(conn, caso.get('id_caso', ''))

    if es_reevaluacion:
        # Guardar en historial antes de actualizar
        cursor.execute("""
            INSERT INTO historial_evaluaciones
            (id_caso, fecha_evaluacion, dictamen, n_criterios_cumplidos,
             criterios_fallidos, motivo_reevaluacion)
            SELECT id_caso, fecha_evaluacion, dictamen, n_criterios_cumplidos,
                   criterios_fallidos, ?
            FROM evaluaciones WHERE id_caso = ?
        """, (motivo_reevaluacion or 'Re-evaluación', caso.get('id_caso')))

        # Actualizar registro existente
        cursor.execute("""
            UPDATE evaluaciones SET
                fecha_evaluacion = ?,
                n_criterios_cumplidos = ?,
                n_criterios_fallidos = ?,
                criterios_fallidos = ?,
                cumple_elegibilidad = ?,
                dictamen = ?,
                accion_requerida = ?,
                gei_evitadas_anual_tco2 = ?,
                gei_evitadas_total_tco2 = ?,
                cobertura_energetica_pct = ?,
                capacidad_kwp = ?,
                n_evaluaciones = n_evaluaciones + 1,
                updated_at = ?
            WHERE id_caso = ?
        """, (
            dictamen.get('fecha_evaluacion'),
            dictamen.get('n_criterios_cumplidos'),
            dictamen.get('n_criterios_fallidos'),
            ', '.join(dictamen.get('criterios_fallidos', [])),
            1 if dictamen.get('cumple_elegibilidad') else 0,
            dictamen.get('dictamen'),
            dictamen.get('accion_requerida'),
            dictamen.get('indicadores', {}).get('gei_evitadas_anual_tco2'),
            dictamen.get('indicadores', {}).get('gei_evitadas_total_tco2'),
            dictamen.get('indicadores', {}).get('cobertura_energetica_pct'),
            dictamen.get('indicadores', {}).get('capacidad_kwp'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            caso.get('id_caso'),
        ))
    else:
        # Insertar nuevo registro
        cursor.execute("""
            INSERT INTO evaluaciones (
                id_caso, fecha_gestion, fecha_evaluacion, responsable,
                razon_social, ruc, sector_bg, segmento, canal_gestion,
                no_operacion, asesor_comercial, destino_terra, codigo_terra,
                monto_credito_usd, etapa, tipo_sistema, propietario_sistema,
                energia_producida_mwh_anio, capacidad_instalada_mwp, capacidad_kwp,
                consumo_cliente_mwh_anio, cobertura_energetica_pct, vida_util_anios,
                factor_emision_sni, gei_evitadas_anual_tco2, gei_evitadas_total_tco2,
                capex_usd, aporte_propio_usd, tarifa_electrica_usd_kwh,
                ahorro_anual_usd, payback_anios,
                n_criterios_cumplidos, n_criterios_fallidos, criterios_fallidos,
                cumple_elegibilidad, dictamen, accion_requerida
            ) VALUES (
                :id_caso, :fecha_gestion, :fecha_evaluacion, :responsable,
                :razon_social, :ruc, :sector_bg, :segmento, :canal_gestion,
                :no_operacion, :asesor_comercial, :destino_terra, :codigo_terra,
                :monto_credito_usd, :etapa, :tipo_sistema, :propietario_sistema,
                :energia_producida_mwh_anio, :capacidad_instalada_mwp, :capacidad_kwp,
                :consumo_cliente_mwh_anio, :cobertura_energetica_pct, :vida_util_anios,
                :factor_emision_sni, :gei_evitadas_anual_tco2, :gei_evitadas_total_tco2,
                :capex_usd, :aporte_propio_usd, :tarifa_electrica_usd_kwh,
                :ahorro_anual_usd, :payback_anios,
                :n_criterios_cumplidos, :n_criterios_fallidos, :criterios_fallidos,
                :cumple_elegibilidad, :dictamen, :accion_requerida
            )
        """, {
            **caso,
            'fecha_evaluacion': dictamen.get('fecha_evaluacion'),
            'capacidad_kwp': dictamen.get('indicadores', {}).get('capacidad_kwp'),
            'cobertura_energetica_pct': dictamen.get('indicadores', {}).get('cobertura_energetica_pct'),
            'gei_evitadas_anual_tco2': dictamen.get('indicadores', {}).get('gei_evitadas_anual_tco2'),
            'gei_evitadas_total_tco2': dictamen.get('indicadores', {}).get('gei_evitadas_total_tco2'),
            'factor_emision_sni': dictamen.get('indicadores', {}).get('factor_emision_sni'),
            'n_criterios_cumplidos': dictamen.get('n_criterios_cumplidos'),
            'n_criterios_fallidos': dictamen.get('n_criterios_fallidos'),
            'criterios_fallidos': ', '.join(dictamen.get('criterios_fallidos', [])),
            'cumple_elegibilidad': 1 if dictamen.get('cumple_elegibilidad') else 0,
            'dictamen': dictamen.get('dictamen'),
            'accion_requerida': dictamen.get('accion_requerida'),
        })

    conn.commit()
    return es_reevaluacion


def consultar_portafolio(conn: sqlite3.Connection) -> dict:
    df = pd.read_sql_query("SELECT * FROM evaluaciones", conn)
    if df.empty:
        return {"mensaje": "Sin datos en el portafolio aún."}

    # Asegurar tipos numéricos correctos
    cols_numericas = [
        'monto_credito_usd', 'capacidad_instalada_mwp', 'capacidad_kwp',
        'energia_producida_mwh_anio', 'consumo_cliente_mwh_anio',
        'cobertura_energetica_pct', 'gei_evitadas_anual_tco2',
        'gei_evitadas_total_tco2', 'capex_usd', 'aporte_propio_usd',
        'tarifa_electrica_usd_kwh', 'ahorro_anual_usd', 'payback_anios',
        'vida_util_anios', 'factor_emision_sni', 'cumple_elegibilidad'
    ]
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return {
        "total_casos": len(df),
        "casos_cumplen": int(df["cumple_elegibilidad"].sum()),
        "casos_no_cumplen": int((~df["cumple_elegibilidad"].astype(bool)).sum()),
        "tasa_aprobacion_pct": round(df["cumple_elegibilidad"].mean() * 100, 1),
        "monto_total_evaluado_usd": round(df["monto_credito_usd"].sum(), 2),
        "monto_promedio_usd": round(df["monto_credito_usd"].mean(), 2),
        "gei_total_evitadas_tco2": round(df["gei_evitadas_total_tco2"].sum(), 2),
        "gei_anual_evitadas_tco2": round(df["gei_evitadas_anual_tco2"].sum(), 2),
        "capacidad_total_mwp": round(df["capacidad_instalada_mwp"].sum(), 3),
        "por_sector": df.groupby("sector_bg")["id_caso"].count().to_dict(),
        "por_etapa": df.groupby("etapa")["id_caso"].count().to_dict(),
        "por_dictamen": df.groupby("dictamen")["id_caso"].count().to_dict(),
        "por_segmento": df.groupby("segmento")["id_caso"].count().to_dict(),
    }


COLS_NUMERICAS = [
    'monto_credito_usd', 'capacidad_instalada_mwp', 'capacidad_kwp',
    'energia_producida_mwh_anio', 'consumo_cliente_mwh_anio',
    'cobertura_energetica_pct', 'gei_evitadas_anual_tco2',
    'gei_evitadas_total_tco2', 'capex_usd', 'aporte_propio_usd',
    'tarifa_electrica_usd_kwh', 'ahorro_anual_usd', 'payback_anios',
    'vida_util_anios', 'factor_emision_sni', 'cumple_elegibilidad',
    'n_criterios_cumplidos', 'n_criterios_fallidos'
]

def cargar_portafolio_df(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT * FROM evaluaciones ORDER BY created_at DESC", conn
    )
    for col in COLS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df
