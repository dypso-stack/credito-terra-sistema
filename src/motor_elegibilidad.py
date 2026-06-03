"""
Módulo: Motor de elegibilidad
Crédito Terra - Banco Guayaquil
Evalúa automáticamente los criterios de elegibilidad y emite dictamen justificado.
"""

import pandas as pd
from datetime import datetime

FACTOR_EMISION_SNI = 0.4567  # tCO2/MWh — Informe 2024 Ecuador

# Descripciones de cada criterio para el dictamen
CRITERIOS_DESCRIPCION = {
    "uso_exclusivo_fondos": (
        "¿El monto será usado exclusivamente para el proyecto verde?",
        "Requisitos generales del Crédito Terra"
    ),
    "evidencia_objetiva_proyecto": (
        "¿Existe evidencia objetiva del proyecto?",
        "Documentación requerida del Crédito Terra"
    ),
    "indicadores_ambientales_completos": (
        "¿Existen indicadores ambientales del proyecto?",
        "Indicadores ambientales y sociales del Crédito Terra"
    ),
    "cumple_normativa_ambiental": (
        "¿Cumple con la normativa nacional ambiental y social?",
        "Anexo 3 - Exclusiones generales del Crédito Terra"
    ),
    "no_categoria_a_ifc": (
        "¿El proyecto NO es Categoría A según normas IFC?",
        "Anexo 3 - Exclusiones generales del Crédito Terra"
    ),
    "no_involucra_combustibles_fosiles": (
        "¿El proyecto NO involucra combustibles fósiles?",
        "Anexo 3 - Exclusiones generales del Crédito Terra"
    ),
    "no_impacto_negativo_otros_objetivos": (
        "¿El proyecto NO produce impactos negativos en otros objetivos ambientales?",
        "Anexo 3 - Exclusiones generales del Crédito Terra"
    ),
    "no_lista_exclusion_saras": (
        "¿El proyecto NO está en la lista de exclusión del SARAS?",
        "Anexo 3 - Exclusiones generales del Crédito Terra"
    ),
    "no_controversias_socioambientales": (
        "¿El cliente NO tiene controversias socioambientales?",
        "Anexo 3 - Exclusiones generales del Crédito Terra"
    ),
    "no_es_credito_consumo": (
        "¿El crédito NO corresponde a un préstamo de consumo?",
        "Anexo 3 - Exclusiones generales del Crédito Terra"
    ),
}


class MotorElegibilidad:
    """
    Motor de evaluación de elegibilidad para Crédito Terra.
    Implementa las reglas del documento de criterios de Banco Guayaquil.
    """

    def __init__(self, caso: dict):
        self.caso = caso
        self.resultados_criterios = {}
        self.indicadores_calculados = {}

    def calcular_indicadores(self):
        """
        Recalcula los indicadores ambientales de la Sección 4
        directamente desde los datos técnicos ingresados.
        Independiente de las fórmulas del Excel.
        """
        def to_float(val):
            try:
                return float(val) if val is not None else 0
            except (ValueError, TypeError):
                return 0

        energia = to_float(self.caso.get("energia_producida_mwh_anio", 0))
        capacidad_mwp = to_float(self.caso.get("capacidad_instalada_mwp", 0))
        consumo = to_float(self.caso.get("consumo_cliente_mwh_anio", 0))
        vida_util = to_float(self.caso.get("vida_util_anios", 0))

        # Cálculos replicados del Excel
        gei_anual = round(energia * FACTOR_EMISION_SNI, 4)
        gei_total = round(gei_anual * vida_util, 4)
        cobertura = round((energia / consumo * 100), 2) if consumo > 0 else 0
        capacidad_kwp = round(capacidad_mwp * 1000, 2)

        self.indicadores_calculados = {
            "energia_producida_mwh_anio": energia,
            "capacidad_kwp": capacidad_kwp,
            "cobertura_energetica_pct": cobertura,
            "factor_emision_sni": FACTOR_EMISION_SNI,
            "tipo_factor_emision": "Ex Ante",
            "gei_evitadas_anual_tco2": gei_anual,
            "gei_evitadas_total_tco2": gei_total,
            "vida_util_anios": vida_util,
        }

        return self.indicadores_calculados

    def evaluar_criterios(self):
        """
        Evalúa los 10 criterios de elegibilidad de la Sección 6.
        Para cada criterio: determina cumplimiento, pregunta y referencia.
        """
        for criterio in CRITERIOS_DESCRIPCION:
            valor = self.caso.get(criterio)
            # Normalizar: acepta bool o string "SI"/"NO"
            if isinstance(valor, bool):
                cumple = valor
            elif isinstance(valor, str):
                cumple = valor.upper() in ["SI", "SÍ", "TRUE", "1"]
            else:
                cumple = bool(valor)

            pregunta, referencia = CRITERIOS_DESCRIPCION[criterio]
            self.resultados_criterios[criterio] = {
                "cumple": cumple,
                "pregunta": pregunta,
                "referencia": referencia,
            }

        return self.resultados_criterios

    def emitir_dictamen(self) -> dict:
        """
        Emite el dictamen final con justificación completa.
        Retorna estructura lista para generar informe.
        """
        self.calcular_indicadores()
        self.evaluar_criterios()

        criterios_cumplidos = [k for k, v in self.resultados_criterios.items() if v["cumple"]]
        criterios_fallidos = [k for k, v in self.resultados_criterios.items() if not v["cumple"]]
        cumple_todo = len(criterios_fallidos) == 0

        # Construir justificación textual
        lineas_dictamen = []
        for criterio, detalle in self.resultados_criterios.items():
            simbolo = "✅" if detalle["cumple"] else "❌"
            lineas_dictamen.append(
                f"{simbolo} {detalle['pregunta']} — {detalle['referencia']}"
            )

        # Acción requerida
        if cumple_todo:
            accion = "El proyecto cumple todos los criterios. Proceder a comité de aprobación."
        else:
            fallas_texto = "; ".join([
                CRITERIOS_DESCRIPCION[c][0] for c in criterios_fallidos
            ])
            accion = f"Criterios no cumplidos: {fallas_texto}. Solicitar documentación y/o aclaraciones al cliente."

        dictamen = {
            "id_caso": self.caso.get("id_caso", "N/D"),
            "razon_social": self.caso.get("razon_social", "N/D"),
            "fecha_evaluacion": datetime.today().strftime("%d/%m/%Y"),
            "destino_terra": self.caso.get("destino_terra", "Energía Renovable"),
            "codigo_terra": self.caso.get("codigo_terra", "04 ER. 1"),
            "monto_credito_usd": self.caso.get("monto_credito_usd", 0),

            # Indicadores recalculados
            "indicadores": self.indicadores_calculados,

            # Criterios
            "n_criterios_total": len(CRITERIOS_DESCRIPCION),
            "n_criterios_cumplidos": len(criterios_cumplidos),
            "n_criterios_fallidos": len(criterios_fallidos),
            "criterios_fallidos": criterios_fallidos,
            "detalle_criterios": lineas_dictamen,

            # Dictamen final
            "cumple_elegibilidad": cumple_todo,
            "dictamen": "CUMPLE" if cumple_todo else "NO CUMPLE",
            "accion_requerida": accion,
            "responsable": self.caso.get("responsable", "N/D"),
        }

        return dictamen


def evaluar_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica el motor de elegibilidad a todo el dataset.
    Retorna DataFrame enriquecido con resultados del motor.
    """
    resultados = []

    for _, row in df.iterrows():
        caso = row.to_dict()
        motor = MotorElegibilidad(caso)
        dictamen = motor.emitir_dictamen()

        resultados.append({
            "id_caso": dictamen["id_caso"],
            "razon_social": dictamen["razon_social"],
            "dictamen_motor": dictamen["dictamen"],
            "n_criterios_cumplidos": dictamen["n_criterios_cumplidos"],
            "n_criterios_fallidos": dictamen["n_criterios_fallidos"],
            "criterios_fallidos": ", ".join(dictamen["criterios_fallidos"]),
            "gei_anual_calculado": dictamen["indicadores"]["gei_evitadas_anual_tco2"],
            "gei_total_calculado": dictamen["indicadores"]["gei_evitadas_total_tco2"],
            "cobertura_calculada_pct": dictamen["indicadores"]["cobertura_energetica_pct"],
            "accion_requerida": dictamen["accion_requerida"],
        })

    return pd.DataFrame(resultados)


if __name__ == "__main__":
    from generador_datos import generar_dataset

    print("Generando dataset de prueba...")
    df = generar_dataset(n_casos=10)

    print("\nEvaluando elegibilidad de cada caso...\n")
    for _, row in df.iterrows():
        caso = row.to_dict()
        motor = MotorElegibilidad(caso)
        dictamen = motor.emitir_dictamen()

        print(f"{'='*60}")
        print(f"CASO: {dictamen['id_caso']} — {dictamen['razon_social']}")
        print(f"DICTAMEN: {dictamen['dictamen']}")
        print(f"Criterios: {dictamen['n_criterios_cumplidos']}/10 cumplidos")
        print(f"\nDetalle:")
        for linea in dictamen["detalle_criterios"]:
            print(f"  {linea}")
        print(f"\nAcción: {dictamen['accion_requerida']}")
        print(f"\nIndicadores calculados:")
        ind = dictamen["indicadores"]
        print(f"  GEI evitadas/año: {ind['gei_evitadas_anual_tco2']} tCO2/año")
        print(f"  GEI evitadas totales: {ind['gei_evitadas_total_tco2']} tCO2")
        print(f"  Cobertura energética: {ind['cobertura_energetica_pct']}%")
