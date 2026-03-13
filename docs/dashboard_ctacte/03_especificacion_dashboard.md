# Especificación Funcional — Dashboard Interactivo

## Principios de diseño

- **Tiempo real:** Los datos se obtienen directamente de la base de datos en cada interacción (sin caché estático). Opcionalmente, implementar caché de 5 minutos con `diskcache` para aliviar carga en DB.
- **Reactivo:** Todos los gráficos y tablas se actualizan automáticamente al cambiar cualquier filtro.
- **Control visual:** El objetivo principal es detectar anomalías (faltantes, desvíos) de forma inmediata y visual, no solo consultar números.
- **Mobile-friendly:** Layout responsivo usando Dash Bootstrap Components (grid de 12 columnas).

---

## Filtros globales (panel superior)

Estos filtros afectan a **todas** las vistas del dashboard simultáneamente.

| Filtro | Componente Dash | Descripción |
|--------|----------------|-------------|
| Entidad | `dcc.Dropdown` (multi) | Seleccionar una o varias municipalidades. Carga desde tabla `trabajo`. |
| Año | `dcc.Dropdown` | Año del período. Valores: últimos 3 años + año actual. |
| Período (cuota) | `dcc.Dropdown` (multi) | Meses 1-12. Permite seleccionar rango o meses específicos. |
| Tipo de movimiento | `dcc.Checklist` | Liquidaciones / Cobranzas / Gastos / Devoluciones |
| Botón actualizar | `html.Button` | Fuerza recarga de datos desde DB. |

---

## Página 1: Inicio — Resumen general

### Panel KPIs (fila de tarjetas)
Mostrar siempre visibles en la parte superior:

- **Total debe (período seleccionado):** suma de todos los registros debe filtrados
- **Total haber (período seleccionado):** suma de todos los haber filtrados
- **Saldo neto:** debe - haber (con color rojo si positivo, verde si negativo o cero)
- **Entidades con deuda:** cantidad de entidades con saldo > 0
- **Períodos sin cobranza:** cantidad de combinaciones entidad+período con liquidación pero sin cobranza

### Gráfico: Ranking de entidades por saldo

- Tipo: Barras horizontales ordenadas de mayor a menor saldo
- Color: Rojo si saldo > 0 (deuda), Verde si saldo ≤ 0 (al día)
- Interactivo: Click en una barra navega a la Vista 2 (detalle de entidad)
- Plotly: `go.Bar` horizontal con `color_discrete_map`

### Gráfico: Evolución mensual — total cobrado vs liquidado (todas las entidades)

- Tipo: Barras agrupadas o líneas dobles
- Eje X: períodos mes/año (formato "Ene 2025", "Feb 2025"...)
- Series: "Total liquidado" (suma de debe tipos IM/MI/IS) vs "Total cobrado" (suma de haber tipos IT/IA/IC/IE)
- Muestra la tendencia global: ¿la mutual está cobrando lo que liquida?
- Filtrable por año con el filtro global
- Plotly: `go.Bar` con `barmode='group'` o `go.Scatter` para ambas series

### Gráfico: Evolución temporal del saldo total

- Tipo: Línea de área (area chart)
- Eje X: períodos (anio+cuota formateados como "Ene 2026", "Feb 2026", etc.)
- Eje Y: saldo neto acumulado
- Muestra tendencia: ¿el saldo total crece o se reduce mes a mes?

### Tabla: Resumen por entidad

Columnas: Entidad | Debe | Haber | Saldo | Períodos pendientes | Estado
- Estado: semáforo (🔴 deuda alta / 🟡 deuda baja / 🟢 al día)
- Ordenable por cualquier columna
- Click en fila → navega a Vista 2

---

## Página 2: Por entidad — Detalle completo

Se activa al seleccionar una entidad en el menú lateral o al hacer click en el ranking de la página de inicio. Internamente organizada en **4 pestañas** usando `dbc.Tabs`:

| Pestaña | Contenido |
|---------|-----------|
| Resumen | Encabezado KPIs + gráfico barras liquidado vs cobrado + saldo acumulado |
| Cuadro de control | Cuadro pivote por año con % de diferencia y colores |
| Movimientos | Tabla detalle de todos los registros filtrables |
| Análisis | Gráficos de distribución por subgrupo (mutuos, cuota social, sepelio, etc.) |

### Encabezado de entidad
- Nombre completo de la entidad
- Saldo actual destacado (grande, con color según estado)
- Última cobranza registrada (fecha y monto)
- Última liquidación emitida (fecha y monto)

### Filtro de año

- Dropdown con los años disponibles para esa entidad (ej: 2024, 2025, 2026)
- Al cambiar el año se actualizan el cuadro pivote y el gráfico
- Por defecto muestra el año actual

### Cuadro pivote: Liquidado / Cobrado / Diferencia por período

Este es el cuadro central de control por entidad. Muestra columnas por mes (cuota 1 a 12) del año seleccionado, con las filas fijas:

| Fila | Descripción | Cálculo |
|------|-------------|---------|
| Liquidado | Total emitido ese período | SUM(debe) donde tipo IN (IM, MI, IS) |
| Cobrado | Total recibido ese período | SUM(haber) donde tipo IN (IT, IA, IC, IE) |
| Diferencia | Monto no cobrado | Liquidado - Cobrado |
| % Diferencia | Proporción no cobrada | (Diferencia / Liquidado) × 100 |

**Formato de columnas:** el año va como encabezado del cuadro (ej: "Año 2026") y debajo las columnas son los meses: Ene, Feb, Mar, Abr, May, Jun, Jul, Ago, Sep, Oct, Nov, Dic. Los meses sin datos se muestran vacíos o con guión.

**Colorización de celdas (fila % Diferencia):**

El color de cada celda se determina comparando el % real calculado contra el **% esperado de procesamiento** definido en `PARAMETROS_ENTIDAD` para esa combinación `idtrabajo + idenvio`, con una tolerancia de `±TOLERANCIA_PCT` puntos porcentuales.

| Color | Condición |
|-------|-----------|
| 🟢 Verde | % real dentro del rango esperado ± tolerancia |
| 🔴 Rojo | % real fuera del rango (demasiado alto o demasiado bajo) |
| 🟡 Amarillo | Cobrado > 0 pero sin liquidación cargada (error de carga) |
| ⬜ Gris | Sin actividad en el período (ambos en cero) |

**Ejemplos concretos:**
- Guaymallén (proc. esperado 1%, tolerancia ±2%): rango aceptable 0%–3%. Si el real es 2% → verde. Si es 15% → rojo.
- Ciudad Mza. (proc. esperado 8%, tolerancia ±2%): rango aceptable 6%–10%. Si el real es 7.5% → verde. Si es 20% → rojo.
- Irrigación (proc. esperado 20%): si el real es 18% → verde. Si es 5% → rojo (pagaron de más).

**Fila adicional: % Comisión real** — para entidades que tienen comisión esperada (`com` no nulo en `PARAMETROS_ENTIDAD`), agregar una quinta fila al cuadro:

| Fila | Descripción | Cálculo |
|------|-------------|---------|
| % Comisión | Comisión real cobrada | SUM(debe) clase GC/CO / Liquidado × 100 |

Esta fila también se coloriza: verde si está dentro del rango esperado ± tolerancia, rojo si no.

**Comportamiento especial:**
- Si Liquidado > 0 y Cobrado = 0: mostrar % diferencia como 100% en rojo
- Si ambos son 0: celda gris

**Implementación:** usar `dash.DataTable` con `style_data_conditional` para colorizar celdas dinámicamente según el valor del % de diferencia.

### Gráfico: Liquidaciones vs Cobranzas por período

- Tipo: Barras agrupadas
- Eje X: meses del año seleccionado (Ene, Feb, Mar...)
- Series: "Liquidado" vs "Cobrado"
- Complementa el cuadro pivote con una vista visual de la magnitud
- Plotly: `go.Bar` con `barmode='group'`

### Gráfico: Saldo acumulado de la entidad

- Tipo: Línea con área rellena
- Eje X: períodos cronológicos
- Eje Y: saldo acumulado
- Línea de referencia horizontal en 0
- Zonas coloreadas: rojo arriba de 0, verde abajo de 0

### Tabla: Detalle de movimientos

Columnas: Fecha | Período (cuota/anio) | Tipo | Clase | Subgrupo | Detalle | Debe | Haber | Usuario
- Filtrable por tipo de movimiento
- Exportable a Excel con un botón
- Paginación de 20 registros por página
- Usar `dash.DataTable`

### Pestaña Análisis: distribución por subgrupo

Esta pestaña está dentro del detalle de entidad y muestra cómo se compone lo liquidado y cobrado por conceptos.

**Gráfico: Torta de liquidaciones por subgrupo**
- Muestra qué proporción del total liquidado corresponde a Mutuos, Cuota Social, Sepelio, Fallecimiento, Comisiones, etc.
- Filtrado por año seleccionado
- Plotly: `go.Pie` con `hole=0.4` (donut) para mejor legibilidad
- Solo incluye tipos IM, MI, IS (liquidaciones reales)

**Gráfico: Torta de cobranzas por forma de pago**
- Distribución de lo cobrado entre Transferencia (IT), FDC (IA), Cheque (IC), Efectivo (IE)
- Permite ver si la entidad paga siempre de la misma forma o varía

**Gráfico: Barras de comisiones por período**
- Muestra los montos de clase GC y CO a lo largo del año
- Útil para detectar períodos donde se cobraron o no se cobraron comisiones

---

## Página 3: Control de carga — detección de faltantes

Esta vista es la más importante para el control operativo.

### Heatmap de cobertura

- Eje X: períodos (meses del año)
- Eje Y: entidades
- Celda: 
  - 🟢 Verde: liquidación + cobranza presentes
  - 🟡 Amarillo: solo liquidación (falta cobranza)
  - 🔴 Rojo: ni liquidación ni cobranza (ambas faltantes)
  - ⬜ Gris: entidad no activa en ese período
- Plotly: `go.Heatmap` con colorscale personalizada o `px.imshow`
- Click en celda → muestra detalle del período/entidad

### Tabla: Faltantes detectados

Lista de todos los períodos con datos incompletos:

| Entidad | Período | Liquidación | Cobranza | Acción sugerida |
|---------|---------|-------------|----------|-----------------|
| Guaymallén | Feb 2026 | ✅ Cargada | ❌ Faltante | Cargar cobranza |
| Las Heras | Mar 2026 | ❌ Faltante | ❌ Faltante | Verificar ambas |

- Exportable a Excel
- Ordenable por entidad o período

### KPIs de control

- Total de celdas con faltantes
- Entidades con algún faltante
- Período más antiguo sin cerrar
- Porcentaje de períodos completos (del total esperado)

---

## Vista 4: Análisis por concepto (extensión futura)

Cuando se definan en detalle los valores de tipo/clase:

- Desglose por concepto (cuotas de préstamos, aportes, etc.)
- Comparativo entre entidades por concepto
- Evolución de un concepto específico en el tiempo

---

## Comportamiento de actualización

```python
# Patrón de callback reactivo en Dash
@app.callback(
    Output('grafico-saldo', 'figure'),
    Output('tabla-detalle', 'data'),
    Output('kpi-saldo', 'children'),
    Input('filtro-entidad', 'value'),
    Input('filtro-anio', 'value'),
    Input('filtro-cuota', 'value'),
    Input('btn-actualizar', 'n_clicks')
)
def actualizar_vista(entidad, anio, cuota, n_clicks):
    # Cada cambio de filtro dispara recarga desde DB
    df = queries.get_estado_cuenta(entidad, anio, cuota)
    figura = charts.build_saldo_chart(df)
    tabla = df.to_dict('records')
    kpi = f"${df['saldo_neto'].sum():,.2f}"
    return figura, tabla, kpi
```

---

## Paleta de colores y estilo

- Fondo: blanco / gris muy claro
- Deuda alta (saldo > umbral): `#E24B4A` (rojo)
- Deuda baja / advertencia: `#EF9F27` (ámbar)
- Al día / pagado: `#1D9E75` (verde teal)
- Sin datos: `#B4B2A9` (gris)
- Liquidación (barras): `#378ADD` (azul)
- Cobranza (barras): `#1D9E75` (verde)
- Fuente: Inter o sistema por defecto

---

## Exportación

- Cada tabla debe tener un botón "Exportar a Excel" usando `dcc.send_data_frame` + `pandas.ExcelWriter`
- Nombre de archivo sugerido: `estado_cuenta_{entidad}_{anio}_{mes_actual}.xlsx`
