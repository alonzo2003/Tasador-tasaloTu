"""
main.py
=====
interfaz principal - tasador RD MVP V1

modes de uso:
  1. Interactivo  : python main.py
  2. Directo      : python main.py --marca Toyota --modelo Corolla --tipo sedan --anio 2020
  3. Historial    : python main.py --historial
  4. Listar marcas: python main.py --marcas

Flujo interactivo:
  → Selecciona marca
  → Selecciona modelo
  → Ingresa año
  → Selecciona origen
  → Motor calcula
  → Muestra resultado
  → Opción de generar PDF
"""
import argparse
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor import MotorTasacion, DatosVehiculo, tasar_rapido
from base_datos import (
    inicializar_db, get_session, listar_marcas, listar_modelos, Tasacion
)

# ══════════════════════════════════════════════
# CONSTANTES DE UI
# ══════════════════════════════════════════════

BANNER = """
╔══════════════════════════════════════════════╗
║       TASADOR DE VEHÍCULOS — RD  v1.0        ║
║       República Dominicana                   ║
╚══════════════════════════════════════════════╝
"""

TIPOS_VALIDOS = ['sedan', 'suv', 'pickup', 'lujo', 'comercial', 'hatchback', 'minivan']
ORIGENES = {
    "1": ("local", "Local(ya tiene placa RD)"),
    "2": ("importado", "Importado (sin placa RD)"),
    "3": ("importado_usado", "Importado usado (con placa RD)")
} 

ANO_MIN = 1990
ANO_MAX = datetime.now().year + 1

# ══════════════════════════════════════════════
# HELPERS DE INPUT
# ══════════════════════════════════════════════

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def separador(char='-', length=50):
    print(char * length)

def titulo(texto: str):
    separador( '=')
    print(f"{texto.center(50)}") 
    separador( '=')

def input_requerido(prompt: str) -> str:
    """Input que no acepta valores vacíos."""
    while True:
        valor = input(prompt).strip()
        if valor:
            return valor
        print("Este campo es obligatorio. Por favor, ingresa un valor.")

def input_numero(promot: str, minimo: int, maximo: int) -> int:
    """input numerico con rango validado."""
    while True:
        try:
            valor = int(input(promot).strip())
            if minimo <= valor <= maximo:
                return valor
            print(f"Por favor, ingresa un número entre {minimo} y {maximo}.")
        except ValueError:
            print("Entrada no válida. Por favor, ingresa un número.")


def input_opcion(prompt: str, opciones: list) -> str:
    """Input que valida contra una lista de opciones"""
    while True:
        valor = input(prompt).strip().lower()
        if valor in [o.lower() for o in opciones]:
            return valor
        print (f"Opcion invalida. opciones: {', '.join(opciones)}")  


def mostrat_lista_numerada(items: list, titulo_col: str = "Opcion") -> None:
    """Muestra una lista con numerada y retorna la selección."""
    for i, item in enumerate(items, 1):
        print(f"{i:>3}. {item}")

def seleccionar_de_lista(items: list, prompt: str) -> str:
    """Muestra una lista numerada y pide seleccion por numero."""
    mostrat_lista_numerada(items)
    idx = input_numero(prompt, 1, len(items)) 
    return items[idx - 1]


# ══════════════════════════════════════════════
# FLUJO INTERACTIVO PRINCIPAL
# ══════════════════════════════════════════════

def flujo_interactivo(motor: MotorTasacion, session) -> None:
    """
    Guía al usuario paso a paso para realizar una tasación.
    """
    print(BANNER)

    # ── PASO 1: MARCA ──────────────────────────
    titulo("PASO 1 — Selecciona la marca")
    marcas = listar_marcas(session)

    if not marcas:
        print("  ⚠ No hay marcas en la base de datos.")
        print("  Ejecuta primero: python base_datos.py")
        return

    marca = seleccionar_de_lista(marcas, "\n  Número de marca: ")
    print(f"\n  ✓ Marca seleccionada: {marca}")

    # ── PASO 2: MODELO ─────────────────────────
    titulo("PASO 2 — Selecciona el modelo")
    modelos_obj = listar_modelos(session, marca)

    if not modelos_obj:
        print(f"  ⚠ No hay modelos registrados para {marca}.")
        print("  Puedes ingresar el modelo manualmente.")
        modelo_nombre = input_requerido("  Modelo: ")
        tipo          = input_opcion(
            f"  Tipo ({'/'.join(TIPOS_VALIDOS)}): ",
            TIPOS_VALIDOS
        )
    else:
        nombres_modelos = [f"{m.nombre}  ({m.tipo})" for m in modelos_obj]
        seleccion       = seleccionar_de_lista(nombres_modelos, "\n  Número de modelo: ")
        idx             = nombres_modelos.index(seleccion)
        modelo_obj      = modelos_obj[idx]
        modelo_nombre   = modelo_obj.nombre
        tipo            = modelo_obj.tipo

    print(f"\n  ✓ Modelo: {modelo_nombre}  |  Tipo: {tipo}")

    # ── PASO 3: AÑO ────────────────────────────
    titulo("PASO 3 — Año del vehículo")
    anio = input_numero(
        f"  Año ({ANO_MIN} - {ANO_MAX}): ",
        ANO_MIN, ANO_MAX
    )
    anios_uso = datetime.now().year - anio
    print(f"\n  ✓ Año: {anio}  |  Años de uso: {anios_uso}")

    # ── PASO 4: ORIGEN ─────────────────────────
    titulo("PASO 4 — Origen del vehículo")
    for key, (_, desc) in ORIGENES.items():
        print(f"  {key}. {desc}")

    origen_key = input_opcion("\n  Selecciona (1/2/3): ", list(ORIGENES.keys()))
    origen, origen_desc = ORIGENES[origen_key]
    print(f"\n  ✓ Origen: {origen_desc}")

    # ── PASO 5: NOTAS OPCIONALES ───────────────
    titulo("PASO 5 — Notas adicionales (opcional)")
    print("  Puedes agregar observaciones para el reporte.")
    notas = input("  Notas (Enter para omitir): ").strip()

    # ── PASO 6: CONFIRMAR ──────────────────────
    titulo("RESUMEN — Confirma los datos")
    print(f"  Marca   : {marca}")
    print(f"  Modelo  : {modelo_nombre}")
    print(f"  Tipo    : {tipo}")
    print(f"  Año     : {anio}  ({anios_uso} años de uso)")
    print(f"  Origen  : {origen_desc}")
    if notas:
        print(f"  Notas   : {notas}")

    separador()
    confirmar = input_opcion(
        "\n  ¿Proceder con la tasación? (s/n): ",
        ["s", "n"]
    )

    if confirmar == "n":
        print("\n  Tasación cancelada.")
        return

    # ── PASO 7: TASAR ──────────────────────────
    print("\n  Calculando...")
    separador()

    datos = DatosVehiculo(
        marca   = marca,
        modelo  = modelo_nombre,
        tipo    = tipo,
        anio    = anio,
        origen  = origen,
        notas   = notas
    )

    resultado = motor.tasar(datos)

    # ── PASO 8: MOSTRAR RESULTADO ──────────────
    print("\n")
    if resultado.exitoso:
        print(resultado.resumen())
        _ofrecer_pdf(resultado)
    else:
        print(f"  ✗ Error: {resultado.mensaje}")

    # ── PASO 9: OTRA TASACIÓN ──────────────────
    separador()
    otra = input_opcion("\n  ¿Realizar otra tasación? (s/n): ", ["s", "n"])
    if otra == "s":
        flujo_interactivo(motor, session)


def _ofrecer_pdf(resultado) -> None:
    """Ofrece generar el PDF del reporte."""
    try:
        from reporte import generar_pdf
        separador()
        generar = input_opcion(
            "\n  ¿Generar reporte PDF? (s/n): ",
            ["s", "n"]
        )
        if generar == "s":
            ruta = generar_pdf(resultado)
            print(f"\n  ✅ PDF generado: {ruta}")
    except ImportError:
        print("\n  ℹ  Módulo de PDF no disponible aún (próximo paso).")


# ══════════════════════════════════════════════
# MODO HISTORIAL
# ══════════════════════════════════════════════

def mostrar_historial(session, limite: int = 20) -> None:
    """Muestra las últimas tasaciones registradas."""
    titulo(f"HISTORIAL — Últimas {limite} tasaciones")

    tasaciones = (
        session.query(Tasacion)
        .order_by(Tasacion.fecha.desc())
        .limit(limite)
        .all()
    )

    if not tasaciones:
        print("  No hay tasaciones registradas aún.")
        return

    print(f"  {'ID':>4}  {'Fecha':<17}  {'Vehículo':<30}  {'Año':>4}  {'Valor Final RD$':>15}")
    separador(ancho=80)

    for t in tasaciones:
        vehiculo = f"{t.marca} {t.modelo}"[:30]
        fecha    = t.fecha.strftime("%d/%m/%Y %H:%M") if t.fecha else "—"
        valor    = f"RD$ {t.valor_final_rd:>12,.0f}" if t.valor_final_rd else "—"
        print(f"  {t.id:>4}  {fecha:<17}  {vehiculo:<30}  {t.anio:>4}  {valor:>15}")

    separador(ancho=80)
    total = session.query(Tasacion).count()
    print(f"\n  Total en historial: {total} tasaciones")


# ══════════════════════════════════════════════
# MODO LISTAR MARCAS
# ══════════════════════════════════════════════

def mostrar_marcas(session) -> None:
    """Lista todas las marcas y modelos disponibles en la DB."""
    titulo("MARCAS Y MODELOS DISPONIBLES")
    marcas = listar_marcas(session)

    if not marcas:
        print("  No hay marcas registradas. Ejecuta: python base_datos.py")
        return

    for marca in marcas:
        modelos = listar_modelos(session, marca)
        nombres = ", ".join([m.nombre for m in modelos])
        print(f"\n  {marca}")
        print(f"    └ {nombres}")

    separador()
    print(f"  Total: {len(marcas)} marcas")


# ══════════════════════════════════════════════
# PARSEO DE ARGUMENTOS
# ══════════════════════════════════════════════

def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tasador de Vehículos RD — MVP v1",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--marca",    type=str, help="Marca del vehículo (ej: Toyota)")
    parser.add_argument("--modelo",   type=str, help="Modelo del vehículo (ej: Corolla)")
    parser.add_argument("--tipo",     type=str,
                        choices=TIPOS_VALIDOS,
                        help="Tipo de vehículo")
    parser.add_argument("--anio",     type=int, help="Año del vehículo (ej: 2020)")
    parser.add_argument("--origen",   type=str,
                        choices=["local", "importado_nuevo", "importado_usado"],
                        default="local",
                        help="Origen del vehículo (default: local)")
    parser.add_argument("--tasa",     type=float,
                        default=59.5,
                        help="Tasa de cambio RD$/USD (default: 59.5)")
    parser.add_argument("--historial", action="store_true",
                        help="Mostrar historial de tasaciones")
    parser.add_argument("--marcas",   action="store_true",
                        help="Listar marcas y modelos disponibles")
    parser.add_argument("--pdf",      action="store_true",
                        help="Generar PDF automáticamente (modo directo)")

    return parser


# ══════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════

def main():
    parser = construir_parser()
    args   = parser.parse_args()

    # Inicializar DB
    engine  = inicializar_db()
    session = get_session(engine)

    # ── MODO: listar marcas ────────────────────
    if args.marcas:
        mostrar_marcas(session)
        session.close()
        return

    # ── MODO: historial ───────────────────────
    if args.historial:
        mostrar_historial(session)
        session.close()
        return

    # ── MODO: directo (argumentos completos) ──
    if args.marca and args.modelo and args.tipo and args.anio:
        motor = MotorTasacion(tasa_cambio=args.tasa)
        datos = DatosVehiculo(
            marca  = args.marca,
            modelo = args.modelo,
            tipo   = args.tipo,
            anio   = args.anio,
            origen = args.origen,
        )
        resultado = motor.tasar(datos)
        motor.cerrar()
        session.close()

        if resultado.exitoso:
            print("\n" + resultado.resumen())
            if args.pdf:
                _ofrecer_pdf(resultado)
        else:
            print(f"\n✗ Error: {resultado.mensaje}")
            sys.exit(1)
        return

    # ── MODO: interactivo (default) ───────────
    try:
        motor = MotorTasacion()
        flujo_interactivo(motor, session)
        motor.cerrar()
    except KeyboardInterrupt:
        print("\n\n  Hasta luego. 🚗")
    finally:
        session.close()


if __name__ == "__main__":
    main()
    
