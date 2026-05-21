"""
app.py
======
Interfaz Web — Tasador RD MVP v1
Framework: Streamlit

Correr con:
    streamlit run app.py

Requiere:
    pip install streamlit sqlalchemy reportlab
"""

import streamlit as st
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor import MotorTasacion, DatosVehiculo
from base_datos import inicializar_db, get_session, listar_marcas, listar_modelos
from reporte import generar_pdf


# ══════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════

st.set_page_config(
    page_title="TasaloTu - Tasación de Vehículos en República Dominicana",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════
# ESTILOS CUSTOM
# ══════════════════════════════════════════════

st.markdown("""
<style>
    /* Fondo general */
    .stApp { background-color: #f8f9fa; }

    /* Encabezado hero */
    .hero {
        background: linear-gradient(135deg, #1a3a5c 0%, #2e86c1 100%);
        border-radius: 16px;
        padding: 2rem 2rem 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
        color: white;
    }
    .hero h1 { font-size: 2.2rem; margin: 0; font-weight: 700; }
    .hero p  { font-size: 1rem; margin: 0.4rem 0 0; opacity: 0.85; }

    /* Tarjeta resultado */
    .resultado-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #e0e0e0;
        margin-top: 1rem;
    }

    /* Valor final grande */
    .valor-final {
        background: #eafaf1;
        border: 2px solid #1e8449;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .valor-final .label {
        font-size: 0.85rem;
        color: #1e8449;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .valor-final .monto {
        font-size: 2.6rem;
        font-weight: 700;
        color: #1e8449;
        margin: 0.2rem 0;
    }
    .valor-final .equiv {
        font-size: 0.95rem;
        color: #27ae60;
    }

    /* Fila de desglose */
    .fila-desglose {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid #f0f0f0;
        font-size: 0.95rem;
    }
    .fila-desglose:last-child { border-bottom: none; }
    .fila-label { color: #566573; }
    .fila-valor { font-weight: 600; color: #2c3e50; }
    .fila-valor.deduccion { color: #e74c3c; }
    .fila-valor.suma      { color: #27ae60; }
    .fila-total {
        font-size: 1rem;
        font-weight: 700;
        color: #1a3a5c;
        border-top: 2px solid #1a3a5c !important;
        padding-top: 0.7rem !important;
        margin-top: 0.3rem;
    }

    /* Badge de fuente */
    .badge {
        display: inline-block;
        font-size: 0.72rem;
        padding: 2px 8px;
        border-radius: 99px;
        font-weight: 600;
    }
    .badge-db      { background: #e8f4fd; color: #1a5276; }
    .badge-est     { background: #fef9e7; color: #7d6608; }
    .badge-scraper { background: #eafaf1; color: #1e8449; }

    /* Sección título */
    .sec-titulo {
        font-size: 0.78rem;
        font-weight: 700;
        color: #1a3a5c;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin: 1.2rem 0 0.5rem;
        padding-bottom: 4px;
        border-bottom: 2px solid #2e86c1;
    }

    /* Botón tasar */
    div[data-testid="stButton"] > button {
        background: #1a3a5c;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.7rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        transition: background 0.2s;
    }
    div[data-testid="stButton"] > button:hover {
        background: #2e86c1;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# INICIALIZACIÓN (cache para no repetir)
# ══════════════════════════════════════════════

@st.cache_resource
def init_db():
    engine  = inicializar_db()
    session = get_session(engine)
    from data_vehiculos import cargar_vehiculos_ampliados
    cargar_vehiculos_ampliados(session)
    return engine, session

@st.cache_resource
def init_motor():
    return MotorTasacion()


engine, session = init_db()
motor           = init_motor()


# ══════════════════════════════════════════════
# HERO HEADER
# ══════════════════════════════════════════════

st.markdown("""
<div class="hero">
    <h1>🚗 Tasador RD</h1>
    <p>Servicio Profesional de Tasación de Vehículos · República Dominicana</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# FORMULARIO
# ══════════════════════════════════════════════

with st.container():

    col1, col2 = st.columns(2)

    with col1:
        marcas         = listar_marcas(session)
        marca_sel      = st.selectbox("Marca", marcas, index=0)

    with col2:
        modelos_obj    = listar_modelos(session, marca_sel)
        nombres_modelos = [m.nombre for m in modelos_obj]
        if nombres_modelos:
            modelo_sel = st.selectbox("Modelo", nombres_modelos)
            tipo_auto  = next(
                (m.tipo for m in modelos_obj if m.nombre == modelo_sel),
                "sedan"
            )
        else:
            modelo_sel = st.text_input("Modelo", placeholder="Ej: Corolla")
            tipo_auto  = "sedan"

    col3, col4 = st.columns(2)

    with col3:
        anio_actual = datetime.now().year
        anio_sel    = st.selectbox(
            "Año",
            list(range(anio_actual, 1989, -1)),
            index=4
        )

    with col4:
        origen_opciones = {
            "Local (placa RD)":   "local",
            "Importado nuevo":    "importado_nuevo",
            "Importado usado":    "importado_usado",
        }
        origen_label = st.selectbox("Origen", list(origen_opciones.keys()))
        origen_sel   = origen_opciones[origen_label]

    # Tasa de cambio
    with st.expander("⚙ Configuración avanzada"):
        tasa = st.number_input(
            "Tasa de cambio RD$/USD",
            min_value=50.0, max_value=80.0,
            value=59.5, step=0.5,
            help="Actualiza según la tasa del Banco Central RD"
        )
        notas = st.text_area(
            "Notas adicionales (opcional)",
            placeholder="Ej: Vehículo en excelentes condiciones, sin accidentes...",
            height=80
        )

    st.markdown("<br>", unsafe_allow_html=True)
    tasar_btn = st.button("Calcular Tasación")


# ══════════════════════════════════════════════
# RESULTADO
# ══════════════════════════════════════════════

if tasar_btn:
    if not modelo_sel:
        st.error("Por favor selecciona o ingresa un modelo.")
    else:
        with st.spinner("Calculando tasación..."):
            motor.tasa_cambio = tasa
            datos = DatosVehiculo(
                marca   = marca_sel,
                modelo  = modelo_sel,
                tipo    = tipo_auto,
                anio    = anio_sel,
                origen  = origen_sel,
                notas   = notas if notas else ""
            )
            resultado = motor.tasar(datos)

        if not resultado.exitoso:
            st.error(f"Error en la tasación: {resultado.mensaje}")
        else:
            d   = resultado.desglose
            dep = d.depreciacion

            # ── VALOR FINAL ──────────────────────
            st.markdown(f"""
            <div class="valor-final">
                <div class="label">Valor de Tasación Final</div>
                <div class="monto">RD$ {resultado.valor_final_rd:,.0f}</div>
                <div class="equiv">≈ USD {resultado.valor_final_usd:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

            # ── DATOS DEL VEHÍCULO ───────────────
            st.markdown('<div class="sec-titulo">Vehículo Tasado</div>', unsafe_allow_html=True)

            badge_map = {
                "db_local":  ('<span class="badge badge-db">Base de datos</span>', ""),
                "estimado":  ('<span class="badge badge-est">Estimado</span>', ""),
                "scraper":   ('<span class="badge badge-scraper">Supercarros</span>', ""),
            }
            badge_html, _ = badge_map.get(d.fuente_precio, ("", ""))

            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Marca",       marca_sel)
            v2.metric("Modelo",      modelo_sel)
            v3.metric("Año",         str(anio_sel))
            v4.metric("Años de uso", str(dep.anios_uso))

            # ── DESGLOSE ─────────────────────────
            st.markdown('<div class="sec-titulo">Desglose del Cálculo</div>', unsafe_allow_html=True)

            pct_perdida   = round((1 - dep.factor_final) * 100, 1)
            pct_retencion = round(dep.factor_final * 100, 1)

            filas = [
                ("Precio base de referencia",
                 f"USD {d.precio_base_usd:,.0f}",    "normal"),
                (f"Depreciación acumulada ({pct_perdida}% en {dep.anios_uso} años)",
                 f"- USD {d.precio_base_usd * (1 - dep.factor_final):,.0f}", "deduccion"),
                (f"Factor de retención ({pct_retencion}%)",
                 f"{dep.factor_final:.4f}",           "normal"),
                ("Valor comercial (USD)",
                 f"USD {d.valor_comercial_usd:,.0f}", "normal"),
                (f"Conversión a RD$ (tasa {d.tasa_cambio})",
                 f"RD$ {d.valor_comercial_rd:,.0f}",  "normal"),
                ("─" * 30, "", "sep"),
                ("Impuesto DGII / Arancel",
                 f"+ RD$ {d.impuesto_dgii_rd:,.0f}",  "suma"),
                ("ITBIS (18%)",
                 f"+ RD$ {d.itbis_rd:,.0f}",          "suma"),
                ("Marbete / Placa / Trámites",
                 f"+ RD$ {d.placa_rd:,.0f}",          "suma"),
                ("Total impuestos",
                 f"RD$ {d.total_impuestos_rd:,.0f}",  "normal"),
                ("VALOR FINAL",
                 f"RD$ {resultado.valor_final_rd:,.0f}", "total"),
            ]

            for label, valor, estilo in filas:
                if estilo == "sep":
                    st.markdown("---")
                    continue
                extra_label = "fila-total" if estilo == "total" else ""
                extra_valor = f"fila-{estilo}" if estilo in ("deduccion","suma","total") else "fila-valor"
                st.markdown(f"""
                <div class="fila-desglose {extra_label}">
                    <span class="fila-label">{label}</span>
                    <span class="{extra_valor}">{valor}</span>
                </div>
                """, unsafe_allow_html=True)

            # ── DEPRECIACIÓN INFO ────────────────
            st.markdown('<div class="sec-titulo">Análisis de Depreciación</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Factor retención",  f"{pct_retencion}%")
            c2.metric("Depreciación total", f"{pct_perdida}%")
            c3.metric("Tasa efectiva/año",
                      f"{round(dep.tasa_anual_efectiva * 100, 1)}%")

            st.info(dep.descripcion)

            # ── PDF ──────────────────────────────
            #st.markdown('<div class="sec-titulo">Reporte</div>', unsafe_allow_html=True)

            #if st.button("📄 Generar y Descargar PDF"):
            #    with st.spinner("Generando PDF..."):
             #       ruta_pdf = generar_pdf(resultado)

              #  with open(ruta_pdf, "rb") as f:
               #     pdf_bytes = f.read()

                #nombre_archivo = (
                 #   f"tasacion_{marca_sel}_{modelo_sel}_{anio_sel}.pdf"
                  #  .replace(" ", "_")
                #)

                #st.download_button(
                 #   label      = "⬇ Descargar PDF",
                  #  data       = pdf_bytes,
                   # file_name  = nombre_archivo,
                    #mime       = "application/pdf",
                #)
                #st.success(f"PDF generado: {ruta_pdf}")


# ══════════════════════════════════════════════
# SIDEBAR — HISTORIAL
# ══════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 📋 Historial")

    from base_datos import Tasacion
    tasaciones = (
        session.query(Tasacion)
        .order_by(Tasacion.fecha.desc())
        .limit(10)
        .all()
    )

    if not tasaciones:
        st.info("Aún no hay tasaciones registradas.")
    else:
        for t in tasaciones:
            fecha = t.fecha.strftime("%d/%m/%Y") if t.fecha else "—"
            valor = f"RD$ {t.valor_final_rd:,.0f}" if t.valor_final_rd else "—"
            st.markdown(f"""
            **{t.marca} {t.modelo} {t.anio}**
            {fecha} · {valor}
            ---
            """)

    st.markdown("---")
    st.markdown(
        "<small>Tasador RD v1.0 · República Dominicana</small>",
        unsafe_allow_html=True
    )
