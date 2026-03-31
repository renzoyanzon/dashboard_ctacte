"""
Transformaciones de datos para el dashboard.
"""

from __future__ import annotations

import calendar
from datetime import date

import numpy as np
import pandas as pd

from config import (
    CLASES_COMISION,
    COLOR_AMBAR,
    COBRANZA_DEVOLUCIONES,
    MESES,
    TIPOS_COBRANZA_REAL,
    TIPOS_LIQUIDACION_REAL,
    TOLERANCIA_PCT,
    VENCIMIENTOS,
    codigos_tipo_devolucion,
    get_parametros_entidad,
    get_regla_devoluciones_cobranza,
    get_nombre_entidad,
)


def _asegurar_columnas_mov(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nombres de columnas en minúsculas (evita Tipo/tipo según driver) y columnas mínimas.
    """
    d = df.copy()
    if d.empty:
        return d
    d.columns = [str(c).strip().lower() for c in d.columns]
    if "envio" not in d.columns and "idenvio" in d.columns:
        d["envio"] = d["idenvio"]
    for col in ("debe", "haber"):
        if col not in d.columns:
            d[col] = 0.0
    return d


def _mascara_devoluciones_por_regla(dff: pd.DataFrame, idt: int, ide: int, cfg: dict) -> pd.Series:
    """Filas que son devolución a restar: entidad + clase (+ tipo si la regla lo indica)."""
    tipos_dev = codigos_tipo_devolucion(cfg)
    clase_dev = str(cfg.get("clase", "")).strip().upper()
    m = (
        (dff["idtrabajo"] == int(idt))
        & (dff["envio"] == int(ide))
        & (dff["clase"] == clase_dev)
    )
    if tipos_dev:
        m &= dff["tipo"].isin(tipos_dev)
    return m


def calcular_cobranza_neta(df: pd.DataFrame, idtrabajo: int, idenvio: int) -> pd.DataFrame:
    """
    Calcula cobranza neta restando devoluciones si la entidad está en COBRANZA_DEVOLUCIONES.

    Retorna DataFrame con columnas:
        anio, cuota, cobranza_bruta, devoluciones, cobranza_neta

    Para el resto de entidades: devoluciones=0, neta=bruta.
    """
    try:
        dev_config = get_regla_devoluciones_cobranza(int(idtrabajo), int(idenvio))

        dfx = _asegurar_columnas_mov(df)
        if dfx.empty:
            return pd.DataFrame(
                columns=["anio", "cuota", "cobranza_bruta", "devoluciones", "cobranza_neta"]
            )

        if "tipo" in dfx.columns:
            dfx["tipo"] = dfx["tipo"].astype(str).str.strip().str.upper()
        else:
            dfx["tipo"] = ""
        if "clase" in dfx.columns:
            dfx["clase"] = dfx["clase"].astype(str).str.strip().str.upper()
        else:
            dfx["clase"] = ""
        dfx["haber"] = pd.to_numeric(dfx["haber"], errors="coerce").fillna(0.0)
        dfx["anio"] = pd.to_numeric(dfx["anio"], errors="coerce")
        dfx["cuota"] = pd.to_numeric(dfx["cuota"], errors="coerce").fillna(0).astype(int)

        cob_bruta = (
            dfx[dfx["tipo"].isin(TIPOS_COBRANZA_REAL)]
            .groupby(["anio", "cuota"])["haber"]
            .sum()
            .reset_index()
            .rename(columns={"haber": "cobranza_bruta"})
        )
        if cob_bruta.empty:
            return pd.DataFrame(
                columns=["anio", "cuota", "cobranza_bruta", "devoluciones", "cobranza_neta"]
            )

        if dev_config is None:
            cob_bruta["devoluciones"] = 0
            cob_bruta["cobranza_neta"] = cob_bruta["cobranza_bruta"]
            return cob_bruta

        tipos_dev = codigos_tipo_devolucion(dev_config)
        clase_esp = str(dev_config.get("clase", "")).strip().upper()
        tipo_s = dfx["tipo"].astype(str).str.strip().str.upper()
        clase_s = dfx["clase"].astype(str).str.strip().str.upper()
        mask = clase_s == clase_esp
        if tipos_dev:
            mask &= tipo_s.isin(tipos_dev)
        deb = pd.to_numeric(dfx["debe"], errors="coerce").fillna(0.0)
        dfx_m = dfx.assign(_mdev=deb)
        devoluciones = (
            dfx_m[mask]
            .groupby(["anio", "cuota"])["_mdev"]
            .sum()
            .reset_index()
            .rename(columns={"_mdev": "devoluciones"})
        )
        result = cob_bruta.merge(devoluciones, on=["anio", "cuota"], how="left")
        result["devoluciones"] = result["devoluciones"].fillna(0)
        result["cobranza_neta"] = result["cobranza_bruta"] - result["devoluciones"]
        return result
    except Exception as e:
        print(f"Error en calcular_cobranza_neta(): {e}")
        return pd.DataFrame(
            columns=["anio", "cuota", "cobranza_bruta", "devoluciones", "cobranza_neta"]
        )


def calcular_cobranza_neta_global(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cobranza neta global: bruto (IT/IA/IC/IE) menos devoluciones solo para las entidades
    definidas en COBRANZA_DEVOLUCIONES. El resto de entidades no resta nada (bruto = neto).

    Por período (anio, cuota): ratio = (bruta_total - devoluciones_total) / bruta_total
    y se aplica a cada forma de pago (tipo).

    Retorna DataFrame con columnas:
        anio, cuota, tipo, cobranza_neta
    """
    try:
        if df is None or df.empty:
            return pd.DataFrame(columns=["anio", "cuota", "tipo", "cobranza_neta"])

        # Primero unificar nombres (Tipo→tipo); si no, la validación falla con columnas del driver
        dff = _asegurar_columnas_mov(df)
        for col in ("idtrabajo", "anio", "cuota"):
            if col not in dff.columns:
                return pd.DataFrame(columns=["anio", "cuota", "tipo", "cobranza_neta"])

        if "envio" not in dff.columns and "idenvio" in dff.columns:
            dff["envio"] = dff["idenvio"]

        if "envio" not in dff.columns:
            return pd.DataFrame(columns=["anio", "cuota", "tipo", "cobranza_neta"])

        dff["haber"] = pd.to_numeric(dff["haber"], errors="coerce").fillna(0.0)
        dff["debe"] = pd.to_numeric(dff["debe"], errors="coerce").fillna(0.0)
        dff["idtrabajo"] = pd.to_numeric(dff["idtrabajo"], errors="coerce").fillna(-1).astype(int)
        dff["envio"] = pd.to_numeric(dff["envio"], errors="coerce").fillna(-1).astype(int)
        if "tipo" in dff.columns:
            dff["tipo"] = dff["tipo"].astype(str).str.strip().str.upper()
        else:
            dff["tipo"] = ""
        if "clase" in dff.columns:
            dff["clase"] = dff["clase"].astype(str).str.strip().str.upper()
        else:
            dff["clase"] = ""

        cob = dff[dff["tipo"].isin(TIPOS_COBRANZA_REAL)].copy()
        if cob.empty:
            return pd.DataFrame(columns=["anio", "cuota", "tipo", "cobranza_neta"])

        cob_tipos = cob.groupby(["anio", "cuota", "tipo"], as_index=False)["haber"].sum()
        tot_bruta = cob_tipos.groupby(["anio", "cuota"], as_index=False)["haber"].sum().rename(
            columns={"haber": "bruta_total"}
        )

        # Importe de devoluciones en campo debe (cobranza ingresos va en haber)
        dff = dff.assign(_monto_devolucion=dff["debe"])

        mask_dev = pd.Series(False, index=dff.index)
        for (idt, ide), cfg in COBRANZA_DEVOLUCIONES.items():
            mask_dev |= _mascara_devoluciones_por_regla(dff, idt, ide, cfg)

        dev_por_periodo = (
            dff[mask_dev]
            .groupby(["anio", "cuota"], as_index=False)["_monto_devolucion"]
            .sum()
            .rename(columns={"_monto_devolucion": "devoluciones"})
        )

        merged = tot_bruta.merge(dev_por_periodo, on=["anio", "cuota"], how="left")
        merged["devoluciones"] = merged["devoluciones"].fillna(0.0)
        merged["neta_total"] = merged["bruta_total"] - merged["devoluciones"]
        merged["ratio"] = np.where(
            merged["bruta_total"] > 0,
            merged["neta_total"] / merged["bruta_total"],
            1.0,
        )

        out = cob_tipos.merge(merged[["anio", "cuota", "ratio"]], on=["anio", "cuota"], how="left")
        out["ratio"] = out["ratio"].fillna(1.0)
        out["cobranza_neta"] = out["haber"] * out["ratio"]
        return out[["anio", "cuota", "tipo", "cobranza_neta"]]
    except Exception as e:
        print(f"Error en calcular_cobranza_neta_global(): {e}")
        return pd.DataFrame(columns=["anio", "cuota", "tipo", "cobranza_neta"])


def tabla_cobranza_neta_por_entidad(df_mov: pd.DataFrame) -> pd.DataFrame:
    """
    Una fila por entidad (idtrabajo, envio): nombre y cobranza neta total
    en el rango de movimientos dado (misma lógica que calcular_cobranza_neta por entidad).
    """
    try:
        if df_mov is None or df_mov.empty:
            return pd.DataFrame(columns=["nombre", "cobranza_neta"])

        dfx = _asegurar_columnas_mov(df_mov)
        if "envio" not in dfx.columns and "idenvio" in dfx.columns:
            dfx["envio"] = dfx["idenvio"]
        if "idtrabajo" not in dfx.columns or "envio" not in dfx.columns:
            return pd.DataFrame(columns=["nombre", "cobranza_neta"])

        dfx["idtrabajo"] = pd.to_numeric(dfx["idtrabajo"], errors="coerce")
        dfx["envio"] = pd.to_numeric(dfx["envio"], errors="coerce")
        dfx = dfx.dropna(subset=["idtrabajo", "envio"])

        rows = []
        for (idt, ide), g in dfx.groupby(["idtrabajo", "envio"]):
            idt_i, ide_i = int(idt), int(ide)
            net = calcular_cobranza_neta(g, idt_i, ide_i)
            if net.empty:
                total = 0.0
            else:
                total = float(net["cobranza_neta"].sum())
            if total <= 0:
                continue
            label = get_nombre_entidad(idt_i, ide_i)
            if not label or str(label).strip() == "":
                label = f"{idt_i} / {ide_i}"
            rows.append({"nombre": str(label).strip(), "cobranza_neta": total})

        out = pd.DataFrame(rows)
        if out.empty:
            return out
        return out.sort_values("cobranza_neta", ascending=False).reset_index(drop=True)
    except Exception as e:
        print(f"Error en tabla_cobranza_neta_por_entidad(): {e}")
        return pd.DataFrame(columns=["nombre", "cobranza_neta"])


def cobranza_neta_por_fecha_desde_movimientos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reparte cobranza neta por año/mes de fecha de movimiento (para gráfico Inicio «Por fecha»).
    """
    try:
        if df is None or df.empty or "fecha" not in df.columns:
            return pd.DataFrame(columns=["anio_fecha", "mes_fecha", "tipo", "total_haber"])

        dff = df.copy()
        dff["haber"] = pd.to_numeric(dff["haber"], errors="coerce").fillna(0.0)
        if "tipo" in dff.columns:
            dff["tipo"] = dff["tipo"].astype(str).str.strip().str.upper()
        else:
            dff["tipo"] = ""

        df_net = calcular_cobranza_neta_global(dff)
        cob = dff[dff["tipo"].isin(TIPOS_COBRANZA_REAL)].copy()
        cob["fecha"] = pd.to_datetime(cob["fecha"], errors="coerce")
        cob = cob.dropna(subset=["fecha"])
        if cob.empty:
            return pd.DataFrame(columns=["anio_fecha", "mes_fecha", "tipo", "total_haber"])

        cob = cob.merge(
            df_net.rename(columns={"cobranza_neta": "neta_tipo"}),
            on=["anio", "cuota", "tipo"],
            how="left",
        )
        cob["neta_tipo"] = cob["neta_tipo"].fillna(0)
        cob["bruta_tipo"] = cob.groupby(["anio", "cuota", "tipo"])["haber"].transform("sum")
        cob["haber_neta"] = np.where(
            cob["bruta_tipo"] > 0,
            cob["haber"] * cob["neta_tipo"] / cob["bruta_tipo"],
            0.0,
        )
        cob["anio_fecha"] = cob["fecha"].dt.year.astype(int)
        cob["mes_fecha"] = cob["fecha"].dt.month.astype(int)
        out = (
            cob.groupby(["anio_fecha", "mes_fecha", "tipo"], as_index=False)["haber_neta"]
            .sum()
            .rename(columns={"haber_neta": "total_haber"})
        )
        return out
    except Exception as e:
        print(f"Error en cobranza_neta_por_fecha_desde_movimientos(): {e}")
        return pd.DataFrame(columns=["anio_fecha", "mes_fecha", "tipo", "total_haber"])


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
        dev_config = get_regla_devoluciones_cobranza(int(idtrabajo), int(idenvio))

        df_anio = df[df["anio"] == anio].copy()

        # series por mes
        liq = (
            df_anio[df_anio["tipo"].isin(TIPOS_LIQUIDACION_REAL)]
            .groupby("cuota")["debe"]
            .sum()
        )
        cob_bruta = (
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
        cob_bruta = cob_bruta.reindex(meses_cols, fill_value=0.0)
        com = com.reindex(meses_cols, fill_value=0.0)

        dev_s = pd.Series(0.0, index=meses_cols)
        if dev_config is not None:
            nmx = calcular_cobranza_neta(df_anio, int(idtrabajo), int(idenvio))
            if not nmx.empty:
                nmx = nmx[nmx["anio"] == anio]
                if not nmx.empty:
                    dev_s = nmx.set_index("cuota")["devoluciones"].reindex(meses_cols, fill_value=0.0)
                    cob = nmx.set_index("cuota")["cobranza_neta"].reindex(meses_cols, fill_value=0.0)
                else:
                    cob = cob_bruta
            else:
                cob = cob_bruta
        else:
            cob = cob_bruta

        dif = liq - cob
        liq_nan = liq.replace(0, float("nan"))
        pct_proc = (dif / liq_nan * 100).round(1)
        pct_com = (com / liq_nan * 100).round(1)

        filas = ["Liquidado", "Cobrado"]
        if dev_config is not None:
            filas.append("Devoluciones")
        filas += ["Diferencia", "% Proc. real"]
        if proc_esp is not None:
            filas.append("% Proc. esperado")
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
            d_val = float(dev_s[m]) if dev_config is not None else 0.0
            sin = (l_val == 0 and c_val == 0 and (dev_config is None or d_val == 0))

            vals = [
                _fmt_money(l_val, sin),
                _fmt_money(c_val, sin),
            ]
            if dev_config is not None:
                vals.append(_fmt_money(d_val, sin))
            vals += [
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
            if dev_config is not None:
                styles.append(
                    {
                        "if": {"filter_query": "{Concepto} = 'Devoluciones'", "column_id": col},
                        "backgroundColor": COLOR_AMBAR,
                        "color": "#1a1a1a",
                        "fontWeight": "bold",
                    }
                )
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

