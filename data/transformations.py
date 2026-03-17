"""
Transformaciones de datos para el dashboard.
"""

from __future__ import annotations

import pandas as pd

from config import (
    TIPOS_LIQUIDACION_REAL,
    TIPOS_COBRANZA_REAL,
    CLASES_COMISION,
    MESES,
    TOLERANCIA_PCT,
    get_parametros_entidad,
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

