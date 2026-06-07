# Sistema de Evaluación Automatizada — Crédito Terra
**Banco Guayaquil - Sostenibilidad**
**Proyecto Integrador de Sistema de IA Aplicada para Análisis Predictivo**

---

## Descripción

Sistema de IA aplicada que automatiza tres procesos del Crédito Terra:
1. **Evaluación formal** de elegibilidad por cliente
2. **Estimación preliminar** para clientes interesados (antes del levantamiento)
3. **Análisis consolidado** del portafolio verde para comité e inversionistas

---

## Instalación

```bash
pip install -r requirements.txt
```

---

## Setup inicial

La base de datos y el modelo no se incluyen en el repositorio; se generan
localmente la primera vez:

```bash
# 1. Colocar las 200 fichas simuladas en data/simulated/fichas/

# 2. Poblar la base de datos procesándolas en lote (Flujo 1)
python src/procesar_ficha.py --carpeta data/simulated/fichas/

# 3. Entrenar el modelo ML y generar el .pkl (notebook, Sección B)
jupyter notebook notebooks/analisis_credito_terra.ipynb
```

> La base de datos (`credito_terra.db`) se puebla en el paso 2 y el modelo
> (`modelo_estimacion.pkl`) se genera en el paso 3. Ninguno está versionado en el repositorio.

---

## Estructura del proyecto

```
credito_terra/
├── src/
│   ├── lector_ficha.py          # Extrae campos de la ficha FLI CT-001
│   ├── validador.py             # Verifica campos, rangos técnicos y consistencia financiera
│   ├── motor_elegibilidad.py    # Evalúa los 10 criterios, recalcula indicadores y emite dictamen
│   ├── generador_informe.py     # Genera el Informe de Evaluación de Elegibilidad (.docx)
│   ├── base_datos.py            # SQLite: duplicados, historial y consultas de portafolio
│   ├── procesar_ficha.py        # Orquesta el Flujo 1 (flags --reevaluar y --carpeta)
│   ├── modelo_estimacion.py     # Random Forest: clasificador de elegibilidad + regresores de GEI y cobertura
│   └── app.py                   # Interfaz Streamlit de estimación preliminar (Flujo 2)
├── data/
│   ├── raw/                     # Ficha plantilla FLI CT-001
│   ├── simulated/fichas/        # Fichas simuladas (pegar aquí las 200)
│   └── outputs/                 # Informes y reportes generados
├── database/
│   └── credito_terra.db         # Generada en el setup inicial (no incluida en repo)
├── models/
│   └── modelo_estimacion.pkl    # Generado en el setup inicial (no incluido en repo)
├── notebooks/
│   └── analisis_credito_terra.ipynb
├── requirements.txt
└── README.md
```

---

## Flujo 1 — Evaluación formal (uso diario)

```bash
# Procesar una ficha nueva
python src/procesar_ficha.py data/simulated/fichas/CT-0001_Empresa_1.xlsx

# Reevaluar un caso existente
python src/procesar_ficha.py data/simulated/fichas/CT-0001_Empresa_1.xlsx --reevaluar
```

El sistema automáticamente:
1. Lee todos los campos de la ficha Excel
2. Valida datos obligatorios e inconsistencias
3. Evalúa los 10 criterios de elegibilidad
4. Genera informe Word en `data/outputs/`
5. Registra el caso en la base de datos (sin duplicados)

---

## Flujo 2 — Estimación preliminar (clientes interesados)

```bash
streamlit run src/app.py
```

Interfaz web donde el analista ingresa datos básicos del proyecto y obtiene:
- Indicadores ambientales estimados (GEI, cobertura energética)
- Probabilidad de elegibilidad (modelo ML)
- Recomendación de viabilidad

---

## Flujo 3 — Portafolio verde (reporte periódico)

```bash
# Abrir en VS Code o Jupyter
notebooks/analisis_credito_terra.ipynb
```

El notebook consulta la BD y genera:
- KPIs del portafolio
- Dashboard con 4 visualizaciones
- Análisis de elegibilidad por sector/etapa/tipo
- Impacto ambiental consolidado con equivalencias
- Análisis del modelo ML
- Reporte Word exportable para inversionistas

---

## Modelo ML — Nota metodológica

El modelo de estimación es una **demostración metodológica** entrenada con datos simulados.

**Umbrales de operación** (Riley et al., 2019. *Statistics in Medicine*, 38(7), 1276–1296):
- Primer entrenamiento real: ≥200 casos evaluados en producción
- Reentrenamiento: cada 150 casos nuevos **o** cuando precisión < 80%
- Validación humana requerida antes de activar cada nueva versión

```bash
# Reentrenar el modelo cuando haya suficientes datos reales
python src/modelo_estimacion.py
```

---

## Destino cubierto
- Energía Solar Fotovoltaica (04 ER.1) — Ficha FLI CT-001

---
