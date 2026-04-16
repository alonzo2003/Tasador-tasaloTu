#logica de tasacion

"""
motor.py
========
Motor de Tasación — Tasador RD MVP v1
 
Flujo completo:
  1. Recibe: marca, modelo, tipo, año
  2. Busca precio base en DB local
  3. Si no existe → scraper (Supercarros) [v2]
  4. Aplica depreciación (depreciacion.py)
  5. Aplica impuestos DGII básicos
  6. Convierte a RD$ con tasa de cambio actual
  7. Guarda en historial (tasaciones)
  8. Retorna TasacionResultado completo
 
Diseñado para crecer:
  - Millaje, estado, accidentes → v2
  - Scraper activo              → v2
  - Conocimiento experto        → v3
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import os
import sys


#Aseguramos que el directorio raiz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from depreciación import calcular_depreciacion, ResultadoDepreciacion
from base_datos import (
    inicializar_db, get_session, buscar_vehiculo, guardar_tasacion, Marca, Modelo
)

# ══════════════════════════════════════════════
# CONFIGURACIÓN DEL MOTOR
# ═════════════════════════════════════════════

# Tasa de cambio RD$ por USD
#Todo v2: obtener automaticamente del Banco Central
TASA_CAMBIO = 59.5

#Precios base estimados por tipo de vehículo (en USD) cuando No hay registro en DB
#Son promedios de mercado - el scraper los reemplazará en v2

PRECIOS_BASE_ESTIMADOS = {
    'sedan': 18_000,
    'suv': 28_000,
    'pickup': 32_000,
    'lujo': 55_000,
    'comercial': 25_000,
    'hatchback': 15_000,
    'coupe': 22_000,
    'minivan': 20_000,
    }

# Imppuestos simplificados para MVP
# Fuente: DGII / Aduanas Rd (aproximados - refinar con tasador)
IMPUESTOS = {
    "local": {
    # Vehículo ya en RD con placa
    "tasa_dgii":  0.01,   # 1% del valor comercial (marbete anual aprox)
    "itbis":      0.00,   # no aplica para vehículos usados locales
    "placa":      3_500,  # RD$ fijos estimados (marbete + trámites)
    "descripcion": "Vehículo local — marbete + trámites DGII"
},
"importado_nuevo": {
    # Importado nuevo (CIF)
    "tasa_dgii":  0.20,   # 20% arancel sobre valor CIF
    "itbis":      0.18,   # 18% ITBIS sobre (CIF + arancel)
    "placa":      8_500,  # RD$ fijos primera placa
    "descripcion": "Importado nuevo — arancel 20% + ITBIS 18%"
},
"importado_usado": {
    # Importado usado
    "tasa_dgii":  0.17,   # 17% sobre valor depreciado CIF
    "itbis":      0.18,   # 18% ITBIS
    "placa":      8_500,
    "descripcion": "Importado usado — arancel 17% + ITBIS 18%"
},
}

# ══════════════════════════════════════════════
# DATACLASSES DE ENTRADA Y SALIDA
# ══════════════════════════════════════════════

@dataclass
class DatosVehiculo:
    """
    Entrada del motor — MVP v1.
    Campos mínimos para tasar.
    """
    marca:    str
    modelo:   str
    tipo:     str          # sedan, suv, pickup, lujo, comercial
    anio:     int
    origen:   str = "local"   # local | importado_nuevo | importado_usado
    tasador:  str = "sistema"
    notas:    str = ""


@dataclass
class DesglosePrecio:
    """Desglose detallado de cómo se llegó al precio final."""
    precio_base_usd:      float   # precio de referencia en USD
    fuente_precio:        str     # "db_local", "estimado", "scraper"

    depreciacion:         ResultadoDepreciacion

    valor_comercial_usd:  float   # precio_base × factor_depreciacion
    valor_comercial_rd:   float   # valor_comercial_usd × tasa_cambio

    impuesto_dgii_rd:     float   # arancel/DGII en RD$
    itbis_rd:             float   # ITBIS en RD$
    placa_rd:             float   # marbete/placa en RD$
    total_impuestos_rd:   float   # suma de todos los impuestos

    tasa_cambio:          float   # RD$ por USD usado
    descripcion_impuesto: str


@dataclass
class TasacionResultado:
    """
    Resultado completo de una tasación.
    Este objeto se guarda en DB y genera el PDF.
    """
    # Datos del vehículo
    datos:          DatosVehiculo

    # Desglose completo
    desglose:       DesglosePrecio

    # Resultado final
    valor_final_rd: float
    valor_final_usd: float

    # Metadata
    fecha:          datetime = field(default_factory=datetime.now)
    id_tasacion:    Optional[int] = None
    exitoso:        bool = True
    mensaje:        str = "Tasación completada exitosamente."

    def resumen(self) -> str:
        """Texto corto para mostrar en consola o interfaz."""
        d = self.desglose
        v = self.datos
        lineas = [
            "=" * 55,
            f"  TASACIÓN — {v.marca.upper()} {v.modelo.upper()} {v.anio}",
            "=" * 55,
            f"  Tipo          : {v.tipo.capitalize()}",
            f"  Origen        : {v.origen.replace('_', ' ').capitalize()}",
            f"  Años de uso   : {d.depreciacion.anios_uso} año(s)",
            f"  Fuente precio : {d.fuente_precio}",
            "-" * 55,
            f"  Precio base   : USD {d.precio_base_usd:>10,.0f}",
            f"  Factor depr.  : {d.depreciacion.factor_final:.4f}  "
            f"({round(d.depreciacion.factor_final*100,1)}% del original)",
            f"  Valor comerc. : USD {d.valor_comercial_usd:>10,.0f}",
            f"  Tasa cambio   : RD$ {d.tasa_cambio}",
            "-" * 55,
            f"  Valor comerc. : RD$ {d.valor_comercial_rd:>11,.0f}",
            f"  Impuestos     : RD$ {d.total_impuestos_rd:>11,.0f}",
            f"    · DGII/Aran.: RD$ {d.impuesto_dgii_rd:>11,.0f}",
            f"    · ITBIS     : RD$ {d.itbis_rd:>11,.0f}",
            f"    · Placa/Mrb.: RD$ {d.placa_rd:>11,.0f}",
            "=" * 55,
            f"  VALOR FINAL   : RD$ {self.valor_final_rd:>11,.0f}",
            f"                  USD {self.valor_final_usd:>10,.0f}",
            "=" * 55,
            f"  {d.depreciacion.descripcion}",
            f"  {d.descripcion_impuesto}",
            f"  Fecha: {self.fecha.strftime('%d/%m/%Y %H:%M')}",
        ]
        if self.id_tasacion:
            lineas.append(f"  ID Tasación: #{self.id_tasacion}")
        return "\n".join(lineas)


# ══════════════════════════════════════════════
# MOTOR PRINCIPAL
# ══════════════════════════════════════════════

class MotorTasacion:
    """
    Motor central del tasador.
    Instanciar una vez y reutilizar para múltiples tasaciones.
    """

    def __init__(self, tasa_cambio: float = TASA_CAMBIO):
        self.tasa_cambio = tasa_cambio
        self.engine  = inicializar_db()
        self.session = get_session(self.engine)
        print(f"🚗 Motor de tasación iniciado | Tasa: RD${tasa_cambio}/USD")

    # ──────────────────────────────────────────
    # MÉTODO PRINCIPAL
    # ──────────────────────────────────────────

    def tasar(self, datos: DatosVehiculo) -> TasacionResultado:
        """
        Ejecuta la tasación completa para un vehículo.

        Parámetros:
            datos : DatosVehiculo con marca, modelo, tipo, año, origen

        Retorna:
            TasacionResultado con desglose completo y valor final en RD$
        """
        print(f"\n▶ Tasando: {datos.marca} {datos.modelo} {datos.anio}...")

        try:
            # PASO 1: Obtener precio base
            precio_usd, fuente = self._obtener_precio_base(datos)
            print(f"  ✓ Precio base: USD {precio_usd:,.0f} [{fuente}]")

            # PASO 2: Calcular depreciación
            dep = calcular_depreciacion(
                anio_vehiculo = datos.anio,
                tipo          = datos.tipo,
                marca         = datos.marca
            )
            print(f"  ✓ Factor depreciación: {dep.factor_final:.4f} "
                  f"({dep.anios_uso} años, mod. marca {dep.modificador_marca})")

            # PASO 3: Valor comercial
            valor_comercial_usd = round(precio_usd * dep.factor_final, 2)
            valor_comercial_rd  = round(valor_comercial_usd * self.tasa_cambio, 2)
            print(f"  ✓ Valor comercial: USD {valor_comercial_usd:,.0f} "
                  f"| RD$ {valor_comercial_rd:,.0f}")

            # PASO 4: Impuestos
            imp = self._calcular_impuestos(valor_comercial_usd, datos.origen)
            print(f"  ✓ Impuestos: RD$ {imp['total']:,.0f} [{datos.origen}]")

            # PASO 5: Valor final
            valor_final_rd  = round(valor_comercial_rd + imp["total"], 2)
            valor_final_usd = round(valor_final_rd / self.tasa_cambio, 2)
            print(f"  ✓ Valor final: RD$ {valor_final_rd:,.0f}")

            # PASO 6: Ensamblar resultado
            desglose = DesglosePrecio(
                precio_base_usd      = precio_usd,
                fuente_precio        = fuente,
                depreciacion         = dep,
                valor_comercial_usd  = valor_comercial_usd,
                valor_comercial_rd   = valor_comercial_rd,
                impuesto_dgii_rd     = imp["dgii"],
                itbis_rd             = imp["itbis"],
                placa_rd             = imp["placa"],
                total_impuestos_rd   = imp["total"],
                tasa_cambio          = self.tasa_cambio,
                descripcion_impuesto = imp["descripcion"],
            )

            resultado = TasacionResultado(
                datos           = datos,
                desglose        = desglose,
                valor_final_rd  = valor_final_rd,
                valor_final_usd = valor_final_usd,
            )

            # PASO 7: Guardar en historial
            resultado.id_tasacion = self._guardar_historial(resultado)
            print(f"  ✓ Guardado en historial con ID #{resultado.id_tasacion}")

            return resultado

        except Exception as e:
            print(f"  ✗ Error en tasación: {e}")
            return TasacionResultado(
                datos           = datos,
                desglose        = None,
                valor_final_rd  = 0,
                valor_final_usd = 0,
                exitoso         = False,
                mensaje         = f"Error: {str(e)}"
            )

    # ──────────────────────────────────────────
    # PASO 1: OBTENER PRECIO BASE
    # ──────────────────────────────────────────

    def _obtener_precio_base(self, datos: DatosVehiculo) -> tuple[float, str]:
        """
        Jerarquía de búsqueda:
          1. DB local (vehículo registrado con precio)
          2. Estimado por tipo (fallback MVP)
          3. Scraper Supercarros [TODO v2]
        """
        # Intento 1: DB local
        vehiculo = buscar_vehiculo(
            self.session, datos.marca, datos.modelo, datos.anio
        )
        if vehiculo and vehiculo.precio_base_usd:
            return vehiculo.precio_base_usd, "db_local"

        # Intento 2: Estimado por tipo (MVP fallback)
        tipo_norm = datos.tipo.lower()
        if tipo_norm in PRECIOS_BASE_ESTIMADOS:
            precio = PRECIOS_BASE_ESTIMADOS[tipo_norm]
            print(f"  ⚠ No encontrado en DB — usando estimado por tipo ({tipo_norm})")
            return float(precio), "estimado"

        # Intento 3: Fallback absoluto
        print(f"  ⚠ Tipo '{datos.tipo}' no reconocido — usando sedan como base")
        return float(PRECIOS_BASE_ESTIMADOS["sedan"]), "estimado_fallback"

    # ──────────────────────────────────────────
    # PASO 4: CALCULAR IMPUESTOS
    # ──────────────────────────────────────────

    def _calcular_impuestos(self, valor_usd: float, origen: str) -> dict:
        """
        Calcula impuestos según el origen del vehículo.
        Retorna dict con dgii, itbis, placa, total, descripcion.
        """
        config = IMPUESTOS.get(origen, IMPUESTOS["local"])

        valor_rd = valor_usd * self.tasa_cambio

        dgii  = round(valor_rd * config["tasa_dgii"], 2)
        itbis = round((valor_rd + dgii) * config["itbis"], 2)
        placa = config["placa"]
        total = round(dgii + itbis + placa, 2)

        return {
            "dgii":        dgii,
            "itbis":       itbis,
            "placa":       placa,
            "total":       total,
            "descripcion": config["descripcion"],
        }

    # ──────────────────────────────────────────
    # PASO 7: GUARDAR HISTORIAL
    # ──────────────────────────────────────────

    def _guardar_historial(self, r: TasacionResultado) -> int:
        """Persiste la tasación en la tabla tasaciones y retorna su ID."""
        d = r.desglose
        t = guardar_tasacion(self.session, {
            "fecha":               r.fecha,
            "marca":               r.datos.marca,
            "modelo":              r.datos.modelo,
            "tipo":                r.datos.tipo,
            "anio":                r.datos.anio,
            "precio_base_usd":     d.precio_base_usd,
            "factor_depreciacion": d.depreciacion.factor_final,
            "valor_comercial_usd": d.valor_comercial_usd,
            "tasa_cambio":         d.tasa_cambio,
            "impuestos_rd":        d.total_impuestos_rd,
            "valor_final_rd":      r.valor_final_rd,
            "tasador":             r.datos.tasador,
            "notas":               r.datos.notas,
        })
        return t.id

    # ──────────────────────────────────────────
    # UTILIDADES
    # ──────────────────────────────────────────

    def actualizar_tasa_cambio(self, nueva_tasa: float):
        """Actualiza la tasa de cambio sin reiniciar el motor."""
        self.tasa_cambio = nueva_tasa
        print(f"✓ Tasa de cambio actualizada: RD${nueva_tasa}/USD")

    def cerrar(self):
        """Cierra la sesión de DB limpiamente."""
        self.session.close()
        print("Motor cerrado.")


# ══════════════════════════════════════════════
# FUNCIÓN RÁPIDA (sin instanciar la clase)
# ══════════════════════════════════════════════

def tasar_rapido(
    marca:  str,
    modelo: str,
    tipo:   str,
    anio:   int,
    origen: str = "local",
    tasa:   float = TASA_CAMBIO
) -> TasacionResultado:
    """
    Shortcut para tasar un vehículo en una línea.

    Ejemplo:
        resultado = tasar_rapido("Toyota", "Corolla", "sedan", 2020)
        print(resultado.resumen())
    """
    motor = MotorTasacion(tasa_cambio=tasa)
    datos = DatosVehiculo(
        marca=marca, modelo=modelo,
        tipo=tipo, anio=anio, origen=origen
    )
    resultado = motor.tasar(datos)
    motor.cerrar()
    return resultado


# ══════════════════════════════════════════════
# EJECUCIÓN DIRECTA — demo
# ══════════════════════════════════════════════

if __name__ == "__main__":
    motor = MotorTasacion()

    casos = [
        DatosVehiculo("Toyota",        "Corolla",   "sedan",    2020, "local"),
        DatosVehiculo("Honda",         "CR-V",      "suv",      2019, "local"),
        DatosVehiculo("Nissan",        "Frontier",  "pickup",   2018, "local"),
        DatosVehiculo("BMW",           "Serie 3",   "lujo",     2021, "importado_usado"),
        DatosVehiculo("Toyota",        "RAV4",      "suv",      2022, "importado_nuevo"),
        DatosVehiculo("Mercedes-Benz", "Clase C",   "lujo",     2017, "local"),
    ]

    for datos in casos:
        resultado = motor.tasar(datos)
        if resultado.exitoso:
            print("\n" + resultado.resumen())
        else:
            print(f"\n✗ Error tasando {datos.marca} {datos.modelo}: {resultado.mensaje}")
        print()

    motor.cerrar()