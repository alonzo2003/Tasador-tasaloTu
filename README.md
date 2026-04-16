# Tasador de Vehículos RD — MVP v1

Sistema profesional de tasación de vehículos para República Dominicana.

---

## Instalación

```bash
# 1. Clonar / copiar el proyecto
cd tasador_rd

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Inicializar la base de datos (solo la primera vez)
python base_datos.py
```

---

## Uso

### Modo interactivo (recomendado)
```bash
python main.py
```
Te guía paso a paso: marca → modelo → año → origen → resultado → PDF.

### Modo directo (una línea)
```bash
python main.py --marca Toyota --modelo Corolla --tipo sedan --anio 2020
python main.py --marca BMW --modelo "Serie 3" --tipo lujo --anio 2021 --origen importado_usado
```

### Ver historial de tasaciones
```bash
python main.py --historial
```

### Ver marcas disponibles
```bash
python main.py --marcas
```

### Generar PDF directo
```bash
python main.py --marca Toyota --modelo Corolla --tipo sedan --anio 2020 --pdf
```

---

## Estructura del proyecto

```
tasador_rd/
├── main.py              ← Interfaz principal (ejecutar este)
├── motor.py             ← Lógica de tasación
├── depreciacion.py      ← Tablas de depreciación
├── base_datos.py        ← Base de datos SQLite
├── reporte.py           ← Generador de PDF
├── requirements.txt     ← Dependencias
├── datos/
│   └── vehiculos.db     ← Base de datos (se crea automáticamente)
└── reportes/            ← PDFs generados (se crea automáticamente)
```

---

## Tipos de vehículo válidos
`sedan` · `suv` · `pickup` · `lujo` · `comercial` · `hatchback` · `minivan`

## Orígenes válidos
`local` · `importado_nuevo` · `importado_usado`

---

## Roadmap

| Versión | Funcionalidad |
|---------|--------------|
| v1 (MVP) | Tipo + año + marca + modelo → PDF |
| v2 | Millaje + estado + accidentes + scraper Supercarros |
| v3 | Conocimiento experto + interfaz web + multi-usuario |

---

## Migración a PostgreSQL (v2)

Solo cambiar una línea en `base_datos.py`:

```python
# Antes (SQLite)
DATABASE_URL = "sqlite:///datos/vehiculos.db"

# Después (PostgreSQL)
DATABASE_URL = "postgresql://usuario:password@host/tasador_db"
```

Todo lo demás del código queda igual. ✅