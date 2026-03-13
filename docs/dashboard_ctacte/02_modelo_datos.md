# Modelo de Datos — ctactetrabajo

## Tabla principal: `ctactetrabajo`

Esta es la tabla central del sistema. Cada fila representa un **movimiento** en el estado de cuenta de una entidad (municipalidad u organismo).

### Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT PK | Identificador único del registro |
| `idtrabajo` | INT/VARCHAR | Identificador de la entidad (municipalidad/organismo). Se une con tabla `trabajo` para obtener el nombre |
| `operacion` | VARCHAR | Código o descripción de la operación |
| `fecha` | DATE | Fecha real del registro/pago |
| `cuota` | INT | Número de mes del período de descuento (1=enero, 2=febrero, ..., 12=diciembre) |
| `anio` | INT | Año del período de descuento |
| `tipo` | VARCHAR/INT | Clasificación principal del movimiento (ver tabla de tipos) |
| `clase` | VARCHAR/INT | Subclasificación del movimiento |
| `saldo` | DECIMAL | Saldo acumulado hasta ese registro |
| `debe` | DECIMAL | Monto que la entidad adeuda (liquidaciones, gastos) |
| `haber` | DECIMAL | Monto que la entidad pagó (cobranzas, devoluciones) |
| `detalle` | VARCHAR | Descripción textual del movimiento |
| `envio` | INT/VARCHAR | Identificador del envío/remesa. Junto con `idtrabajo` identifica unívocamente cada combinación entidad/tipo/clase |
| `usuario` | VARCHAR | Usuario que registró el movimiento |

### Clave de negocio compuesta

La combinación `idtrabajo + envio` identifica cada grupo de movimientos relacionados a una entidad en un envío particular.

### Identificación del período

- `cuota` = mes del período de descuento (no necesariamente el mes de pago)
- `anio` = año del período de descuento
- `fecha` = fecha real del pago o registro

**Ejemplo:** Una municipalidad paga en abril de 2026 los descuentos de febrero de 2026:
- `fecha = 2026-04-15` (cuando pagó)
- `cuota = 2` (febrero)
- `anio = 2026` (año del período)

---

## Tabla secundaria: `trabajo`

Proporciona el nombre/descripción de cada entidad a partir de `idtrabajo`.

| Campo | Descripción |
|-------|-------------|
| `idtrabajo` | FK con ctactetrabajo.idtrabajo |
| `nombre` o campo equivalente | Nombre de la municipalidad/organismo |

**Uso:** JOIN con `ctactetrabajo` para mostrar nombres legibles en el dashboard.

---

## Combinaciones tipo/clase

La diferenciación entre movimientos se realiza mediante `tipo` y `clase`. Esta es la tabla completa de valores reales del sistema:

| tipo | clase | Grupo | Subgrupo | Forma de pago | Lado contable |
|------|-------|-------|----------|---------------|---------------|
| IM | CS | Liquidacion | Cuota Social | | debe |
| IM | GC | Liquidacion | Comisiones | | debe |
| IM | GP | Liquidacion | Procesamiento | | debe |
| IM | GV | Liquidacion | Varios | | debe |
| IM | M | Liquidacion | Mutuos | | debe |
| IM | RG | Liquidacion | Recupero de gastos | | debe |
| IM | SF | Liquidacion | Fallecimiento | | debe |
| IM | SS | Liquidacion | Sepelio | | debe |
| IM | TR | Liquidacion | Cobro de terceros | | debe |
| MI | CS | Liquidacion | Cuota Social | | debe |
| MI | DV | Liquidacion | Devoluciones | | debe |
| MI | GC | Liquidacion | Comisiones | | debe |
| MI | GP | Liquidacion | Procesamiento | | debe |
| MI | M | Liquidacion | Mutuos | | debe |
| MI | RG | Liquidacion | Recupero de gastos | | debe |
| MI | SF | Liquidacion | Fallecimiento | | debe |
| MI | SS | Liquidacion | Sepelio | | debe |
| MI | TR | Liquidacion | Cobro de terceros | | debe |
| IS | M | Liquidacion | Mutuos | | debe |
| IS | SF | Liquidacion | Fallecimiento | | debe |
| IS | SS | Liquidacion | Sepelio | | debe |
| IS | DI | Liquidacion | Falta imputacion | | debe |
| CP | CP | Liquidacion | Cierre periodo | | debe |
| CP | SI | Liquidacion | Saldo inicial | | debe |
| IT | C | Ingresos | | Transferencia | haber |
| IA | C | Ingresos | | FDC | haber |
| IC | C | Ingresos | | Cheque | haber |
| IE | C | Ingresos | | Efectivo | haber |
| ET | CO | Egresos | Comisiones | Transferencia | haber |
| ET | CS | Egresos | Cuota Social | Transferencia | haber |
| ET | DV | Egresos | Devoluciones | Transferencia | haber |
| EC | DV | Egresos | Devoluciones | Cheque | haber |
| EE | CO | Egresos | Comisiones | Efectivo | haber |
| EE | DV | Egresos | Devoluciones | Efectivo | haber |
| AN | CS | Ajuste | Cuota Social | | debe/haber* |
| AN | M | Ajuste | Mutuos | | debe/haber* |
| AN | RG | Ajuste | Recupero de gastos | | debe/haber* |
| AN | SS | Ajuste | Sepelio | | debe/haber* |
| AN | TR | Ajuste | Cobro de terceros | | debe/haber* |
| AP | M | Ajuste | Mutuos | | debe/haber* |

> *Los ajustes (AN, AP) pueden impactar en debe o haber según el signo del monto. Verificar con el campo efectivamente cargado.

### Agrupamiento lógico para el dashboard

Para simplificar filtros y visualizaciones, agrupar así:

**Liquidaciones** (lo que la entidad debe): tipos `IM`, `MI`, `IS`, `CP`

**Ingresos / Cobranzas** (pagos recibidos): tipos `IT`, `IA`, `IC`, `IE`

**Egresos** (devoluciones y comisiones pagadas): tipos `ET`, `EC`, `EE`
	Nota: las devoluciones se deben mostrar separado de las comisiones

**Ajustes** (correcciones manuales): tipos `AN`, `AP`

### Subgrupos relevantes para filtros

- **Mutuos** (préstamos): clase `M` — el concepto principal del negocio
- **Cuota Social**: clase `CS`
- **Sepelio**: clase `SS`
- **Fallecimiento**: clase `SF`
- **Comisiones**: clase `GC`, `CO`
- **Procesamiento**: clase `GP`
- **Devoluciones**: clase `DV`
- **Cobro de terceros**: clase `TR`
- **Recupero de gastos**: clase `RG`

### Detección de faltantes — lógica correcta

Para detectar períodos con liquidación pero sin cobranza, comparar:

- **Liquidaciones emitidas:** registros con tipo IN (`IM`, `MI`, `IS`) agrupados por `idtrabajo + anio + cuota`
- **Cobranzas recibidas:** registros con tipo IN (`IT`, `IA`, `IC`, `IE`) agrupados por `idtrabajo + anio + cuota`

Los registros `CP` (cierre de período y saldo inicial) son asientos contables internos, **no** deben incluirse en la comparación de faltantes.

Los registros `AN` y `AP` (ajustes) tampoco se consideran liquidaciones ni cobranzas para este fin.

---

## Consultas base recomendadas

### Estado de cuenta por entidad
```sql
SELECT 
    t.nombre AS entidad,
    c.idtrabajo,
    c.anio,
    c.cuota,
    c.tipo,
    c.clase,
    SUM(c.debe) AS total_debe,
    SUM(c.haber) AS total_haber,
    SUM(c.debe) - SUM(c.haber) AS saldo_neto
FROM ctactetrabajo c
JOIN trabajo t ON c.idtrabajo = t.idtrabajo
GROUP BY t.nombre, c.idtrabajo, c.anio, c.cuota, c.tipo, c.clase
ORDER BY c.anio DESC, c.cuota DESC
```

### Saldo actual por entidad
```sql
SELECT 
    t.nombre AS entidad,
    c.idtrabajo,
    SUM(c.debe) AS total_debe,
    SUM(c.haber) AS total_haber,
    SUM(c.debe) - SUM(c.haber) AS saldo_actual
FROM ctactetrabajo c
JOIN trabajo t ON c.idtrabajo = t.idtrabajo
GROUP BY t.nombre, c.idtrabajo
ORDER BY saldo_actual DESC
```

### Períodos con liquidación pero sin cobranza (deuda pendiente)
```sql
WITH liquidaciones AS (
    SELECT idtrabajo, anio, cuota
    FROM ctactetrabajo
    WHERE tipo = :tipo_liquidacion AND clase = :clase_liquidacion
    GROUP BY idtrabajo, anio, cuota
),
cobranzas AS (
    SELECT idtrabajo, anio, cuota
    FROM ctactetrabajo
    WHERE tipo = :tipo_cobranza AND clase = :clase_cobranza
    GROUP BY idtrabajo, anio, cuota
)
SELECT l.idtrabajo, l.anio, l.cuota
FROM liquidaciones l
LEFT JOIN cobranzas c 
    ON l.idtrabajo = c.idtrabajo 
    AND l.anio = c.anio 
    AND l.cuota = c.cuota
WHERE c.idtrabajo IS NULL
```

### Detalle completo por entidad (con filtros)
```sql
SELECT 
    c.*,
    t.nombre AS nombre_entidad
FROM ctactetrabajo c
JOIN trabajo t ON c.idtrabajo = t.idtrabajo
WHERE c.idtrabajo = :idtrabajo
  AND (:anio IS NULL OR c.anio = :anio)
  AND (:cuota IS NULL OR c.cuota = :cuota)
ORDER BY c.fecha DESC, c.id DESC
```

---

## Notas de implementación

- Todas las consultas deben ser **parametrizadas** (nunca concatenar strings con valores de usuario).
- Usar `pandas.read_sql()` con el engine de SQLAlchemy para obtener DataFrames directamente.
- El campo `saldo` en la tabla puede ser el saldo acumulado histórico; para el saldo actual calcular siempre como `SUM(debe) - SUM(haber)` en la consulta, no confiar en el campo almacenado.
- Considerar índices en `idtrabajo`, `anio`, `cuota`, `fecha` para performance.

---

## Tabla de parámetros por entidad/envío

Cada combinación `idtrabajo + idenvio` tiene un porcentaje esperado de gastos de procesamiento y, en algunos casos, un porcentaje de comisión. Estos valores son la referencia para el control del dashboard.

**Gastos de procesamiento:** diferencia implícita entre lo liquidado y lo cobrado. No hay factura ni registro contable separado. La entidad simplemente paga menos. El % se calcula sobre el total liquidado.

**Comisiones:** se registran aparte en la tabla como registros con clase `GC` o `CO`. El % también se calcula sobre el total liquidado.

| idtrabajo | Entidad | idenvio | Envío | % Procesamiento | % Comisión |
|-----------|---------|---------|-------|-----------------|------------|
| 25 | Irrigacion | 17 | Asociacion Gremial Irrigacion | 20% | — |
| 6 | Municipalidad de Ciudad Mza. | 13 | Sindicato Muni. Ciudad Mza | 8% | 6% |
| 7 | Godoy Cruz | 15 | Sindicato Muni. Godoy Cruz | 1% | 10% |
| 14 | Municipalidad de Maipu | 10 | Sindicato Muni. Maipu | 10% | — |
| 9 | Guaymallen | 14 | Sindicato Muni. Guaymallen | 1% | 9% |
| 13 | Lujan | 11 | Sindicato Muni. Lujan | 0% | 8% |
| 21 | Tupungato | 8 | Sindicato Muni. Tupungato | 0% | 7% |
| 8 | Gral Alvear | 12 | Sindicato Muni. Gral. Alvear | 3% | 4% |
| 34 | Tarjeta Naranja | 33 | Tarjeta Naranja | 6% | — |
| 2 | BioPlanta | 18 | Asociacion Mutual BioPlanta | 6% | — |
| 20 | Tunuyan | 7 | Sindicato Muni. Tunuyan | 5% | — |
| 20 | Tunuyan | 23 | FATAG | 5% | — |
| 22 | Lavalle | 29 | Sindicato Muni. Lavalle | 0% | 5% |
| 30 | Esc.Nicolas Avellaneda | 26 | Esc.N.Avellaneda | 4% | — |
| 11 | La Paz | 24 | AMAS CODIGO | 4% | — |
| 8 | Gral Alvear | 23 | FATAG | 3% | — |
| 17 | San Carlos | 5 | Sindicato Muni. San Carlos | 3% | — |
| 12 | Las Heras | 22 | SAGAM | 3% | — |
| 47 | Tarjeta Mastercard | 45 | Tarjeta Mastercard | 2% | — |
| 7 | Godoy Cruz | 24 | AMAS CODIGO | 2% | — |
| 46 | Tarjeta Visa | 44 | Tarjeta Visa | 2% | — |
| 18 | San Martin | 9 | Sindicato Muni. San Martin | 2% | — |
| 5 | Gobierno de Mendoza | 21 | CUAD FATAG | 2% | — |
| 5 | Gobierno de Mendoza | 20 | CUAD AMAS | 2% | — |
| 16 | Rivadavia | 23 | FATAG | 1% | — |
| 10 | Junin | 24 | AMAS CODIGO | 1% | — |
| 24 | Sindicato de Correos | 16 | Sindicato Correos | 0% | — |
| 39 | Centro Empleados de Comercio | 37 | CEC | 0% | — |
| 3 | Camara de Diputados | 24 | AMAS CODIGO | 0% | — |
| 4 | Camara de Senadores | 24 | AMAS CODIGO | 0% | — |
| 49 | Hotel Uspallata | 46 | CEC Hotel Uspallata | 0% | — |

> Estos valores deben cargarse como constante en `config.py` (diccionario Python) ya que no están en la base de datos. Son la referencia fija del negocio.

### Estructura del diccionario en config.py

```python
# Clave: (idtrabajo, idenvio)
# Valor: {"proc": % esperado procesamiento, "com": % esperado comisión o None}
PARAMETROS_ENTIDAD = {
    (25, 17): {"proc": 20.0, "com": None},
    (6,  13): {"proc":  8.0, "com":  6.0},
    (7,  15): {"proc":  1.0, "com": 10.0},
    (14, 10): {"proc": 10.0, "com": None},
    (9,  14): {"proc":  1.0, "com":  9.0},
    (13, 11): {"proc":  0.0, "com":  8.0},
    (21,  8): {"proc":  0.0, "com":  7.0},
    (8,  12): {"proc":  3.0, "com":  4.0},
    (34, 33): {"proc":  6.0, "com": None},
    (2,  18): {"proc":  6.0, "com": None},
    (20,  7): {"proc":  5.0, "com": None},
    (20, 23): {"proc":  5.0, "com": None},
    (22, 29): {"proc":  0.0, "com":  5.0},
    (30, 26): {"proc":  4.0, "com": None},
    (11, 24): {"proc":  4.0, "com": None},
    (8,  23): {"proc":  3.0, "com": None},
    (17,  5): {"proc":  3.0, "com": None},
    (12, 22): {"proc":  3.0, "com": None},
    (47, 45): {"proc":  2.0, "com": None},
    (7,  24): {"proc":  2.0, "com": None},
    (46, 44): {"proc":  2.0, "com": None},
    (18,  9): {"proc":  2.0, "com": None},
    (5,  21): {"proc":  2.0, "com": None},
    (5,  20): {"proc":  2.0, "com": None},
    (16, 23): {"proc":  1.0, "com": None},
    (10, 24): {"proc":  1.0, "com": None},
    (24, 16): {"proc":  0.0, "com": None},
    (39, 37): {"proc":  0.0, "com": None},
    (3,  24): {"proc":  0.0, "com": None},
    (4,  24): {"proc":  0.0, "com": None},
    (49, 46): {"proc":  0.0, "com": None},
}
```

### Tolerancia de desvío

En el dashboard se considera que el % real es **aceptable** si está dentro de ±`TOLERANCIA_PCT` puntos porcentuales del valor esperado. Configurar en `config.py`:

```python
TOLERANCIA_PCT = 2.0  # ±2 puntos porcentuales sobre el % esperado
```

Ejemplos:
- Guaymallén espera 1% de procesamiento → aceptable entre -1% y 3%
- Ciudad Mza. espera 8% → aceptable entre 6% y 10%
- Si el real cae fuera de ese rango → celda roja en el dashboard
