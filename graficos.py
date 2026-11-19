"""Construção das figuras Plotly (sem lógica de Streamlit)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import analises as an
import config

FONTE = dict(family="Inter, Segoe UI, Arial, sans-serif", size=13)


def _base(fig: go.Figure, ytitle: str, altura: int = 430, legenda_abaixo: bool = True) -> go.Figure:
    fig.update_layout(
        height=altura, font=FONTE, separators=",.", margin=dict(t=30, l=10, r=10, b=10),
        hovermode="x unified", yaxis_title=ytitle, xaxis_title="Semana (data final)",
        legend=dict(orientation="h", y=-0.22 if legenda_abaixo else 1.08, x=0, title_text=""),
    )
    fig.update_xaxes(hoverformat="%d/%m/%Y", tickformat="%b/%y", showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


def adicionar_marcos(fig: go.Figure, inicio: pd.Timestamp, fim: pd.Timestamp, visivel: bool = True) -> go.Figure:
    """Linhas verticais dos marcos geopolíticos (só os que caem no intervalo exibido) + entradas na legenda."""
    if not visivel:
        return fig
    for m in config.MARCOS:
        if not (inicio <= m["data"] <= fim):
            continue
        x = m["data"].strftime("%Y-%m-%d")
        fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, xref="x", yref="paper", layer="below",
                      line=dict(color=m["cor"], dash=m["dash"], width=1.6))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", hoverinfo="skip",
                                 line=dict(color=m["cor"], dash=m["dash"], width=2),
                                 name=f"{m['data']:%d/%m/%Y} · {m['descricao']}"))
    return fig


# ---------------------------------------------------------------- Gráfico 1
def grafico_brasil(df: pd.DataFrame, marcos: bool, inicio, fim) -> go.Figure:
    fig = go.Figure()
    for comb in config.ORDEM_COMBUSTIVEIS:
        d = df[df["Combustível"] == comb].sort_values("Data final")
        if d.empty:
            continue
        fig.add_trace(go.Scatter(x=d["Data final"], y=d["Preço médio"], mode="lines+markers", name=comb,
                                 line=dict(color=config.CORES_COMBUSTIVEIS[comb], width=2.5),
                                 marker=dict(size=5), hovertemplate="R$ %{y:.2f}/l"))
    _base(fig, "Preço médio de revenda (R$/litro)")
    fig.update_yaxes(tickprefix="R$ ", tickformat=".2f")
    return adicionar_marcos(fig, inicio, fim, marcos)


# ---------------------------------------------------------------- Gráfico 2.1
def grafico_regioes(reg: pd.DataFrame, comb: str, marcos: bool, inicio, fim) -> go.Figure:
    fig = go.Figure()
    for r in config.ORDEM_REGIOES:
        d = reg[reg["Região"] == r].sort_values("Data final")
        if d.empty:
            continue
        fig.add_trace(go.Scatter(x=d["Data final"], y=d["Preço médio"], mode="lines", name=r,
                                 line=dict(color=config.CORES_REGIOES[r], width=2.3),
                                 hovertemplate="R$ %{y:.2f}/l"))
    _base(fig, f"{comb} – preço médio regional (R$/litro)", altura=470)
    fig.update_yaxes(tickprefix="R$ ", tickformat=".2f")
    return adicionar_marcos(fig, inicio, fim, marcos)


# ---------------------------------------------------------------- Gráfico 2.2
def grafico_ranking(top: pd.DataFrame, comb: str) -> go.Figure:
    ordem = list(top["Estado"])               # caros (decrescente) e depois baratos (crescente)
    cores = {"Mais caros": "#C0392B", "Mais baratos": "#1E8449"}
    fig = go.Figure()
    for grupo in ["Mais caros", "Mais baratos"]:
        d = top[top["Grupo"] == grupo]
        fig.add_trace(go.Bar(
            x=d["Preço médio"], y=d["Estado"], orientation="h", name=grupo, marker_color=cores[grupo],
            text=[an.brl(v) for v in d["Preço médio"]], textposition="outside", cliponaxis=False,
            customdata=d["Região"], hovertemplate="%{y} (%{customdata}): R$ %{x:.2f}/l<extra></extra>"))
    fig.update_layout(height=470, font=FONTE, separators=",.", margin=dict(t=30, l=10, r=60, b=10),
                      xaxis_title=f"{comb} – preço médio no mês (R$/litro)", yaxis_title="", bargap=0.35,
                      legend=dict(orientation="h", y=-0.22, x=0, title_text=""))
    fig.update_yaxes(categoryorder="array", categoryarray=ordem, autorange="reversed")
    fig.update_xaxes(range=[0, float(top["Preço médio"].max()) * 1.15], tickprefix="R$ ", tickformat=".2f",
                     gridcolor="rgba(128,128,128,0.2)")
    return fig


# ---------------------------------------------------------------- Gráfico 3
def grafico_brent(brent: pd.DataFrame, marcos: bool, inicio, fim) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=brent["Data"], y=brent[config.COL_BRENT], mode="lines+markers",
                             name="Petróleo Brent (US$/barril)", line=dict(color="#1B1B1B", width=2.5),
                             marker=dict(size=5), hovertemplate="US$ %{y:.2f}/barril"))
    _base(fig, "Brent – preço spot (US$ por barril)")
    fig.update_xaxes(title_text="Semana (data da cotação)")
    fig.update_yaxes(tickprefix="US$ ", tickformat=".0f")
    return adicionar_marcos(fig, inicio, fim, marcos)


# ---------------------------------------------------------------- Gráfico 4
def grafico_dispersao(d: pd.DataFrame, res: dict, comb: str) -> go.Figure:
    """d: observações semanais pareadas do combustível escolhido (colunas Brent, Preço médio, Data Brent)."""
    fases, ordem_fases = an.fases_conflito(d["Data Brent"])
    paleta = ["#7F8C8D", "#6A1B9A", "#BF360C", "#263238"]
    fig = go.Figure()
    for rot, cor in zip(ordem_fases, paleta):
        sel = fases == rot
        if not sel.any():
            continue
        dd = d[sel]
        fig.add_trace(go.Scatter(
            x=dd[config.COL_BRENT], y=dd["Preço médio"], mode="markers", name=rot,
            marker=dict(size=9, color=cor, opacity=0.85, line=dict(width=0.5, color="white")),
            customdata=dd["Data final"].dt.strftime("%d/%m/%Y"),
            hovertemplate="Semana até %{customdata}<br>Brent: US$ %{x:.2f}<br>"
                          f"{comb}: R$ %{{y:.2f}}/l<extra></extra>"))
    if res is not None:
        xs = np.array([res["x_min"], res["x_max"]])
        fig.add_trace(go.Scatter(x=xs, y=res["intercept"] + res["slope"] * xs, mode="lines",
                                 name="Regressão linear", line=dict(color=config.CORES_COMBUSTIVEIS[comb],
                                                                     width=3, dash="solid"),
                                 hoverinfo="skip"))
        texto = (f"<b>{an.equacao(res)}</b><br>R² = {an.fmt(res['r2'], 3)} · r = {an.fmt(res['r'], 3)}<br>"
                 f"n = {res['n']} semanas")
        fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper", text=texto, showarrow=False,
                           align="left", xanchor="left", yanchor="top", bgcolor="rgba(255,255,255,0.88)",
                           bordercolor="rgba(0,0,0,0.3)", borderwidth=1, font=dict(size=12, color="#222"))
    fig.update_layout(height=500, font=FONTE, separators=",.", margin=dict(t=30, l=10, r=10, b=10),
                      xaxis_title="Preço do petróleo Brent (US$ por barril)",
                      yaxis_title=f"{comb} – preço médio nacional (R$/litro)", hovermode="closest",
                      legend=dict(orientation="h", y=-0.22, x=0, title_text=""))
    fig.update_xaxes(tickprefix="US$ ", gridcolor="rgba(128,128,128,0.2)")
    fig.update_yaxes(tickprefix="R$ ", tickformat=".2f", gridcolor="rgba(128,128,128,0.2)")
    return fig
