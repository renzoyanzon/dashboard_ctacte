# Contexto del Proyecto — Dashboard Estado de Cuenta Mutual

## Descripción general

Este proyecto es un **dashboard interactivo en Python** para visualizar y controlar el estado de cuenta de las entidades de una mutual de crédito. La mutual otorga préstamos a empleados públicos de distintas municipalidades. Cada municipalidad descuenta el importe del sueldo de los empleados y paga mensualmente a la mutual de forma agrupada.

El objetivo del dashboard es tener **control exhaustivo en tiempo real** de los movimientos por entidad, detectar faltantes de carga (liquidaciones o cobranzas no registradas) y monitorear el estado deudor/acreedor de cada entidad.

---

## Conceptos del negocio

### Liquidaciones
- La mutual **emite mensualmente** las liquidaciones: son los descuentos que cada municipalidad debería aplicar a sus empleados.
- En la base de datos, las liquidaciones representan el **debe** (lo que la entidad adeuda a la mutual).
- Se identifican por tipo y clase en la tabla `ctactetrabajo`.

### Cobranzas
- Son los **pagos**  que realiza cada municipalidad a la mutual.
- Representan el **haber** (lo que la entidad ya pagó).
- Una entidad puede pagar en abril (fecha real) los descuentos correspondientes a febrero (período de descuento). En ese caso: `cuota = 2`, `anio = año del período`, `fecha = fecha real del pago`.

### Período vs fecha de pago
- `anio` + `cuota` = **período de descuento** (qué mes/año se está descontando del sueldo del empleado).
- `fecha` = **fecha real** en que la entidad realizó el pago o se registró el movimiento.
- Esta distinción es clave: una entidad puede estar al día en pagos pero adeudando períodos anteriores, o viceversa.

### Saldo
- El saldo de una entidad es la diferencia acumulada: `SUM(debe) - SUM(haber)`.
- Saldo positivo = la entidad debe dinero a la mutual (saldo acreedor)
- Saldo negativo = la mutual tiene saldo a favor de la entidad (saldo deudor).

### Gastos de procesamiento y diferencia liquidado/cobrado
- La diferencia entre lo liquidado y lo cobrado representa implícitamente los gastos de procesamiento, que **no se registran como movimiento separado** en la tabla.
- Esta diferencia es esperada y razonable dentro de un umbral.
- Si el porcentaje de diferencia supera el umbral configurado, indica que algo está mal: puede ser un error de carga, un pago parcial no registrado, o un descuento que no se aplicó correctamente.
- El dashboard debe mostrar este % por período y resaltar visualmente cuando supera el umbral.

---

## Problema principal a resolver

Frecuentemente el responsable administrativo **olvida cargar** alguna liquidación o cobranza. Esto genera inconsistencias en los saldos y dificulta el control. El dashboard debe:

1. Detectar automáticamente períodos sin liquidación para una entidad activa.
2. Detectar períodos con liquidación pero sin cobranza (deuda pendiente).
3. Mostrar en qué estado está cada entidad de forma visual e inmediata.
4. Permitir filtrar y explorar los datos por entidad, período, tipo de movimiento, etc.

---

## Stack tecnológico recomendado

- **Python 3.10+**
- **Dash + Plotly** para el dashboard interactivo (componentes reactivos sin necesidad de JavaScript manual)
- **mysql-connector-python** para la conexión a MySQL (import mysql.connector)
- **Pandas** para la transformación y análisis de datos
- **Dash Bootstrap Components (DBC)** para el layout visual
- Base de datos: **MySQL**

---

## Estructura de archivos del proyecto

```
dashboard_mutual/
├── app.py                  # Punto de entrada, instancia Dash, menú lateral
├── config.py               # Variables de entorno, constantes de negocio
├── db/
│   ├── connection.py       # Pool de conexiones mysql.connector
│   └── queries.py          # Todas las consultas SQL parametrizadas
├── data/
│   └── transformations.py  # Lógica de negocio sobre DataFrames
├── components/
│   ├── filters.py          # Componentes de filtros globales
│   ├── kpis.py             # Tarjetas KPI
│   ├── charts.py           # Todos los gráficos Plotly
│   └── table.py            # Grilla de detalle y cuadro pivote
├── pages/
│   ├── inicio.py           # Resumen general + gráficos globales + ranking
│   ├── entidad.py          # Detalle por entidad (pestañas internas)
│   └── control.py          # Control de carga — heatmap de faltantes
├── assets/
│   └── style.css           # Estilos personalizados
└── requirements.txt
```

## Navegación — menú lateral

El dashboard usa `dash.page_registry` con un sidebar fijo a la izquierda:

- **Inicio** → `pages/inicio.py` — visión global de todas las entidades
- **Por entidad** → `pages/entidad.py` — seleccionás una entidad y ves su detalle completo
- **Control de carga** → `pages/control.py` — heatmap de faltantes y alertas
