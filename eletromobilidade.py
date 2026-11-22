from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import linregress

PASTA_BASES = Path(__file__).resolve().parent / "data" / "processed"

ARQUIVO_ELETRICOS = PASTA_BASES / "Base_Mensal_Eletricos_2026.csv"
ARQUIVO_BRENT = PASTA_BASES / "Base_Brent_Weekly_2026_Tratada.csv"

COL_BRENT = "Weekly Europe Brent Spot Price FOB  (Dollars per Barrel)"


def integrar_bases():
    """Integra os emplacamentos mensais à média mensal do Brent."""

    # 1. Carregamento das bases.
    eletricos = pd.read_csv(ARQUIVO_ELETRICOS)
    brent = pd.read_csv(ARQUIVO_BRENT)

    # 2. Padronização das datas do Brent.
    meses = {
        "jan": "01", "fev": "02", "mar": "03",
        "abr": "04", "mai": "05", "jun": "06",
        "jul": "07", "ago": "08", "set": "09",
        "out": "10", "nov": "11", "dez": "12"
    }

    partes = brent["Date"].str.lower().str.split(expand=True)

    brent["Data"] = pd.to_datetime(
        brent["Ano"].astype(str)
        + "-"
        + partes[0].map(meses)
        + "-"
        + partes[1],
        format="%Y-%m-%d"
    )

    # Validação das datas convertidas.
    if brent["Data"].isna().any():
        raise ValueError(
            "Foram encontradas datas inválidas na base do Brent."
        )

    brent["Mes"] = brent["Data"].dt.strftime("%Y-%m")

    # 3. Conversão dos preços para valores numéricos.
    brent[COL_BRENT] = pd.to_numeric(brent[COL_BRENT])

    # 4. Agregação dos preços semanais por mês.
    brent_mensal = (
        brent.groupby("Mes", as_index=False)
        .agg(Brent_Medio=(COL_BRENT, "mean"))
    )

    # 5. Integração pelo mês de referência.
    base = eletricos.merge(
        brent_mensal,
        on="Mes",
        how="left",
        validate="one_to_one"
    ).sort_values("Mes").reset_index(drop=True)

    # 6. Validação da integração.
    meses_esperados = pd.period_range(
        "2026-01", "2026-09", freq="M"
    ).astype(str).tolist()

    if base["Mes"].tolist() != meses_esperados:
        raise ValueError("Cobertura mensal inválida.")

    if base["Brent_Medio"].isna().any():
        raise ValueError("Existem meses sem preço médio do Brent.")

    # 7. Cálculo das variações percentuais mensais.
    base["Variacao_Brent"] = (
        base["Brent_Medio"].pct_change() * 100
    )

    base["Variacao_Eletricos"] = (
        base["Emplacamentos_Eletricos"].pct_change() * 100
    )

    return base

def analisar_correlacao(base):
    """Calcula as métricas da regressão linear."""

    pares = base.dropna(
        subset=["Variacao_Brent", "Variacao_Eletricos"]
    )

    resultado = linregress(
        pares["Variacao_Brent"],
        pares["Variacao_Eletricos"]
    )

    return {
        "pearson": resultado.rvalue,
        "r2": resultado.rvalue ** 2,
        "coeficiente_angular": resultado.slope,
        "intercepto": resultado.intercept,
        "p_valor": resultado.pvalue,
        "n": len(pares)
    }

def grafico_eletromobilidade(base, metricas):
    """Gera o gráfico de associação entre Brent e elétricos."""

    pares = base.dropna(
        subset=["Variacao_Brent", "Variacao_Eletricos"]
    ).copy()

    pares["Mes_Label"] = (
        pares["Mes"].str[5:7].map({
            "01": "JAN", "02": "FEV", "03": "MAR",
            "04": "ABR", "05": "MAI", "06": "JUN",
            "07": "JUL", "08": "AGO", "09": "SET"
        })
    )

    x = pares["Variacao_Brent"]
    y = pares["Variacao_Eletricos"]

    fig = go.Figure()

    # 1. Pontos de dispersão.
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers+text",
        text=pares["Mes_Label"],
        textposition="top center",
        name="Observações mensais",
        marker=dict(
            size=12,
            color="#29D87C"
        ),
        customdata=pares[
            ["Mes", "Emplacamentos_Eletricos", "Brent_Medio"]
        ].to_numpy(),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Emplacamentos: %{customdata[1]:,.0f}<br>"
            "Brent médio: US$ %{customdata[2]:.2f}<br>"
            "Variação Brent: %{x:.2f}%<br>"
            "Variação elétricos: %{y:.2f}%"
            "<extra></extra>"
        )
    ))

    # 2. Reta de regressão linear.
    x_reta = [x.min(), x.max()]

    y_reta = [
        metricas["coeficiente_angular"] * valor
        + metricas["intercepto"]
        for valor in x_reta
    ]

    fig.add_trace(go.Scatter(
        x=x_reta,
        y=y_reta,
        mode="lines",
        name="Regressão linear",
        line=dict(
            color="#57C9FF",
            dash="dash",
            width=2
        ),
        hoverinfo="skip"
    ))

    # 3. Linhas de referência para variação zero.
    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="gray"
    )

    fig.add_vline(
        x=0,
        line_dash="dot",
        line_color="gray"
    )

    # 4. Configuração visual.
    fig.update_layout(
        xaxis_title="Variação mensal do Brent (%)",
        yaxis_title="Variação mensal dos emplacamentos (%)",
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        separators=",.",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=20, r=20, t=30, b=90)
    )

    fig.update_xaxes(ticksuffix="%")
    fig.update_yaxes(ticksuffix="%")

    return fig

def renderizar_eletromobilidade():
    """Renderiza a análise complementar no dashboard."""

    with st.expander(
        "ϟ Análise complementar: Brent × eletromobilidade",
        expanded=False
    ):
        st.markdown(
            "Associação entre as variações mensais do "
            "preço do petróleo Brent e dos emplacamentos "
            "de automóveis elétricos no Brasil."
        )

        try:
            base = integrar_bases()
            metricas = analisar_correlacao(base)

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Pearson (r)",
                f"{metricas['pearson']:.4f}".replace(".", ",")
            )

            col2.metric(
                "R²",
                f"{metricas['r2']:.2%}".replace(".", ",")
            )

            col3.metric(
                "Observações",
                metricas["n"]
            )

            fig = grafico_eletromobilidade(base, metricas)

            st.plotly_chart(
                fig,
                use_container_width=True,
                theme="streamlit",
                key="grafico_eletromobilidade"
            )

            st.caption(
                "Fontes: "
                "[Fenabrave](https://www.fenabrave.org.br/portalv2/Conteudo/Emplacamentos) e "
                "[EIA](https://www.eia.gov/dnav/pet/hist/RBRTEw.htm). "
                "Abrangência: Brasil. "
                "Período: janeiro a setembro de 2026. "
                "Variações mensais: fevereiro a setembro. "
                "Análise independente dos filtros globais."
            )

            st.info(
                "Análise exploratória com amostra reduzida. "
                "A associação observada não apresentou "
                "significância estatística ao nível de 5% "
                f"(p = {metricas['p_valor']:.4f}) "
                "e não permite estabelecer causalidade."
            )
            
            # Download da base mensal integrada.
            st.download_button(
                label="⇩ Baixar dados mensais (CSV)",
                data=base.to_csv(
                    index=False,
                    sep=";",
                    decimal=","
                ).encode("utf-8-sig"),
                file_name="brent_eletromobilidade_2026.csv",
                mime="text/csv",
                key="download_eletromobilidade"
            )

        except (OSError, ValueError, KeyError) as erro:
            st.warning(
                f"Análise complementar indisponível: {erro}"
            )

if __name__ == "__main__":
    base = integrar_bases()

    print("\nBASE INTEGRADA:")
    print(base.round(2).to_string(index=False))

    print(f"\nTotal de meses: {len(base)}")

    metricas = analisar_correlacao(base)

    print("\nMÉTRICAS ESTATÍSTICAS:")
    print(f"Pearson (r): {metricas['pearson']:.4f}")
    print(f"R²: {metricas['r2']:.4f}")
    print(f"Coeficiente angular: {metricas['coeficiente_angular']:.4f}")
    print(f"Intercepto: {metricas['intercepto']:.4f}")
    print(f"p-valor: {metricas['p_valor']:.4f}")
    print(f"Observações (n): {metricas['n']}")
	
    fig = grafico_eletromobilidade(base, metricas)
    fig.show()
