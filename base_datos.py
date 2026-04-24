"""
base_datos.py
=============
Capa de datos del Tasador RD — MVP v1
Motor: SQLite (archivo local)
ORM:   SQLAlchemy (migración a PostgreSQL en v2 = cambiar solo DATABASE_URL)

Tablas:
  - marcas        → Toyota, Honda, Hyundai ...
  - modelos       → Corolla, Civic, Tucson ...
  - vehiculos     → catálogo con precio base USD
  - tasaciones    → historial de cada tasación realizada
"""

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

class Base(DeclarativeBase):
    pass
from datetime import datetime
import os

# ─────────────────────────────────────────────
# CONFIGURACIÓN — v2: PostgreSQL en Railway
# Lee desde variable de entorno DATABASE_URL
# Si no existe, usa SQLite local como fallback
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_DB_ENV = os.environ.get("DATABASE_URL", "")

# Railway a veces entrega "postgres://" — SQLAlchemy necesita "postgresql://"
if _DB_ENV.startswith("postgres://"):
    _DB_ENV = _DB_ENV.replace("postgres://", "postgresql://", 1)

DATABASE_URL = _DB_ENV if _DB_ENV else f"sqlite:///{os.path.join(BASE_DIR, 'datos', 'vehiculos.db')}"



# ══════════════════════════════════════════════
# MODELOS / TABLAS
# ══════════════════════════════════════════════

class Marca(Base):
    """Toyota, Honda, Hyundai, Kia, etc."""
    __tablename__ = "marcas"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    nombre    = Column(String(100), nullable=False, unique=True)
    pais      = Column(String(50))                        # Japón, Corea, Alemania...
    segmento  = Column(String(50))                        # economico, medio, lujo

    modelos   = relationship("Modelo", back_populates="marca", cascade="all, delete")

    def __repr__(self):
        return f"<Marca {self.nombre}>"


class Modelo(Base):
    """Corolla, Civic, Tucson, RAV4, etc."""
    __tablename__ = "modelos"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    marca_id    = Column(Integer, ForeignKey("marcas.id"), nullable=False)
    nombre      = Column(String(100), nullable=False)
    tipo        = Column(String(50), nullable=False)      # sedan, suv, pickup, lujo, comercial
    traccion    = Column(String(20), default="2WD")       # 2WD, 4WD, AWD

    marca       = relationship("Marca", back_populates="modelos")
    vehiculos   = relationship("Vehiculo", back_populates="modelo", cascade="all, delete")

    def __repr__(self):
        return f"<Modelo {self.marca.nombre} {self.nombre}>"


class Vehiculo(Base):
    """
    Catálogo de vehículos con precio base.
    El precio_base_usd es el valor de referencia nuevo (o precio mercado USA).
    La depreciación se aplica en el motor según el año.
    """
    __tablename__ = "vehiculos"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    modelo_id       = Column(Integer, ForeignKey("modelos.id"), nullable=False)
    anio            = Column(Integer, nullable=False)
    precio_base_usd = Column(Float, nullable=False)       # precio referencia USD
    precio_rd       = Column(Float, nullable=True)        # precio mercado RD$ (scraper)
    fuente          = Column(String(100), default="manual") # manual, supercarros, kbb
    fecha_precio    = Column(DateTime, default=datetime.utcnow)
    notas           = Column(Text, nullable=True)

    modelo          = relationship("Modelo", back_populates="vehiculos")

    def __repr__(self):
        return f"<Vehiculo {self.modelo.marca.nombre} {self.modelo.nombre} {self.anio}>"


class Tasacion(Base):
    """
    Historial de cada tasación realizada.
    Se guarda todo para auditoría y para entrenar el modelo experto.
    """
    __tablename__ = "tasaciones"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    fecha               = Column(DateTime, default=datetime.utcnow)

    # Datos del vehículo tasado
    marca               = Column(String(100), nullable=False)
    modelo              = Column(String(100), nullable=False)
    tipo                = Column(String(50), nullable=False)
    anio                = Column(Integer, nullable=False)

    # Valores calculados
    precio_base_usd     = Column(Float)
    factor_depreciacion = Column(Float)           # ej: 0.72 = 72% del valor original
    valor_comercial_usd = Column(Float)
    tasa_cambio         = Column(Float)           # RD$ por USD al momento
    impuestos_rd        = Column(Float)
    valor_final_rd      = Column(Float)

    # Metadata
    tasador             = Column(String(100), default="sistema")
    notas               = Column(Text, nullable=True)
    pdf_path            = Column(String(255), nullable=True)  # ruta del reporte generado

    def __repr__(self):
        return f"<Tasacion {self.marca} {self.modelo} {self.anio} — RD${self.valor_final_rd:,.0f}>"


# ══════════════════════════════════════════════
# ENGINE & SESSION
# ══════════════════════════════════════════════

def crear_engine():
    """Crea el engine. En SQLite crea el archivo si no existe."""
    os.makedirs(os.path.join(BASE_DIR, "datos"), exist_ok=True)
    engine = create_engine(DATABASE_URL, echo=False)
    return engine


def inicializar_db():
    """Crea todas las tablas. Detecta y repara DB corrupta automaticamente."""
    db_path = os.path.join(BASE_DIR, "datos", "vehiculos.db")

    if os.path.exists(db_path):
        try:
            import sqlite3
            con = sqlite3.connect(db_path)
            con.execute("PRAGMA integrity_check")
            con.close()
        except Exception:
            print("Base de datos corrupta detectada. Recreando...")
            os.remove(db_path)

    engine = crear_engine()
    Base.metadata.create_all(engine)

    session = get_session(engine)
    cargar_datos_semilla(session)
    session.close()

    print("Base de datos inicializada correctamente.")
    return engine


def get_session(engine=None):
    """Retorna una sesión activa para hacer queries."""
    if engine is None:
        engine = crear_engine()
    Session = sessionmaker(bind=engine)
    return Session()


# ══════════════════════════════════════════════
# DATOS SEMILLA — marcas y modelos populares RD
# ══════════════════════════════════════════════

DATOS_SEMILLA = {
    "Toyota": {
        "pais": "Japón", "segmento": "medio",
        "modelos": [
            {"nombre": "Corolla",    "tipo": "sedan",    "traccion": "2WD"},
            {"nombre": "Camry",      "tipo": "sedan",    "traccion": "2WD"},
            {"nombre": "RAV4",       "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "Hilux",      "tipo": "pickup",   "traccion": "4WD"},
            {"nombre": "Land Cruiser","tipo": "suv",     "traccion": "4WD"},
            {"nombre": "Yaris",      "tipo": "sedan",    "traccion": "2WD"},
        ]
    },
    "Honda": {
        "pais": "Japón", "segmento": "medio",
        "modelos": [
            {"nombre": "Civic",      "tipo": "sedan",    "traccion": "2WD"},
            {"nombre": "Accord",     "tipo": "sedan",    "traccion": "2WD"},
            {"nombre": "CR-V",       "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "HR-V",       "tipo": "suv",      "traccion": "2WD"},
            {"nombre": "Pilot",      "tipo": "suv",      "traccion": "AWD"},
        ]
    },
    "Hyundai": {
        "pais": "Corea", "segmento": "medio",
        "modelos": [
            {"nombre": "Tucson",     "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "Santa Fe",   "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "Elantra",    "tipo": "sedan",    "traccion": "2WD"},
            {"nombre": "Accent",     "tipo": "sedan",    "traccion": "2WD"},
        ]
    },
    "Kia": {
        "pais": "Corea", "segmento": "medio",
        "modelos": [
            {"nombre": "Sportage",   "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "Sorento",    "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "Rio",        "tipo": "sedan",    "traccion": "2WD"},
            {"nombre": "Carnival",   "tipo": "comercial","traccion": "2WD"},
        ]
    },
    "Nissan": {
        "pais": "Japón", "segmento": "medio",
        "modelos": [
            {"nombre": "Frontier",   "tipo": "pickup",   "traccion": "4WD"},
            {"nombre": "X-Trail",    "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "Sentra",     "tipo": "sedan",    "traccion": "2WD"},
            {"nombre": "Pathfinder", "tipo": "suv",      "traccion": "AWD"},
        ]
    },
    "Mitsubishi": {
        "pais": "Japón", "segmento": "medio",
        "modelos": [
            {"nombre": "Outlander",  "tipo": "suv",      "traccion": "AWD"},
            {"nombre": "L200",       "tipo": "pickup",   "traccion": "4WD"},
            {"nombre": "ASX",        "tipo": "suv",      "traccion": "2WD"},
        ]
    },
    "BMW": {
        "pais": "Alemania", "segmento": "lujo",
        "modelos": [
            {"nombre": "Serie 3",    "tipo": "lujo",     "traccion": "AWD"},
            {"nombre": "Serie 5",    "tipo": "lujo",     "traccion": "AWD"},
            {"nombre": "X5",         "tipo": "lujo",     "traccion": "AWD"},
        ]
    },
    "Mercedes-Benz": {
        "pais": "Alemania", "segmento": "lujo",
        "modelos": [
            {"nombre": "Clase C",    "tipo": "lujo",     "traccion": "AWD"},
            {"nombre": "Clase E",    "tipo": "lujo",     "traccion": "AWD"},
            {"nombre": "GLE",        "tipo": "lujo",     "traccion": "AWD"},
        ]
    },
}


def cargar_datos_semilla(session):
    """
    Carga marcas y modelos iniciales si la DB está vacía.
    Seguro de llamar múltiples veces — no duplica datos.
    """
    if session.query(Marca).count() > 0:
        print("ℹ️  Datos semilla ya cargados — saltando.")
        return

    for nombre_marca, datos in DATOS_SEMILLA.items():
        marca = Marca(
            nombre   = nombre_marca,
            pais     = datos["pais"],
            segmento = datos["segmento"]
        )
        session.add(marca)
        session.flush()  # para obtener marca.id antes del commit

        for m in datos["modelos"]:
            modelo = Modelo(
                marca_id = marca.id,
                nombre   = m["nombre"],
                tipo     = m["tipo"],
                traccion = m["traccion"]
            )
            session.add(modelo)

    session.commit()
    total_marcas  = session.query(Marca).count()
    total_modelos = session.query(Modelo).count()
    print(f"✅ Semilla cargada: {total_marcas} marcas, {total_modelos} modelos.")


# ══════════════════════════════════════════════
# HELPERS DE CONSULTA
# ══════════════════════════════════════════════

def buscar_vehiculo(session, marca: str, modelo: str, anio: int):
    """
    Busca un vehículo en el catálogo.
    Retorna el objeto Vehiculo o None si no existe.
    """
    return (
        session.query(Vehiculo)
        .join(Modelo)
        .join(Marca)
        .filter(
            Marca.nombre.ilike(f"%{marca}%"),
            Modelo.nombre.ilike(f"%{modelo}%"),
            Vehiculo.anio == anio
        )
        .first()
    )


def listar_marcas(session):
    """Retorna lista de nombres de marcas disponibles."""
    return [m.nombre for m in session.query(Marca).order_by(Marca.nombre).all()]


def listar_modelos(session, marca: str):
    """Retorna lista de modelos para una marca dada."""
    return (
        session.query(Modelo)
        .join(Marca)
        .filter(Marca.nombre.ilike(f"%{marca}%"))
        .all()
    )


def guardar_tasacion(session, datos: dict) -> Tasacion:
    """
    Guarda una tasación en el historial.
    datos = dict con los campos de la tabla Tasacion.
    """
    t = Tasacion(**datos)
    session.add(t)
    session.commit()
    return t


# ══════════════════════════════════════════════
# EJECUCIÓN DIRECTA — setup inicial
# ══════════════════════════════════════════════

if __name__ == "__main__":
    engine  = inicializar_db()
    session = get_session(engine)
    cargar_datos_semilla(session)
    session.close()

    print("\n📋 Marcas disponibles:")
    session = get_session(engine)
    for marca in listar_marcas(session):
        print(f"   • {marca}")
    session.close()