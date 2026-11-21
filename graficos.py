"""Construção dos gráficos Altair e Plotly, sem dependência do Streamlit."""
from __future__ import annotations

import numpy as np
import pandas as pd
import altair as alt
import plotly.graph_objects as go

import analises as an
import config

FONTE = dict(family="Inter, Segoe UI, Arial, sans-serif", size=13)

# ---------------------------------------------------------------- Funções auxiliares Altair

def chart_base(chart, height=320):
    """Aplica as configurações visuais básicas aos gráficos Altair."""
    return (
        chart
        .properties(height=height)
        .configure_view(stroke=None)
    )


def marks(chart, begin, end, enabled):
    """Adiciona os marcos geopolíticos dentro do período selecionado."""
    if not enabled:
        return chart

    for marco in config.MARCOS:
        dt = marco["data"]

        if begin <= dt <= end:
            line = alt.Chart(
                pd.DataFrame({
                    "date": [dt],
                    "event": [marco["descricao"]]
                })
            ).mark_rule(
                color=marco["cor"],
                strokeDash=[5, 4],
                strokeWidth=2
            ).encode(
                x="date:T",
                tooltip="event:N"
            )

            chart = chart + line

    return chart


def line_chart(
    df,
    y,
    colorfield,
    domain,
    colors,
    begin,
    end,
    events,
    ytitle,
    height=315
):
    """Constrói gráficos de evolução semanal com marcos opcionais."""
    base = alt.Chart(df).mark_line(
        point=alt.OverlayMarkDef(size=28),
        strokeWidth=2
    ).encode(
        x=alt.X(
            "Semana:T",
            title="Semanas",
            axis=alt.Axis(
                format="%b/%Y",
                tickCount="month"
            )
        ),
        y=alt.Y(
            f"{y}:Q",
            title=ytitle,
            scale=alt.Scale(zero=False)
        ),
        color=alt.Color(
            f"{colorfield}:N",
            scale=alt.Scale(
                domain=domain,
                range=colors
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip("Semana:T", format="%d/%m/%Y"),
            alt.Tooltip(f"{colorfield}:N"),
            alt.Tooltip(f"{y}:Q", format=".3f")
        ]
    )

    return chart_base(
        marks(base, begin, end, events),
        height
    )


# ---------------------------------------------------------------- Gráfico 1
def grafico_brasil(df, marcos, inicio, fim):
    """Constrói o gráfico de evolução semanal dos preços nacionais."""
    combustiveis = config.ORDEM_COMBUSTIVEIS

    return line_chart(
        df.sort_values("Semana"),
        config.COL_PRECO,
        "Combustível",
        combustiveis,
        [config.CORES_COMBUSTIVEIS[c] for c in combustiveis],
        inicio,
        fim,
        marcos,
        "R$/litro"
    )


# ---------------------------------------------------------------- Gráfico 2.1
def grafico_regioes(df, marcos, inicio, fim):
    """Constrói o gráfico de evolução semanal dos preços regionais."""
    cores = config.CORES_REGIOES

    return line_chart(
        df,
        config.COL_PRECO,
        "Região",
        list(cores.keys()),
        list(cores.values()),
        inicio,
        fim,
        marcos,
        "Preço médio (R$/litro)",
        height=300
    )


# ---------------------------------------------------------------- Gráfico 2.2
def grafico_ranking(df, metric, ranking_extremos):
    """Constrói o gráfico de comparação estadual."""

    if ranking_extremos:
        cores = config.CORES_RANKING
        campo_cor = "Grupo:N"
    else:
        cores = config.CORES_REGIOES
        campo_cor = "Região:N"

    color_encoding = alt.Color(
        campo_cor,
        scale=alt.Scale(
            domain=list(cores.keys()),
            range=list(cores.values())
        ),
        legend=None
    )

    plot = alt.Chart(df).mark_bar(
        cornerRadiusEnd=3
    ).encode(
        x=alt.X(
            f"{metric}:Q",
            title="R$/litro" if metric == "Média" else "Variação (%)",
            scale=alt.Scale(zero=metric == "Média")
        ),
        y=alt.Y(
            "UF:N",
            sort=alt.SortField(
                field=metric,
                order="descending"
            ),
            title=None,
            axis=alt.Axis(labelOverlap=False)
        ),
        color=color_encoding,
        tooltip=[
            "UF:N",
            "Região:N",
            alt.Tooltip(f"{metric}:Q", format=".2f")
        ]
    )

    return chart_base(
        plot,
        max(260, len(df) * 20)
    )


# ---------------------------------------------------------------- Gráfico 3
def grafico_brent(df, y, smooth, marcos, inicio, fim):
    """Constrói o gráfico de evolução semanal do petróleo Brent."""

    base = alt.Chart(df).mark_line(
        point=True,
        color=config.COR_BRENT,
        strokeWidth=2.5
    ).encode(
        x=alt.X(
            "Semana:T",
            title="Semanas",
            axis=alt.Axis(
                format="%b/%Y",
                tickCount="month"
            )
        ),
        y=alt.Y(
            f"{y}:Q",
            title="US$/barril" if y == config.COL_BRENT else "%",
            scale=alt.Scale(zero=False)
        ),
        tooltip=[
            alt.Tooltip("Semana:T", format="%d/%m/%Y"),
            alt.Tooltip(f"{y}:Q", format=".2f")
        ]
    )

    if smooth:
        rolling = an.media_movel_brent(df, y)

        base = base + alt.Chart(rolling).mark_line(
            color=config.COR_MEDIA_MOVEL_BRENT,
            strokeDash=[6, 4]
        ).encode(
            x="Semana:T",
            y="Média móvel:Q"
        )

    return chart_base(
        marks(base, inicio, fim, marcos),
        height=340
    )


# ---------------------------------------------------------------- Gráfico 4
def grafico_dispersao(pairs, regression, fuel, selected_uf, all_mode, ufs):
    """Constrói o gráfico de dispersão e a linha de regressão linear."""

    pairs, phase_names = an.preparar_dispersao(pairs)

    phase_colors = config.CORES_FASES

    fig = go.Figure()

    symbols = [
        "circle",
        "square",
        "diamond",
        "cross",
        "x",
        "triangle-up",
        "triangle-down",
        "triangle-left",
        "triangle-right",
        "star",
        "hexagon",
        "pentagon"
    ]

    symbol_map = {
        state: symbols[i % len(symbols)]
        for i, state in enumerate(ufs)
    }

    # Observações agrupadas por fase geopolítica.
    for phase, color in zip(phase_names, phase_colors):

        group = pairs[pairs["Fase"] == phase]

        if group.empty:
            continue

        fig.add_trace(go.Scatter(
            x=group[config.COL_BRENT],
            y=group[config.COL_PRECO],
            mode="markers",
            name=phase,

            marker=dict(
                size=7 if all_mode else 9,
                color=color,
                opacity=.85,
                symbol=[
                    symbol_map.get(u, "circle")
                    for u in group["UF"]
                ],
                line=dict(
                    width=.5,
                    color="white"
                )
            ),

            customdata=group[["UF", "Data final"]].assign(
                **{
                    "Data final":
                        group["Data final"].dt.strftime("%d/%m/%Y")
                }
            ).to_numpy(),

            hovertemplate=(
                "UF: %{customdata[0]}<br>"
                "Semana até %{customdata[1]}<br>"
                "Brent: US$ %{x:.2f}<br>"
                + fuel +
                ": R$ %{y:.2f}/l<extra></extra>"
            )
        ))

    # Linha de regressão linear.
    if regression is not None:

        xx = np.array([
            regression["x_min"],
            regression["x_max"]
        ])

        fig.add_trace(go.Scatter(
            x=xx,
            y=regression["intercept"] + regression["slope"] * xx,
            mode="lines",
            name="Regressão linear",
            line=dict(
                color=config.CORES_COMBUSTIVEIS[fuel],
                width=3
            ),
            hoverinfo="skip"
        ))

        annotation = (
            f'<b>{an.equacao(regression)}</b><br>'
            f'R² = {an.fmt(regression["r2"], 3)} · '
            f'r = {an.fmt(regression["r"], 3)}<br>'
            f'n = {regression["n"]} semanas'
        )

        fig.add_annotation(
            x=.02,
            y=.98,
            xref="paper",
            yref="paper",
            text=annotation,
            showarrow=False,
            align="left",
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,.88)",
            bordercolor="rgba(0,0,0,.3)",
            borderwidth=1,
            font=dict(
                size=12,
                color="#222"
            )
        )

    # Configurações visuais.
    label = (
        "nacional"
        if selected_uf.startswith("Brasil")
        else f"({selected_uf})"
    )

    fig.update_layout(
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=FONTE,
        separators=",.",
        margin=dict(t=30, l=10, r=10, b=10),
        hovermode="closest",
        xaxis_title="Preço do petróleo Brent (US$ por barril)",
        yaxis_title=f"{fuel} – preço médio {label} (R$/litro)",
        legend=dict(
            orientation="h",
            y=-.22,
            x=0,
            title_text=""
        )
    )

    fig.update_xaxes(
        tickprefix="US$ ",
        gridcolor="rgba(128,128,128,.2)"
    )

    fig.update_yaxes(
        tickprefix="R$ ",
        tickformat=".2f",
        gridcolor="rgba(128,128,128,.2)"
    )

    return fig
