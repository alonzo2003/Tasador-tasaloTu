#pdf fase 1 basico

"""
reporte.py
==========
Generador de Reporte PDF — Tasador RD MVP v1
Librería: reportlab
 
Genera un PDF profesional con:
  - Encabezado con nombre del negocio y fecha
  - Datos del vehículo tasado
  - Desglose completo del cálculo
  - Valor final destacado en RD$
  - Pie de página con número de tasación
  - Listo para imprimir o enviar al cliente
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)
from reportlab.platypus import Flowable
 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ══════════════════════════════════════════════
# CONFIGURACIÓN DEL REPORTE
# ══════════════════════════════════════════════

 
NOMBRE_EMPRESA  = "Tasador RD"
SUBTITULO       = "Servicio Profesional de Tasación de Vehículos"
PAIS            = "República Dominicana"
VERSION         = "v1.0"

CARPETA_REPORTES = "reportes"
 
# Paleta de colores
COLOR_PRIMARIO   = colors.HexColor("#1a3a5c")   # azul oscuro marino
COLOR_SECUNDARIO = colors.HexColor("#2e86c1")   # azul medio
COLOR_ACENTO     = colors.HexColor("#e8f4fd")   # azul muy claro (fondo)
COLOR_EXITO      = colors.HexColor("#1e8449")   # verde oscuro
COLOR_EXITO_BG   = colors.HexColor("#eafaf1")   # verde muy claro
COLOR_GRIS       = colors.HexColor("#f2f3f4")   # gris claro tabla
COLOR_GRIS_MED   = colors.HexColor("#aab7b8")   # gris medio separador
COLOR_TEXTO      = colors.HexColor("#2c3e50")   # texto principal
COLOR_TEXTO_SEC  = colors.HexColor("#566573")   # texto secundario
 
 
# ══════════════════════════════════════════════
# ESTILOS
# ══════════════════════════════════════════════
 
def _build_styles():
    base = getSampleStyleSheet()
 
    estilos = {
        "empresa": ParagraphStyle(
            "empresa",
            fontSize=22, fontName="Helvetica-Bold",
            textColor=COLOR_PRIMARIO, alignment=TA_CENTER,
            spaceAfter=2
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            fontSize=10, fontName="Helvetica",
            textColor=COLOR_SECUNDARIO, alignment=TA_CENTER,
            spaceAfter=2
        ),
        "pais": ParagraphStyle(
            "pais",
            fontSize=9, fontName="Helvetica",
            textColor=COLOR_TEXTO_SEC, alignment=TA_CENTER,
            spaceAfter=0
        ),
        "titulo_seccion": ParagraphStyle(
            "titulo_seccion",
            fontSize=11, fontName="Helvetica-Bold",
            textColor=COLOR_PRIMARIO, spaceBefore=14, spaceAfter=6
        ),
        "normal": ParagraphStyle(
            "normal",
            fontSize=10, fontName="Helvetica",
            textColor=COLOR_TEXTO, spaceAfter=4
        ),
        "valor_final_label": ParagraphStyle(
            "valor_final_label",
            fontSize=12, fontName="Helvetica-Bold",
            textColor=COLOR_EXITO, alignment=TA_CENTER,
            spaceAfter=4
        ),
        "valor_final": ParagraphStyle(
            "valor_final",
            fontSize=28, fontName="Helvetica-Bold",
            textColor=COLOR_EXITO, alignment=TA_CENTER,
            spaceAfter=4
        ),
        "valor_usd": ParagraphStyle(
            "valor_usd",
            fontSize=12, fontName="Helvetica",
            textColor=COLOR_EXITO, alignment=TA_CENTER,
            spaceAfter=0
        ),
        "nota": ParagraphStyle(
            "nota",
            fontSize=8, fontName="Helvetica-Oblique",
            textColor=COLOR_TEXTO_SEC, spaceAfter=4
        ),
        "pie": ParagraphStyle(
            "pie",
            fontSize=8, fontName="Helvetica",
            textColor=COLOR_TEXTO_SEC, alignment=TA_CENTER
        ),
        "deprec": ParagraphStyle(
            "deprec",
            fontSize=9, fontName="Helvetica-Oblique",
            textColor=COLOR_TEXTO_SEC, alignment=TA_CENTER,
            spaceAfter=0
        ),
    }
    return estilos
 
 
# ══════════════════════════════════════════════
# GENERADOR PRINCIPAL
# ══════════════════════════════════════════════
 
def generar_pdf(resultado, nombre_tasador: str = "Sistema") -> str:
    """
    Genera el PDF del reporte de tasación.
 
    Parámetros:
        resultado      : TasacionResultado del motor
        nombre_tasador : Nombre del tasador para el pie de página
 
    Retorna:
        ruta del archivo PDF generado
    """
    # Crear carpeta si no existe
    os.makedirs(CARPETA_REPORTES, exist_ok=True)
 
    # Nombre del archivo
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    marca_m  = resultado.datos.marca.replace(" ", "_")
    modelo_m = resultado.datos.modelo.replace(" ", "_")
    nombre   = f"tasacion_{marca_m}_{modelo_m}_{resultado.datos.anio}_{ts}.pdf"
    ruta     = os.path.join(CARPETA_REPORTES, nombre)
 
    # Documento
    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
        title=f"Tasación {resultado.datos.marca} {resultado.datos.modelo}",
        author=NOMBRE_EMPRESA,
    )
 
    estilos = _build_styles()
    story   = []
 
    # ── ENCABEZADO ─────────────────────────────
    story += _seccion_encabezado(estilos, resultado)
 
    # ── DATOS DEL VEHÍCULO ─────────────────────
    story += _seccion_vehiculo(estilos, resultado)
 
    # ── DESGLOSE DEL CÁLCULO ───────────────────
    story += _seccion_desglose(estilos, resultado)
 
    # ── VALOR FINAL ────────────────────────────
    story += _seccion_valor_final(estilos, resultado)
 
    # ── NOTAS ──────────────────────────────────
    if resultado.datos.notas:
        story += _seccion_notas(estilos, resultado.datos.notas)
 
    # ── PIE DE PÁGINA ──────────────────────────
    story += _seccion_pie(estilos, resultado, nombre_tasador)
 
    doc.build(story)
    return ruta
 
 
# ══════════════════════════════════════════════
# SECCIONES DEL REPORTE
# ══════════════════════════════════════════════
 
def _seccion_encabezado(estilos, resultado):
    """Logo textual + nombre empresa + fecha."""
    fecha_str = resultado.fecha.strftime("%d de %B del %Y, %H:%M")
    id_str    = f"Tasación #{resultado.id_tasacion}" if resultado.id_tasacion else ""
 
    bloques = [
        Paragraph(NOMBRE_EMPRESA, estilos["empresa"]),
        Paragraph(SUBTITULO, estilos["subtitulo"]),
        Paragraph(PAIS, estilos["pais"]),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARIO, spaceAfter=6),
 
        # Fila fecha / ID
        Table(
            [[
                Paragraph(f"Fecha: {fecha_str}", estilos["nota"]),
                Paragraph(id_str, ParagraphStyle(
                    "id_right", fontSize=9, fontName="Helvetica-Bold",
                    textColor=COLOR_SECUNDARIO, alignment=TA_RIGHT
                )),
            ]],
            colWidths=["65%", "35%"],
            style=TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")])
        ),
        Spacer(1, 6),
    ]
    return bloques
 
 
def _seccion_vehiculo(estilos, resultado):
    """Tabla con datos básicos del vehículo."""
    d = resultado.datos
    dep = resultado.desglose.depreciacion
    anios = dep.anios_uso
 
    datos_tabla = [
        ["Marca",         d.marca,
         "Año",           str(d.anio)],
        ["Modelo",        d.modelo,
         "Años de uso",   f"{anios} año{'s' if anios != 1 else ''}"],
        ["Tipo",          d.tipo.capitalize(),
         "Origen",        d.origen.replace("_", " ").capitalize()],
    ]
 
    tabla = Table(
        datos_tabla,
        colWidths=["20%", "30%", "20%", "30%"],
        style=TableStyle([
            ("BACKGROUND",  (0, 0), (0, -1), COLOR_ACENTO),
            ("BACKGROUND",  (2, 0), (2, -1), COLOR_ACENTO),
            ("TEXTCOLOR",   (0, 0), (0, -1), COLOR_PRIMARIO),
            ("TEXTCOLOR",   (2, 0), (2, -1), COLOR_PRIMARIO),
            ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
            ("FONTNAME",    (3, 0), (3, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("PADDING",     (0, 0), (-1, -1), 7),
            ("GRID",        (0, 0), (-1, -1), 0.5, COLOR_GRIS_MED),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, COLOR_GRIS]),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
 
    return [
        Paragraph("Datos del Vehículo", estilos["titulo_seccion"]),
        tabla,
        Spacer(1, 4),
    ]
 
 
def _seccion_desglose(estilos, resultado):
    """Tabla de desglose completo del cálculo."""
    d   = resultado.desglose
    dep = d.depreciacion
 
    def fmt_usd(v): return f"USD {v:>12,.0f}"
    def fmt_rd(v):  return f"RD$ {v:>12,.0f}"
 
    pct_retencion = round(dep.factor_final * 100, 1)
    pct_perdida   = round((1 - dep.factor_final) * 100, 1)
 
    filas = [
        # Encabezado
        ["Concepto", "Valor", "Moneda"],
 
        ["Precio base de referencia",
         f"{d.precio_base_usd:>12,.0f}",   "USD"],
 
        [f"Depreciacion acumulada  ({pct_perdida}% en {dep.anios_uso} años)",
         f"- {d.precio_base_usd * (1-dep.factor_final):>11,.0f}",  "USD"],
 
        [f"Factor de retencion de valor  ({pct_retencion}%)",
         f"{dep.factor_final:.4f}",         "factor"],
 
        ["Valor comercial resultante",
         f"{d.valor_comercial_usd:>12,.0f}", "USD"],
 
        [f"Conversion a RD$  (tasa {d.tasa_cambio} RD$/USD)",
         f"{d.valor_comercial_rd:>12,.0f}",  "RD$"],
 
        ["", "", ""],   # separador visual
 
        [f"Impuesto DGII / Arancel  ({d.descripcion_impuesto})",
         f"+ {d.impuesto_dgii_rd:>11,.0f}",  "RD$"],
 
        ["ITBIS (18%)",
         f"+ {d.itbis_rd:>11,.0f}",          "RD$"],
 
        ["Marbete / Placa / Tramites",
         f"+ {d.placa_rd:>11,.0f}",          "RD$"],
 
        ["Total impuestos y tasas",
         f"{d.total_impuestos_rd:>12,.0f}",  "RD$"],
    ]
 
    # Estilo de la tabla
    estilo = TableStyle([
        # Encabezado
        ("BACKGROUND",   (0, 0), (-1, 0), COLOR_PRIMARIO),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
 
        # Body
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",    (0, 1), (-1, -1), COLOR_TEXTO),
        ("ALIGN",        (1, 1), (1, -1), "RIGHT"),
        ("ALIGN",        (2, 1), (2, -1), "CENTER"),
        ("PADDING",      (0, 0), (-1, -1), 6),
 
        # Filas alternas
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, COLOR_GRIS]),
 
        # Fila separador (vacía)
        ("BACKGROUND",   (0, 6), (-1, 6), colors.white),
        ("LINEBELOW",    (0, 5), (-1, 5), 1, COLOR_SECUNDARIO),
 
        # Fila total impuestos
        ("FONTNAME",     (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",    (0, -1), (-1, -1), COLOR_PRIMARIO),
        ("LINEABOVE",    (0, -1), (-1, -1), 1, COLOR_PRIMARIO),
 
        # Grid
        ("GRID",         (0, 0), (-1, -1), 0.3, COLOR_GRIS_MED),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ])
 
    tabla = Table(
        filas,
        colWidths=["60%", "28%", "12%"],
        style=estilo
    )
 
    nota_dep = Paragraph(
        dep.descripcion,
        estilos["deprec"]
    )
 
    return [
        Paragraph("Desglose del Calculo", estilos["titulo_seccion"]),
        tabla,
        Spacer(1, 4),
        nota_dep,
        Spacer(1, 8),
    ]
 
 
def _seccion_valor_final(estilos, resultado):
    """Caja verde destacada con el valor final."""
    rd_fmt  = f"RD$ {resultado.valor_final_rd:,.0f}"
    usd_fmt = f"Equivalente a USD {resultado.valor_final_usd:,.0f}"
 
    caja = Table(
        [[
            Paragraph("VALOR DE TASACION FINAL", estilos["valor_final_label"]),
        ]],
        colWidths=["100%"],
        style=TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), COLOR_EXITO_BG),
            ("BOX",         (0, 0), (-1, -1), 1.5, COLOR_EXITO),
            ("PADDING",     (0, 0), (-1, -1), 10),
        ])
    )
 
    valor = Table(
        [[Paragraph(rd_fmt, estilos["valor_final"])]],
        colWidths=["100%"],
        style=TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), COLOR_EXITO_BG),
            ("PADDING",     (0, 0), (-1, -1), 6),
        ])
    )
 
    equiv = Table(
        [[Paragraph(usd_fmt, estilos["valor_usd"])]],
        colWidths=["100%"],
        style=TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), COLOR_EXITO_BG),
            ("BOX",         (0, 0), (-1, -1), 1.5, COLOR_EXITO),
            ("PADDING",     (0, 0), (-1, -1), 8),
        ])
    )
 
    return [
        KeepTogether([caja, valor, equiv]),
        Spacer(1, 10),
    ]
 
 
def _seccion_notas(estilos, notas: str):
    """Sección de notas opcionales del tasador."""
    return [
        Paragraph("Observaciones del Tasador", estilos["titulo_seccion"]),
        Paragraph(notas, estilos["normal"]),
        Spacer(1, 6),
    ]
 
 
def _seccion_pie(estilos, resultado, nombre_tasador: str):
    """Pie de página con disclaimer y firma."""
    id_str = f"ID #{resultado.id_tasacion}" if resultado.id_tasacion else ""
    fecha  = resultado.fecha.strftime("%d/%m/%Y")
 
    disclaimer = (
        "Este reporte es una estimacion de valor de mercado basada en datos disponibles al momento "
        "de la tasacion. Los valores pueden variar segun condiciones del mercado, estado fisico del "
        "vehiculo, historial de servicio y otros factores. No constituye una oferta de compra o venta."
    )
 
    pie_tabla = Table(
        [[
            Paragraph(f"Tasador: {nombre_tasador}", estilos["pie"]),
            Paragraph(f"{NOMBRE_EMPRESA} | {VERSION}", estilos["pie"]),
            Paragraph(f"{id_str} | {fecha}", estilos["pie"]),
        ]],
        colWidths=["33%", "34%", "33%"],
        style=TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.5, COLOR_GRIS_MED),
            ("PADDING",   (0, 0), (-1, -1), 4),
        ])
    )
 
    return [
        HRFlowable(width="100%", thickness=0.5, color=COLOR_GRIS_MED, spaceBefore=10),
        Paragraph(disclaimer, estilos["nota"]),
        Spacer(1, 6),
        pie_tabla,
    ]
 
 
# ══════════════════════════════════════════════
# EJECUCIÓN DIRECTA — demo
# ══════════════════════════════════════════════
 
if __name__ == "__main__":
    from motor import MotorTasacion, DatosVehiculo
    from base_datos import inicializar_db
 
    print("Generando reporte de demo...")
 
    motor = MotorTasacion()
    datos = DatosVehiculo(
        marca   = "Toyota",
        modelo  = "Corolla",
        tipo    = "sedan",
        anio    = 2020,
        origen  = "local",
        notas   = "Vehículo en excelentes condiciones. Sin accidentes reportados. Servicio al día."
    )
 
    resultado = motor.tasar(datos)
    motor.cerrar()
 
    if resultado.exitoso:
        ruta = generar_pdf(resultado, nombre_tasador="Admin")
        print(f"\n✅ PDF generado exitosamente:")
        print(f"   {ruta}")
    else:
        print(f"Error: {resultado.mensaje}")
