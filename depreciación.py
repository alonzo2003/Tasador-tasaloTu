"""
depreciacion.py
===============
Tablas y lógica de depreciación del Tasador RD — MVP v1

Lógica:
  1. Depreciación base por TIPO de vehículo (sedan, suv, pickup, lujo, comercial)
  2. Modificador por MARCA (Toyota se deprecia menos que Mitsubishi en RD)
  3. Curva de depreciación por AÑOS (no es lineal — los primeros años bajan más)
  4. Valor residual mínimo (ningún vehículo vale 0)

Estos valores son el punto de partida — el tasador experto los puede
ajustar en la sesión de trabajo (v2: tabla experto en DB).
"""

from dataclasses import dataclass
from typing import Optional


# ══════════════════════════════════════════════
# CONFIGURACIÓN GLOBAL
# ══════════════════════════════════════════════

TASA_CAMBIO_DEFAULT = 59.5   # RD$ por USD — actualizar periódicamente
VALOR_RESIDUAL_MIN  = 0.12   # ningún vehículo vale menos del 12% de su precio original


# ══════════════════════════════════════════════
# TABLA 1: DEPRECIACIÓN BASE POR TIPO
# Tasa anual promedio en el mercado dominicano
# Fuente: estimados de mercado RD (refinar con tasador experto)
# ══════════════════════════════════════════════

DEPRECIACION_POR_TIPO = {
    #  tipo          tasa_anual   descripcion
    "sedan":         0.12,   # -12% por año → muy común en RD, oferta alta
    "suv":           0.10,   # -10% por año → demanda fuerte, se deprecia menos
    "pickup":        0.09,   # -9%  por año → alta demanda laboral/comercial
    "lujo":          0.15,   # -15% por año → se deprecia fuerte, mercado pequeño
    "comercial":     0.08,   # -8%  por año → vida útil larga, valor sostenido
    "hatchback":     0.13,   # -13% por año → mercado limitado en RD
    "coupe":         0.14,   # -14% por año → nicho muy pequeño
    "minivan":       0.11,   # -11% por año
}

TIPO_DEFAULT = 0.12  # fallback si el tipo no está en la tabla


# ══════════════════════════════════════════════
# TABLA 2: MODIFICADOR POR MARCA
# Factor multiplicador sobre la tasa base
# 1.0 = sin cambio | <1.0 = se deprecia MENOS | >1.0 = se deprecia MÁS
# Basado en retención de valor en mercado dominicano
# ══════════════════════════════════════════════

MODIFICADOR_POR_MARCA = {
    # Marcas que retienen valor (factor < 1.0 = deprecian MENOS)
    "Toyota":        0.75,   # líder absoluto en RD, Toyota retiene valor muy bien
    "Honda":         0.82,   # muy buscado, retiene bien
    "Nissan":        0.90,   # buena retención, repuestos accesibles
    "Mitsubishi":    0.95,   # aceptable, depende del modelo
    "Kia":           0.95,   # mejorando en RD
    "Hyundai":       0.95,   # similar a Kia
    "Mazda":         0.88,   # buena retención, fanaticos de la marca
    "Isuzu":         0.85,   # pickups muy demandados en RD

    # Marcas promedio (factor ≈ 1.0)
    "Chevrolet":     1.00,
    "Ford":          1.00,
    "Jeep":          1.05,   # depende del modelo
    "Suzuki":        0.98,

    # Marcas europeas / lujo (factor > 1.0 = deprecian MÁS en RD)
    "BMW":           1.20,   # alto costo de mantenimiento en RD
    "Mercedes-Benz": 1.18,   # ídem
    "Audi":          1.22,   # repuestos caros, deprecia más
    "Volkswagen":    1.10,   # mantenimiento caro localmente
    "Volvo":         1.25,   # nicho muy pequeño en RD
    "Land Rover":    1.30,   # muy caro mantener, deprecia fuerte
    "Lexus":         0.90,   # lujo japonés, retiene mejor que europeos
    "Infiniti":      1.05,
    "Acura":         1.00,
}

MARCA_DEFAULT = 1.0  # fallback si la marca no está en la tabla


# ══════════════════════════════════════════════
# TABLA 3: CURVA DE DEPRECIACIÓN POR AÑOS
# La depreciación NO es lineal:
#   - Año 1: baja mucho (el carro sale del dealer)
#   - Años 2-5: baja moderado
#   - Años 6-10: baja lento
#   - Años 10+: casi estable (valor residual)
#
# Estos factores representan qué % del valor ORIGINAL conserva
# el vehículo después de N años de uso.
# ══════════════════════════════════════════════

CURVA_RETENCION = {
    #  años  factor_retencion (% del precio original que conserva)
    0:  1.00,   # nuevo
    1:  0.82,   # -18% primer año (salida del dealer)
    2:  0.73,   # -9% adicional
    3:  0.65,   # -8%
    4:  0.58,   # -7%
    5:  0.52,   # -6%
    6:  0.47,   # -5%
    7:  0.43,   # -4%
    8:  0.39,   # -4%
    9:  0.36,   # -3%
    10: 0.33,   # -3%
    11: 0.30,
    12: 0.28,
    13: 0.26,
    14: 0.24,
    15: 0.22,
    16: 0.21,
    17: 0.20,
    18: 0.19,
    19: 0.18,
    20: 0.17,
}

ANIOS_MAX_TABLA = 20  # para años > 20 usamos el valor residual mínimo


# ══════════════════════════════════════════════
# DATACLASS DE RESULTADO
# ══════════════════════════════════════════════

@dataclass
class ResultadoDepreciacion:
    anios_uso:            int
    factor_retencion_base: float   # factor de la curva (solo años)
    modificador_marca:    float    # factor por marca
    factor_final:         float    # factor combinado aplicado
    tasa_anual_efectiva:  float    # tasa anual resultante (informativo)
    descripcion:          str      # texto explicativo para el reporte


# ══════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════

def calcular_depreciacion(
    anio_vehiculo: int,
    tipo: str,
    marca: str,
    anio_actual: Optional[int] = None
) -> ResultadoDepreciacion:
    """
    Calcula el factor de depreciación para un vehículo.

    Parámetros:
        anio_vehiculo : año del vehículo (ej: 2019)
        tipo          : tipo de vehículo (sedan, suv, pickup, lujo, comercial)
        marca         : marca del vehículo (Toyota, Honda, BMW, etc.)
        anio_actual   : año de referencia (por defecto: año actual)

    Retorna:
        ResultadoDepreciacion con todos los factores aplicados
    """
    from datetime import datetime
    if anio_actual is None:
        anio_actual = datetime.now().year

    anios_uso = max(0, anio_actual - anio_vehiculo)

    # 1. Factor base de la curva por años
    if anios_uso >= ANIOS_MAX_TABLA:
        factor_base = VALOR_RESIDUAL_MIN
    else:
        factor_base = CURVA_RETENCION.get(anios_uso, VALOR_RESIDUAL_MIN)

    # 2. Modificador por marca
    mod_marca = MODIFICADOR_POR_MARCA.get(marca, MARCA_DEFAULT)

    # 3. Ajuste por tipo sobre el factor base
    # Las marcas que deprecian más "empujan" el factor base hacia abajo
    # usando la tasa del tipo como peso del ajuste adicional
    tasa_tipo = DEPRECIACION_POR_TIPO.get(tipo.lower(), TIPO_DEFAULT)

    # Factor combinado: ajustamos la retención base con el modificador de marca
    # Si mod_marca > 1.0 (deprecia más), reducimos el factor de retención
    # Si mod_marca < 1.0 (deprecia menos), aumentamos el factor de retención
    ajuste = (mod_marca - 1.0) * tasa_tipo * anios_uso
    factor_final = max(VALOR_RESIDUAL_MIN, factor_base - ajuste)

    # 4. Tasa anual efectiva (informativo)
    if anios_uso > 0:
        tasa_efectiva = 1 - (factor_final ** (1 / anios_uso))
    else:
        tasa_efectiva = 0.0

    # 5. Descripción legible
    descripcion = _generar_descripcion(anios_uso, factor_final, marca, tipo)

    return ResultadoDepreciacion(
        anios_uso             = anios_uso,
        factor_retencion_base = factor_base,
        modificador_marca     = mod_marca,
        factor_final          = round(factor_final, 4),
        tasa_anual_efectiva   = round(tasa_efectiva, 4),
        descripcion           = descripcion
    )


def _generar_descripcion(anios: int, factor: float, marca: str, tipo: str) -> str:
    """Genera un texto explicativo del resultado de depreciación."""
    pct = round((1 - factor) * 100, 1)
    retencion = round(factor * 100, 1)

    if anios == 0:
        return f"Vehículo nuevo — sin depreciación aplicada."

    if anios == 1:
        tiempo = "1 año de uso"
    else:
        tiempo = f"{anios} años de uso"

    marca_nota = ""
    mod = MODIFICADOR_POR_MARCA.get(marca, MARCA_DEFAULT)
    if mod < 0.90:
        marca_nota = f" {marca} retiene valor muy bien en el mercado dominicano."
    elif mod > 1.10:
        marca_nota = f" {marca} tiene mayor depreciación por costo de mantenimiento local."

    return (
        f"{marca} {tipo} con {tiempo}: ha perdido el {pct}% de su valor original, "
        f"conservando el {retencion}% ({factor:.4f}).{marca_nota}"
    )


# ══════════════════════════════════════════════
# HELPERS ADICIONALES
# ══════════════════════════════════════════════

def get_factor_retencion(anio_vehiculo: int, tipo: str, marca: str) -> float:
    """Shortcut — retorna solo el factor final (0.0 a 1.0)."""
    resultado = calcular_depreciacion(anio_vehiculo, tipo, marca)
    return resultado.factor_final


def listar_tipos_disponibles() -> list:
    return list(DEPRECIACION_POR_TIPO.keys())


def listar_marcas_con_modificador() -> dict:
    return dict(sorted(MODIFICADOR_POR_MARCA.items(), key=lambda x: x[1]))


# ══════════════════════════════════════════════
# EJECUCIÓN DIRECTA — demo / test
# ══════════════════════════════════════════════

if __name__ == "__main__":
    from datetime import datetime

    anio_actual = datetime.now().year

    print("=" * 60)
    print("DEMO — Tablas de Depreciación Tasador RD")
    print("=" * 60)

    casos = [
        (anio_actual - 1,  "sedan",   "Toyota",        "Corolla 1 año"),
        (anio_actual - 3,  "sedan",   "Toyota",        "Corolla 3 años"),
        (anio_actual - 5,  "suv",     "Honda",         "CR-V 5 años"),
        (anio_actual - 7,  "pickup",  "Nissan",        "Frontier 7 años"),
        (anio_actual - 10, "lujo",    "BMW",           "BMW 10 años"),
        (anio_actual - 5,  "lujo",    "Mercedes-Benz", "Mercedes 5 años"),
        (anio_actual - 5,  "suv",     "Toyota",        "RAV4 5 años"),
        (anio_actual - 12, "sedan",   "Honda",         "Civic 12 años"),
    ]

    for anio, tipo, marca, etiqueta in casos:
        r = calcular_depreciacion(anio, tipo, marca)
        print(f"\n  {etiqueta}")
        print(f"    Factor final    : {r.factor_final:.4f}  ({round(r.factor_final*100, 1)}% del valor original)")
        print(f"    Tasa efectiva   : {round(r.tasa_anual_efectiva*100, 1)}% anual")
        print(f"    Mod. marca      : {r.modificador_marca}")
        print(f"    → {r.descripcion}")

    print("\n" + "=" * 60)
    print("Marcas ordenadas por retención de valor (menor = mejor):")
    for marca, mod in listar_marcas_con_modificador().items():
        barra = "▓" * int(mod * 10)
        etiq = "retiene bien" if mod < 0.90 else ("normal" if mod <= 1.05 else "deprecia más")
        print(f"  {marca:<20} {mod:.2f}  {barra}  {etiq}")