"""
Script operativo principal — Crédito Terra
Banco Guayaquil - Sostenibilidad

Uso:
    # Procesar una ficha nueva
    python src/procesar_ficha.py data/simulated/fichas/CT-0001_Empresa_1.xlsx

    # Re-evaluar un caso existente
    python src/procesar_ficha.py data/simulated/fichas/CT-0001_Empresa_1.xlsx --reevaluar

    # Procesar carpeta completa (solo fichas nuevas)
    python src/procesar_ficha.py --carpeta data/simulated/fichas/
"""

import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(__file__))

from lector_ficha import leer_ficha_excel
from validador import ValidadorFicha
from motor_elegibilidad import MotorElegibilidad
from generador_informe import generar_informe_word
from base_datos import crear_conexion, crear_tablas, registrar_evaluacion, caso_existe

DB_PATH = "database/credito_terra.db"
OUTPUTS_PATH = "data/outputs"


def procesar_ficha(ruta_ficha: str, forzar_reevaluacion: bool = False) -> dict:
    print(f"\n{'='*60}")
    print(f"SISTEMA DE EVALUACIÓN — CRÉDITO TERRA")
    print(f"Banco Guayaquil - Área de Sostenibilidad")
    print(f"{'='*60}\n")

    # Paso 1: Leer ficha
    print("PASO 1 — Leyendo ficha Excel...")
    caso = leer_ficha_excel(ruta_ficha)

    # Verificar duplicado
    conn = crear_conexion(DB_PATH)
    crear_tablas(conn)
    existe = caso_existe(conn, caso.get('id_caso', ''))
    conn.close()

    if existe and not forzar_reevaluacion:
        print(f"\n⚠️  El caso {caso.get('id_caso')} ya existe en la base de datos.")
        print("Si deseas re-evaluar, ejecuta con --reevaluar")
        return {'error': True, 'motivo': 'duplicado', 'caso': caso}

    if existe:
        print(f"ℹ️  Re-evaluando caso existente: {caso.get('id_caso')}")

    # Paso 2: Validar
    print("\nPASO 2 — Validando datos...")
    validador = ValidadorFicha(caso)
    validacion = validador.validar()

    if not validacion['es_valido']:
        print(f"\n❌ {validacion['n_errores']} errores encontrados:")
        for e in validacion['errores']:
            print(f"   {e}")
        print("\nCorrige los errores y vuelve a ejecutar.")
        return {'error': True, 'motivo': 'validacion', 'validacion': validacion, 'caso': caso}

    if validacion['n_advertencias'] > 0:
        print(f"⚠️  {validacion['n_advertencias']} advertencias:")
        for a in validacion['advertencias']:
            print(f"   {a}")

    print("✅ Validación sin errores")

    # Paso 3: Evaluar elegibilidad
    print("\nPASO 3 — Evaluando elegibilidad...")
    motor = MotorElegibilidad(caso)
    dictamen = motor.emitir_dictamen()
    dictamen['detalle_criterios_dict'] = motor.resultados_criterios

    for linea in dictamen['detalle_criterios']:
        print(f"  {linea}")

    print(f"\n{'='*60}")
    print(f"  DICTAMEN: {dictamen['dictamen']}")
    print(f"  Criterios: {dictamen['n_criterios_cumplidos']}/10")
    print(f"{'='*60}")

    # Paso 4: Generar informe Word
    print("\nPASO 4 — Generando informe Word...")
    Path(OUTPUTS_PATH).mkdir(parents=True, exist_ok=True)
    ruta_informe = f"{OUTPUTS_PATH}/Informe_{caso['id_caso']}.docx"
    generar_informe_word(caso, dictamen, ruta_informe)
    print(f"✅ Informe: {ruta_informe}")

    # Paso 5: Registrar en BD
    print("\nPASO 5 — Registrando en base de datos...")
    conn = crear_conexion(DB_PATH)
    es_reevaluacion = registrar_evaluacion(conn, caso, dictamen,
                      motivo_reevaluacion="Re-evaluación manual" if forzar_reevaluacion else None)
    conn.close()

    accion = "actualizado" if es_reevaluacion else "registrado"
    print(f"✅ Caso {caso['id_caso']} {accion} en portafolio")

    print(f"\n{'='*60}")
    print(f"COMPLETADO — {caso.get('razon_social')} → {dictamen['dictamen']}")
    print(f"{'='*60}\n")

    return {
        'error': False,
        'caso': caso,
        'validacion': validacion,
        'dictamen': dictamen,
        'ruta_informe': ruta_informe,
        'es_reevaluacion': es_reevaluacion,
    }


def procesar_carpeta(ruta_carpeta: str):
    """Procesa solo las fichas nuevas de una carpeta."""
    carpeta = Path(ruta_carpeta)
    fichas = sorted(carpeta.glob("*.xlsx"))

    if not fichas:
        print(f"No se encontraron fichas en {ruta_carpeta}")
        return

    conn = crear_conexion(DB_PATH)
    crear_tablas(conn)

    import pandas as pd
    try:
        df_bd = pd.read_sql_query("SELECT id_caso FROM evaluaciones", conn)
        casos_registrados = set(df_bd['id_caso'].tolist())
    except Exception:
        casos_registrados = set()
    conn.close()

    fichas_nuevas = []
    fichas_existentes = []

    for ficha in fichas:
        import openpyxl, warnings
        warnings.filterwarnings('ignore')
        wb = openpyxl.load_workbook(ficha, data_only=True)
        ws = wb['FLI CT-001']
        no_op = ws['C21'].value
        id_caso = f"CT-{no_op}" if no_op else None
        wb.close()

        if id_caso and id_caso in casos_registrados:
            fichas_existentes.append(ficha)
        else:
            fichas_nuevas.append(ficha)

    print(f"\nFichas encontradas:  {len(fichas)}")
    print(f"Ya registradas:      {len(fichas_existentes)}")
    print(f"Nuevas a procesar:   {len(fichas_nuevas)}\n")

    procesadas = 0
    errores = 0
    for ficha in fichas_nuevas:
        resultado = procesar_ficha(str(ficha))
        if not resultado['error']:
            procesadas += 1
        else:
            errores += 1

    print(f"\nResumen: {procesadas} procesadas, {errores} con errores")


if __name__ == "__main__":
    reevaluar = '--reevaluar' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]

    if not args:
        print("Uso:")
        print("  python src/procesar_ficha.py <ruta_ficha.xlsx>")
        print("  python src/procesar_ficha.py <ruta_ficha.xlsx> --reevaluar")
        print("  python src/procesar_ficha.py --carpeta <ruta_carpeta>")
        sys.exit(1)

    if '--carpeta' in sys.argv:
        idx = sys.argv.index('--carpeta')
        procesar_carpeta(sys.argv[idx + 1])
    else:
        procesar_ficha(args[0], forzar_reevaluacion=reevaluar)
