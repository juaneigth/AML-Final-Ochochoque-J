# Dataset - Instrucciones de Generación

> ⚠️ Los datos reales **no se suben al repositorio**. Se generan localmente con el script de síntesis.

## Descripción del Dataset

Dataset sintético que simula el comportamiento de llamadas de cobranza de un portafolio de ~50,000 clientes durante 30 días.

## ¿Cómo generar el dataset?

```bash
cd ..    # raíz del proyecto
python src/generate_dataset.py
```

Esto creará el archivo `data/cobranza_dataset.csv` (~50,000 filas, una por cliente por día).

## Variables generadas

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `id_cliente` | Numérico | Identificador único del cliente |
| `fecha` | Fecha | Fecha del registro diario |
| `cantidad_llamadas_discador_ult_24h` | Numérico | Llamadas del Discador en las últimas 24h (~0–30) |
| `cantidad_llamadas_movil_ult_24h` | Numérico | Llamadas del Móvil en las últimas 24h (~0–4) |
| `contacto_efectivo_discador_ult_24h` | Binario (0/1) | ¿El Discador logró contacto? |
| `contacto_efectivo_movil_ult_24h` | Binario (0/1) | ¿El Móvil logró contacto? (variable de oro) |
| `duracion_llamada_discador` | Numérico | Duración promedio llamadas Discador (segundos) |
| `duracion_llamada_movil` | Numérico | Duración promedio llamadas Móvil (segundos) |
| `ultimo_canal_de_contacto` | Categórica | 'Discador', 'Móvil', 'Ninguno' |
| `dias_desde_ultimo_contacto_directo` | Numérico | Días desde el último contacto humano exitoso |
| `tramo_mora` | Numérico | Días de atraso en la deuda |
| `monto_deuda` | Numérico | Saldo actual (USD) |
| `score_comportamiento_historico` | Numérico (0–1) | Probabilidad histórica de pago |
| `ratio_contacto_movil_7d` | Numérico | Ratio contactos móvil efectivos en los últimos 7 días |
| `tendencia_llamadas_discador_7d` | Numérico | Tendencia (slope) de llamadas Discador en 7 días |
| `hora_ultimo_contacto` | Numérico | Hora del día del último contacto exitoso |
| `ranking_actual` | Numérico (1–10) | Ranking asignado por el sistema actual |
| `target` | Binario (0/1) | **Variable objetivo**: ¿Habrá contacto efectivo mañana? |

## Criterios de simulación

- **Discador**: Alta frecuencia (Poisson λ≈15), baja tasa de contacto (8%)
- **Móvil**: Baja frecuencia (1–4 llamadas), alta tasa de contacto (45%)
- Si el Móvil logra contacto, el cliente pasa automáticamente a target=1 con alta probabilidad
- El Discador tiene impacto mínimo en el target independientemente del volumen
