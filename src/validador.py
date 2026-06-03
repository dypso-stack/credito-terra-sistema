"""
Módulo: Validación de la ficha FLI CT-001
Crédito Terra - Banco Guayaquil
Lee la ficha FLI CT-001, valida campos y detecta inconsistencias.
"""

import pandas as pd
import numpy as np
from pathlib import Path


# --- Campos obligatorios por sección ---
CAMPOS_OBLIGATORIOS = {
    "Sección 0 - Cliente": [
        "razon_social", "ruc", "sector_bg", "segmento", "canal_gestion"
    ],
    "Sección 1 - Crédito": [
        "monto_credito_usd", "asesor_comercial", "destino_terra"
    ],
    "Sección 2 - Proyecto": [
        "direccion_proyecto", "etapa", "tipo_sistema"
    ],
    "Sección 3 - Técnico": [
        "energia_producida_mwh_anio", "capacidad_instalada_mwp",
        "consumo_cliente_mwh_anio", "vida_util_anios"
    ],
    "Sección 5 - Financiero": [
        "capex_usd", "tarifa_electrica_usd_kwh"
    ],
}

CAMPOS_ELEGIBILIDAD = [
    "uso_exclusivo_fondos",
    "evidencia_objetiva_proyecto",
    "indicadores_ambientales_completos",
    "cumple_normativa_ambiental",
    "no_categoria_a_ifc",
    "no_involucra_combustibles_fosiles",
    "no_impacto_negativo_otros_objetivos",
    "no_lista_exclusion_saras",
    "no_controversias_socioambientales",
    "no_es_credito_consumo",
]

LABELS_ELEGIBILIDAD = {
    "uso_exclusivo_fondos": "¿El monto será usado exclusivamente para el proyecto verde?",
    "evidencia_objetiva_proyecto": "¿Existe evidencia objetiva del proyecto?",
    "indicadores_ambientales_completos": "¿Existen indicadores ambientales del proyecto?",
    "cumple_normativa_ambiental": "¿Cumple con la normativa nacional ambiental y social?",
    "no_categoria_a_ifc": "¿El proyecto NO es Categoría A según normas IFC?",
    "no_involucra_combustibles_fosiles": "¿El proyecto NO involucra combustibles fósiles?",
    "no_impacto_negativo_otros_objetivos": "¿El proyecto NO produce impactos negativos en otros objetivos ambientales?",
    "no_lista_exclusion_saras": "¿El proyecto NO está en la lista de exclusión del SARAS?",
    "no_controversias_socioambientales": "¿El cliente NO tiene controversias socioambientales?",
    "no_es_credito_consumo": "¿El crédito NO corresponde a un préstamo de consumo?",
}


class ValidadorFicha:
    """
    Valida un caso de evaluación Crédito Terra.
    Detecta campos vacíos, inconsistencias lógicas y errores de datos.
    """

    def __init__(self, caso: dict):
        self.caso = caso
        self.errores = []
        self.advertencias = []

    def validar(self):
        """Ejecuta todas las validaciones y retorna el resultado."""
        self._validar_campos_obligatorios()
        self._validar_rangos_tecnicos()
        self._validar_consistencia_financiera()
        self._validar_indicadores_ambientales()

        return {
            "es_valido": len(self.errores) == 0,
            "errores": self.errores,
            "advertencias": self.advertencias,
            "n_errores": len(self.errores),
            "n_advertencias": len(self.advertencias),
        }

    def _validar_campos_obligatorios(self):
        """Verifica que todos los campos obligatorios estén presentes y no vacíos."""
        for seccion, campos in CAMPOS_OBLIGATORIOS.items():
            for campo in campos:
                valor = self.caso.get(campo)
                if valor is None or (isinstance(valor, float) and np.isnan(valor)):
                    self.errores.append(
                        f"[{seccion}] Campo obligatorio vacío: '{campo}'"
                    )
                elif valor == 0 and campo in ["energia_producida_mwh_anio", "capacidad_instalada_mwp", "capex_usd"]:
                    self.errores.append(
                        f"[{seccion}] Campo no puede ser cero: '{campo}'"
                    )

    def _validar_rangos_tecnicos(self):
        """Verifica que los valores técnicos estén en rangos razonables."""
        def to_float(val):
            try:
                return float(val) if val is not None else 0
            except (ValueError, TypeError):
                return 0

        capacidad = to_float(self.caso.get("capacidad_instalada_mwp", 0))
        energia = to_float(self.caso.get("energia_producida_mwh_anio", 0))
        vida_util = to_float(self.caso.get("vida_util_anios", 0))

        if capacidad and capacidad > 10:
            self.advertencias.append(
                f"Capacidad instalada ({capacidad} MWp) supera 10 MWp — "
                "verificar si aplica exclusión de energía hidroeléctrica"
            )

        if capacidad and energia:
            ratio = energia / (capacidad * 1000)  # horas equivalentes
            if ratio < 800 or ratio > 2000:
                self.advertencias.append(
                    f"Ratio energía/capacidad inusual ({ratio:.0f} h/año). "
                    "Verificar valores de producción energética."
                )

        if vida_util and vida_util not in [20, 25, 30]:
            self.advertencias.append(
                f"Vida útil declarada ({vida_util} años) fuera del rango típico (20-30 años)"
            )

    def _validar_consistencia_financiera(self):
        """Verifica coherencia entre CAPEX, monto crédito y aporte propio."""
        capex = self.caso.get("capex_usd", 0) or 0
        monto = self.caso.get("monto_credito_usd", 0) or 0
        aporte = self.caso.get("aporte_propio_usd", 0) or 0

        if capex > 0 and monto > capex:
            self.errores.append(
                f"Monto del crédito (${monto:,.2f}) supera el CAPEX total (${capex:,.2f})"
            )

        if capex > 0 and aporte < 0:
            self.errores.append(
                "Aporte propio negativo — revisar CAPEX y monto del crédito"
            )

        if capex == 0 and monto > 0:
            self.advertencias.append(
                "CAPEX no declarado pero monto de crédito ingresado — completar costo total del sistema"
            )

    def _validar_indicadores_ambientales(self):
        """Verifica que los indicadores ambientales sean coherentes."""
        energia = self.caso.get("energia_producida_mwh_anio", 0) or 0
        gei = self.caso.get("gei_evitadas_anual_tco2", 0) or 0
        factor = self.caso.get("factor_emision_sni", 0.4567)

        if energia > 0 and gei > 0:
            gei_esperado = round(energia * factor, 4)
            diferencia = abs(gei - gei_esperado)
            if diferencia > 0.01:
                self.advertencias.append(
                    f"GEI evitadas declaradas ({gei} tCO2/año) difieren del cálculo "
                    f"esperado ({gei_esperado} tCO2/año) — verificar fórmula"
                )


def cargar_dataset(ruta: str) -> pd.DataFrame:
    """
    Carga el dataset de casos simulados desde CSV.
    Retorna DataFrame con tipos correctos.
    """
    df = pd.read_csv(ruta)

    # Convertir columnas booleanas
    bool_cols = CAMPOS_ELEGIBILIDAD + ["cumple_elegibilidad"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    # Convertir fechas
    for col in ["fecha_gestion", "fecha_puesta_marcha"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")

    return df


def validar_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica el validador a todos los casos del dataset.
    Retorna DataFrame con columnas de resultado de validación.
    """
    resultados = []
    for _, row in df.iterrows():
        caso = row.to_dict()
        validador = ValidadorFicha(caso)
        resultado = validador.validar()
        resultados.append({
            "id_caso": caso.get("id_caso"),
            "es_valido": resultado["es_valido"],
            "n_errores": resultado["n_errores"],
            "n_advertencias": resultado["n_advertencias"],
            "errores": " | ".join(resultado["errores"]),
            "advertencias": " | ".join(resultado["advertencias"]),
        })

    return pd.DataFrame(resultados)


if __name__ == "__main__":
    ruta = "data/simulated/casos_simulados.csv"
    print(f"Cargando dataset desde {ruta}...")
    df = cargar_dataset(ruta)

    print(f"\nDataset cargado: {len(df)} casos, {len(df.columns)} variables")
    print(f"\nDistribución de dictámenes:\n{df['dictamen'].value_counts()}")

    print("\nValidando casos...")
    df_validacion = validar_dataset(df)

    casos_validos = df_validacion["es_valido"].sum()
    print(f"\nCasos sin errores de datos: {casos_validos}/{len(df)}")
    print(f"Casos con errores: {len(df) - casos_validos}")

    casos_con_error = df_validacion[~df_validacion["es_valido"]]
    if len(casos_con_error) > 0:
        print(f"\nEjemplo de errores detectados:")
        print(casos_con_error[["id_caso", "errores"]].head(3).to_string(index=False))
