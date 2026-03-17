"""
Transformaciones de datos para el dashboard.
"""

from __future__ import annotations

import pandas as pd
from datetime import date
import calendar

from config import (
    TIPOS_LIQUIDACION_REAL,
    TIPOS_COBRANZA_REAL,
    CLASES_COMISION,
    MESES,
    TOLERANCIA_PCT,
    get_parametros_entidad,
    VENCIMIENTOS,
)


def build_pivot_entidad(df: pd.DataFrame, idtrabajo: int, idenvio: int, anio: int):
    """
    Construye el cuadro pivote por entidad para un año dado.

    Filas:
      - Liquidado / Cobrado / Diferencia
      - % Proc. real / % Proc. esperado
      - (si aplica) % Com. real / % Com. esperado

    Columnas: Ene..Dic

    Reglas:
      - Si no hay datos en un período: mostrar "-"
      - Colorización: según lógica de tolerancia y casos sin actividad / cobro sin liquidación

    Returns:
      pivot_df (pd.DataFrame), styles (list[dict]) para dash.DataTable.style_data_conditional
    """
    try:
        if df is None or df.empty:
            # pivot vacío con columnas fijas
            cols = ["Concepto", *[MESES[m] for m in range(1, 13)]]
            return pd.DataFrame(columns=cols), []

        anio = int(anio)
        params = get_parametros_entidad(int(idtrabajo), int(idenvio)) or {"proc": None, "com": None}
        proc_esp = params.get("proc")
        com_esp = params.get("com")

        df_anio = df[df["anio"] == anio].copy()

        # series por mes
        liq = (
            df_anio[df_anio["tipo"].isin(TIPOS_LIQUIDACION_REAL)]
            .groupby("cuota")["debe"]
            .sum()
        )
        cob = (
            df_anio[df_anio["tipo"].isin(TIPOS_COBRANZA_REAL)]
            .groupby("cuota")["haber"]
            .sum()
        )
        com = (
            df_anio[df_anio["clase"].isin(CLASES_COMISION)]
            .groupby("cuota")["debe"]
            .sum()
        )

        meses_cols = list(range(1, 13))
        liq = liq.reindex(meses_cols, fill_value=0.0)
        cob = cob.reindex(meses_cols, fill_value=0.0)
        com = com.reindex(meses_cols, fill_value=0.0)

        dif = liq - cob
        liq_nan = liq.replace(0, float("nan"))
        pct_proc = (dif / liq_nan * 100).round(1)
        pct_com = (com / liq_nan * 100).round(1)

        filas = ["Liquidado", "Cobrado", "Diferencia", "% Proc. real", "% Proc. esperado"]
        if proc_esp is None:
            filas = ["Liquidado", "Cobrado", "Diferencia", "% Proc. real"]
        if com_esp is not None:
            filas += ["% Com. real", "% Com. esperado"]

        pivot = pd.DataFrame({"Concepto": filas})

        def _fmt_money(v: float, show_dash: bool):
            if show_dash:
                return "-"
            if v == 0:
                return "-"
            # miles con punto y sin decimales (como en guía)
            s = f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"$ {s}"

        def _fmt_pct(v, show_dash: bool):
            if show_dash:
                return "-"
            if pd.isna(v):
                return "-"
            return f"{float(v):.1f}".replace(".", ",") + "%"

        for m in meses_cols:
            col = MESES[m]
            l_val = float(liq[m])
            c_val = float(cob[m])
            sin = (l_val == 0 and c_val == 0)

            vals = [
                _fmt_money(l_val, sin),
                _fmt_money(c_val, sin),
                _fmt_money(float(dif[m]), sin),
                _fmt_pct(pct_proc[m], sin),
            ]
            if proc_esp is not None:
                vals.append(f"{float(proc_esp):.1f}".replace(".", ",") + "%")
            if com_esp is not None:
                vals.append(_fmt_pct(pct_com[m], sin))
                vals.append(f"{float(com_esp):.1f}".replace(".", ",") + "%")

            pivot[col] = vals

        def _color(p_real, p_esp, l_val, c_val):
            # gris: sin actividad
            if l_val == 0 and c_val == 0:
                return "#E9ECEF"
            # amarillo: cobro sin liquidación
            if l_val == 0 and c_val > 0:
                return "#FFF3CD"
            # rojo: sin referencia o nan
            if p_esp is None or pd.isna(p_real):
                return "#F8D7DA"
            # verde: dentro del rango
            if (p_esp - TOLERANCIA_PCT) <= float(p_real) <= (p_esp + TOLERANCIA_PCT):
                return "#D4EDDA"
            return "#F8D7DA"

        styles = []
        for m in meses_cols:
            col = MESES[m]
            styles.append(
                {
                    "if": {"filter_query": "{Concepto} = '% Proc. real'", "column_id": col},
                    "backgroundColor": _color(pct_proc[m], proc_esp, float(liq[m]), float(cob[m])),
                    "fontWeight": "bold",
                }
            )
            if com_esp is not None:
                styles.append(
                    {
                        "if": {"filter_query": "{Concepto} = '% Com. real'", "column_id": col},
                        "backgroundColor": _color(pct_com[m], com_esp, float(liq[m]), float(cob[m])),
                        "fontWeight": "bold",
                    }
                )

        return pivot, styles
    except Exception as e:
        print(f"Error en build_pivot_entidad(): {e}")
        cols = ["Concepto", *[MESES[m] for m in range(1, 13)]]
        return pd.DataFrame(columns=cols), []


def calcular_vencimiento(anio: int, cuota: int, desfasaje: int, dia_corte: int) -> date:
    """
    Calcula la fecha límite de pago para un período dado.
    Si dia_corte = 31 y el mes no tiene 31 días, usa el último día del mes.
    Maneja el desborde de meses (ej: cuota=11 + desfasaje=3 = mes 2 del año siguiente).
    """
    mes_venc = int(cuota) + int(desfasaje)
    anio_venc = int(anio)
    while mes_venc > 12:
        mes_venc -= 12
        anio_venc += 1

    ultimo_dia = calendar.monthrange(anio_venc, mes_venc)[1]
    dia_real = min(int(dia_corte), int(ultimo_dia))
    return date(anio_venc, mes_venc, dia_real)


def calcular_estado_vencimiento(anio: int, cuota: int, nombre_envio: str, tiene_cobranza: bool) -> str:
    """
    Retorna el estado de vencimiento de un período para un envío.

    Estados posibles:
        'ok'         → tiene cobranza registrada
        'pendiente'  → no tiene cobranza pero aún no venció
        'vencido'    → no tiene cobranza y ya pasó la fecha de vencimiento
        'sin_config' → el envío no está en VENCIMIENTOS (no se puede calcular)
    """
    if bool(tiene_cobranza):
        return "ok"

    params = VENCIMIENTOS.get(str(nombre_envio))
    if params is None:
        return "sin_config"

    fecha_venc = calcular_vencimiento(int(anio), int(cuota), int(params["desfasaje"]), int(params["dia_corte"]))
    hoy = date.today()
    if hoy > fecha_venc:
        return "vencido"
    return "pendiente"


def detectar_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta faltantes por período para el universo de datos provisto.

    - Liquidaciones reales: TIPOS_LIQUIDACION_REAL (IM, MI, IS)
    - Cobranzas reales: TIPOS_COBRANZA_REAL (IT, IA, IC, IE)

    Espera columnas mínimas:
      - idtrabajo, idenvio (o envio), anio, cuota, tipo
      - opcionales: entidad_nombre, envio_nombre (para reporting)

    Retorna DataFrame con:
      idtrabajo, idenvio, envio_nombre, entidad_nombre, anio, cuota,
      tiene_liquidacion, tiene_cobranza
    Solo períodos donde falta alguna de las dos.
    """
    try:
        if df is None or df.empty:
            return pd.DataFrame()

        dff = df.copy()
        # Normalizar nombres de columnas
        if "idenvio" not in dff.columns and "envio" in dff.columns:
            dff["idenvio"] = dff["envio"]

        for col in ["idtrabajo", "idenvio", "anio", "cuota"]:
            if col in dff.columns:
                dff[col] = pd.to_numeric(dff[col], errors="coerce")

        base_cols = ["idtrabajo", "idenvio", "anio", "cuota"]
        dff = dff[dff["tipo"].isin(TIPOS_LIQUIDACION_REAL + TIPOS_COBRANZA_REAL)].copy()

        liquidaciones = dff[dff["tipo"].isin(TIPOS_LIQUIDACION_REAL)][base_cols].drop_duplicates()
        liquidaciones["tiene_liquidacion"] = True

        cobranzas = dff[dff["tipo"].isin(TIPOS_COBRANZA_REAL)][base_cols].drop_duplicates()
        cobranzas["tiene_cobranza"] = True

        todos_periodos = dff[base_cols].drop_duplicates()

        res = (
            todos_periodos.merge(liquidaciones, on=base_cols, how="left")
            .merge(cobranzas, on=base_cols, how="left")
        )
        res["tiene_liquidacion"] = res["tiene_liquidacion"].fillna(False)
        res["tiene_cobranza"] = res["tiene_cobranza"].fillna(False)

        # preservar columnas de nombre si existen (join por claves)
        if "envio_nombre" in df.columns:
            names = df[base_cols + ["envio_nombre"]].drop_duplicates()
            res = res.merge(names, on=base_cols, how="left")
        if "entidad_nombre" in df.columns:
            names = df[base_cols + ["entidad_nombre"]].drop_duplicates()
            res = res.merge(names, on=base_cols, how="left")

        falt = res[~(res["tiene_liquidacion"] & res["tiene_cobranza"])].copy()
        return falt
    except Exception as e:
        print(f"Error en detectar_faltantes(): {e}")
        return pd.DataFrame()

