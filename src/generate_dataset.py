"""
generate_dataset.py
===================
Genera un dataset sintético de cobranza que simula el comportamiento de
llamadas del Discador y del Equipo Móvil para ~50,000 clientes durante 30 días.

Uso:
    python src/generate_dataset.py

Salida:
    data/cobranza_dataset.csv   → registros diarios por cliente (features finales)
    data/cobranza_raw.csv       → registros de llamadas individuales (opcional)
"""

import numpy as np
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# =============================================================
# CONFIGURACIÓN
# =============================================================
RANDOM_SEED       = 42
N_CLIENTES        = 50_000
N_DIAS            = 30          # días de historial
FECHA_INICIO      = "2024-01-01"

# Parámetros de simulación - Discador
LAMBDA_DISCADOR        = 15.0   # promedio llamadas/día (Poisson)
P_CONTACTO_DISCADOR    = 0.08   # probabilidad de contacto por llamada
DUR_DISCADOR_MEDIA     = 12     # segundos si NO hay contacto
DUR_DISCADOR_CONTACTO  = 180    # segundos si HAY contacto

# Parámetros de simulación - Móvil
MIN_LLAMADAS_MOVIL     = 1
MAX_LLAMADAS_MOVIL     = 4
P_CONTACTO_MOVIL       = 0.45   # probabilidad de contacto por llamada
DUR_MOVIL_MEDIA        = 25     # segundos si NO hay contacto
DUR_MOVIL_CONTACTO     = 240    # segundos si HAY contacto

# Carpeta de salida
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

np.random.seed(RANDOM_SEED)

# =============================================================
# 1. PERFIL DEL CLIENTE (estático)
# =============================================================
print("🔄 Generando perfiles de clientes...")

clientes = pd.DataFrame({
    "id_cliente": np.arange(1, N_CLIENTES + 1),
    # Días de mora: 1-180, con distribución sesgada a la derecha
    "tramo_mora": np.random.exponential(scale=45, size=N_CLIENTES).clip(1, 180).astype(int),
    # Monto de deuda: entre $100 y $50,000
    "monto_deuda": np.round(np.random.lognormal(mean=7.5, sigma=1.2, size=N_CLIENTES), 2),
    # Score histórico de comportamiento de pago: 0-1
    "score_comportamiento_historico": np.random.beta(a=2, b=3, size=N_CLIENTES).round(4),
    # Algunos clientes son más "contestaban" que otros (factor latente)
    "propension_contestar": np.random.beta(a=2, b=4, size=N_CLIENTES),
})
clientes["monto_deuda"] = clientes["monto_deuda"].clip(100, 50000)

# =============================================================
# 2. SIMULACIÓN DIARIA DE LLAMADAS
# =============================================================
print(f"🔄 Simulando {N_DIAS} días de llamadas para {N_CLIENTES:,} clientes...")

fechas = pd.date_range(start=FECHA_INICIO, periods=N_DIAS, freq="D")
registros = []

for dia_idx, fecha in enumerate(fechas):
    if (dia_idx + 1) % 5 == 0:
        print(f"   Día {dia_idx + 1}/{N_DIAS}...")

    # ── Discador ──────────────────────────────────────────────
    llamadas_discador = np.random.poisson(lam=LAMBDA_DISCADOR, size=N_CLIENTES).clip(0, 35)
    # Contacto efectivo discador: al menos UNA llamada logra contacto
    # (probabilidad de ningún contacto = (1-p)^n)
    p_ninguno_discador = (1 - P_CONTACTO_DISCADOR) ** np.maximum(llamadas_discador, 1)
    contacto_discador = (np.random.rand(N_CLIENTES) > p_ninguno_discador).astype(int)
    # Ajuste: si hay 0 llamadas, no puede haber contacto
    contacto_discador[llamadas_discador == 0] = 0

    # Duración promedio llamadas Discador
    dur_disc_base = np.random.exponential(DUR_DISCADOR_MEDIA, N_CLIENTES)
    dur_disc_contacto = np.random.normal(DUR_DISCADOR_CONTACTO, 40, N_CLIENTES).clip(30)
    duracion_discador = np.where(contacto_discador == 1, dur_disc_contacto, dur_disc_base).round(1)
    duracion_discador[llamadas_discador == 0] = 0

    # ── Móvil ─────────────────────────────────────────────────
    # No todos los clientes reciben llamada móvil cada día (prioridad)
    recibe_movil = np.random.rand(N_CLIENTES) < 0.6  # 60% probabilidad de ser contactado
    llamadas_movil = np.where(
        recibe_movil,
        np.random.randint(MIN_LLAMADAS_MOVIL, MAX_LLAMADAS_MOVIL + 1, N_CLIENTES),
        0
    )
    # Propensión del cliente influye en si contesta al Móvil
    p_contacto_movil_personal = (P_CONTACTO_MOVIL * (0.5 + clientes["propension_contestar"].values)).clip(0, 0.95)
    p_ninguno_movil = (1 - p_contacto_movil_personal) ** np.maximum(llamadas_movil, 1)
    contacto_movil = (np.random.rand(N_CLIENTES) > p_ninguno_movil).astype(int)
    contacto_movil[llamadas_movil == 0] = 0

    dur_mov_base = np.random.exponential(DUR_MOVIL_MEDIA, N_CLIENTES)
    dur_mov_contacto = np.random.normal(DUR_MOVIL_CONTACTO, 60, N_CLIENTES).clip(30)
    duracion_movil = np.where(contacto_movil == 1, dur_mov_contacto, dur_mov_base).round(1)
    duracion_movil[llamadas_movil == 0] = 0

    # ── Último canal de contacto ───────────────────────────────
    ultimo_canal = np.where(
        contacto_movil == 1, "Móvil",
        np.where(contacto_discador == 1, "Discador", "Ninguno")
    )

    # ── Hora del último contacto ───────────────────────────────
    hora_contacto = np.where(
        (contacto_movil == 1) | (contacto_discador == 1),
        np.random.randint(8, 20, N_CLIENTES),
        -1  # -1 = sin contacto
    )

    registros.append(pd.DataFrame({
        "id_cliente": clientes["id_cliente"].values,
        "fecha": fecha,
        "cantidad_llamadas_discador_ult_24h": llamadas_discador,
        "cantidad_llamadas_movil_ult_24h": llamadas_movil,
        "contacto_efectivo_discador_ult_24h": contacto_discador,
        "contacto_efectivo_movil_ult_24h": contacto_movil,
        "duracion_llamada_discador": duracion_discador,
        "duracion_llamada_movil": duracion_movil,
        "ultimo_canal_de_contacto": ultimo_canal,
        "hora_ultimo_contacto": hora_contacto,
    }))

df_diario = pd.concat(registros, ignore_index=True)
df_diario = df_diario.sort_values(["id_cliente", "fecha"]).reset_index(drop=True)

# =============================================================
# 3. FEATURE ENGINEERING
# =============================================================
print("🔄 Aplicando feature engineering...")

# Merge con perfil del cliente
df_diario = df_diario.merge(
    clientes[["id_cliente", "tramo_mora", "monto_deuda", "score_comportamiento_historico"]],
    on="id_cliente", how="left"
)

# Ordenar por cliente y fecha para cálculos rolling
df_diario = df_diario.sort_values(["id_cliente", "fecha"])

# Agrupar por cliente para calcular variables rolling (últimos 7 días)
def rolling_features(group):
    # Ratio de contacto móvil en últimos 7 días
    group["ratio_contacto_movil_7d"] = (
        group["contacto_efectivo_movil_ult_24h"]
        .rolling(window=7, min_periods=1)
        .mean()
        .round(4)
    )
    # Tendencia de llamadas del Discador en 7 días (slope aproximado)
    group["tendencia_llamadas_discador_7d"] = (
        group["cantidad_llamadas_discador_ult_24h"]
        .rolling(window=7, min_periods=3)
        .apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 3 else 0, raw=True)
        .round(4)
    )
    # Días desde el último contacto directo (Móvil o Discador)
    contacto_hoy = (
        (group["contacto_efectivo_movil_ult_24h"] == 1) |
        (group["contacto_efectivo_discador_ult_24h"] == 1)
    )
    # cumcount de días sin contacto
    dias_sin = []
    contador = 0
    for c in contacto_hoy:
        if c:
            contador = 0
        else:
            contador += 1
        dias_sin.append(contador)
    group["dias_desde_ultimo_contacto_directo"] = dias_sin

    # Ratio contacto discador 7d
    group["ratio_contacto_discador_7d"] = (
        group["contacto_efectivo_discador_ult_24h"]
        .rolling(window=7, min_periods=1)
        .mean()
        .round(4)
    )
    return group

print("   Calculando features rolling (esto puede tardar 1-2 min)...")
df_diario = df_diario.groupby("id_cliente", group_keys=False).apply(rolling_features)

# =============================================================
# 4. VARIABLE OBJETIVO (TARGET)
# =============================================================
print("🔄 Calculando variable objetivo (target del día siguiente)...")

# El target es si MAÑANA habrá contacto efectivo (Móvil o Discador)
# Lo construimos como el shift(-1) del contacto efectivo de cualquier canal
df_diario["contacto_efectivo_hoy"] = (
    (df_diario["contacto_efectivo_movil_ult_24h"] == 1) |
    (df_diario["contacto_efectivo_discador_ult_24h"] == 1)
).astype(int)

# target = contacto_efectivo del día siguiente (por cliente)
df_diario["target"] = (
    df_diario.groupby("id_cliente")["contacto_efectivo_hoy"]
    .shift(-1)
)

# El MÓVIL tiene efecto mucho mayor: si contacto_movil=1 hoy, target mañana es 1 con mucha más probabilidad
# Esto ya está capturado porque el target real depende del comportamiento del siguiente día.
# Adicionalmente, amplificamos el efecto móvil con un boost de ruido
boost_movil = df_diario["contacto_efectivo_movil_ult_24h"] * 0.3
noise = np.random.randn(len(df_diario)) * 0.1
prob_target = (df_diario["target"].fillna(0) + boost_movil + noise).clip(0, 1)
df_diario["target"] = (prob_target > 0.5).astype(float)

# Eliminar el último día de cada cliente (target=NaN)
df_diario = df_diario.dropna(subset=["target"])
df_diario["target"] = df_diario["target"].astype(int)

# =============================================================
# 5. RANKING ACTUAL (sistema legacy 1-10)
# =============================================================
print("🔄 Calculando ranking actual del sistema...")

# El sistema actual hace un score simple basado en suma de contactos sin ponderar
score_legacy = (
    df_diario["contacto_efectivo_discador_ult_24h"] * 0.3 +
    df_diario["contacto_efectivo_movil_ult_24h"] * 0.3 +
    (df_diario["cantidad_llamadas_discador_ult_24h"] / 30) * 0.2 +
    df_diario["score_comportamiento_historico"] * 0.2
)
# Invertir: rank 1 = mayor prioridad
df_diario["ranking_actual"] = pd.qcut(
    score_legacy, q=10, labels=range(1, 11), duplicates="drop"
).astype(int)

# =============================================================
# 6. LIMPIEZA FINAL Y GUARDADO
# =============================================================
print("🔄 Guardando dataset final...")

COLUMNAS_FINALES = [
    "id_cliente", "fecha",
    # Datos crudos del día
    "cantidad_llamadas_discador_ult_24h",
    "cantidad_llamadas_movil_ult_24h",
    "contacto_efectivo_discador_ult_24h",
    "contacto_efectivo_movil_ult_24h",
    "duracion_llamada_discador",
    "duracion_llamada_movil",
    "ultimo_canal_de_contacto",
    "hora_ultimo_contacto",
    # Perfil del cliente
    "tramo_mora",
    "monto_deuda",
    "score_comportamiento_historico",
    # Feature engineering
    "ratio_contacto_movil_7d",
    "ratio_contacto_discador_7d",
    "tendencia_llamadas_discador_7d",
    "dias_desde_ultimo_contacto_directo",
    # Sistema legacy
    "ranking_actual",
    # Target
    "target",
]
df_final = df_diario[COLUMNAS_FINALES].copy()

output_path = DATA_DIR / "cobranza_dataset.csv"
df_final.to_csv(output_path, index=False)

print("\n" + "=" * 60)
print("✅ Dataset generado exitosamente")
print("=" * 60)
print(f"   📁 Ruta: {output_path}")
print(f"   📊 Filas (registros diarios): {len(df_final):,}")
print(f"   📋 Columnas: {len(df_final.columns)}")
print(f"   🎯 Distribución del target:")
print(f"      0 (sin contacto mañana): {(df_final['target']==0).sum():,} ({(df_final['target']==0).mean()*100:.1f}%)")
print(f"      1 (contacto mañana):     {(df_final['target']==1).sum():,} ({(df_final['target']==1).mean()*100:.1f}%)")
print(f"   🗓️  Rango de fechas: {df_final['fecha'].min()} → {df_final['fecha'].max()}")
print(f"   👥 Clientes únicos: {df_final['id_cliente'].nunique():,}")
print(f"\n📌 Muestra de datos:")
print(df_final.head(3).to_string())
