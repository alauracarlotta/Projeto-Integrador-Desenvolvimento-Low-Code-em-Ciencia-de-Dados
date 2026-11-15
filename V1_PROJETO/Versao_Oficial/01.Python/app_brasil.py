import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dados

st.set_page_config(page_title="Combustíveis x Instabilidade Geopolítica", layout="wide")


@st.cache_data
def carregar_base():
    return dados.carregar()


base = carregar_base()
CORES = {"Gasolina Comum": "#E4572E", "Etanol Hidratado": "#2E9E5B", "Diesel S-10": "#2B59C3"}

# ---------------------------------------------------------------- Título
st.title("⛽ Preços dos Combustíveis no Brasil e a Instabilidade Geopolítica")
st.caption("Fonte: ANP – Levantamento semanal de preços de revenda (Brasil). "
           "Análise de comportamento e associação; não afirma relação de causa e efeito.")

# ---------------------------------------------------------------- Filtros
st.sidebar.header("Filtros")
data_min, data_max = base["Data final"].min().date(), base["Data final"].max().date()
periodo = st.sidebar.date_input("Período (data final da semana)", value=(data_min, data_max),
                                min_value=data_min, max_value=data_max)
if len(periodo) != 2:
    st.info("Selecione a data inicial e a final no filtro lateral.")
    st.stop()
combs = st.sidebar.multiselect("Combustíveis", list(dados.PRODUTOS.values()),
                               default=list(dados.PRODUTOS.values()))
marcos = st.sidebar.checkbox("Mostrar marcos do conflito", value=True)

df = base[(base["Data final"].dt.date >= periodo[0]) & (base["Data final"].dt.date <= periodo[1])
          & (base["Combustível"].isin(combs))]
if df.empty:
    st.warning("Nenhum dado para os filtros escolhidos.")
    st.stop()

tabela_kpi = dados.kpis(df, ref=base)
dfv = dados.com_variacao(df, ref=base)


def linha_marcos(fig):
    if marcos:
        for nome, d in dados.MARCOS.items():
            if periodo[0] <= d.date() <= periodo[1]:
                fig.add_vline(x=d, line_dash="dot", line_color="gray")
                fig.add_annotation(x=d, y=1.04, yref="paper", text=nome, showarrow=False,
                                   textangle=-30, font=dict(size=9, color="gray"))
    return fig


# ---------------------------------------------------------------- KPIs
st.subheader("Indicadores-chave")
cols = st.columns(len(tabela_kpi))
for col, (_, r) in zip(cols, tabela_kpi.iterrows()):
    with col:
        st.markdown(f"**{r['Combustível']}**")
        st.metric(f"Preço atual ({r['Semana mais recente']:%d/%m/%Y})",
                  f"R$ {r['Preço atual (R$/l)']:.2f}",
                  f"{r['Variação desde 28/02 (%)']:+.1f}% desde 28/02/2026", delta_color="inverse")
        st.caption(f"Em 28/02/2026: R$ {r['Preço em 28/02/2026']:.2f} · "
                   f"Média do período: R$ {r['Média do período (R$/l)']:.2f}")
        st.caption(f"🔺 Mais caro: R$ {r['Maior preço médio (R$/l)']:.2f} "
                   f"({r['Semana do maior preço']:%d/%m/%Y})")
        st.caption(f"🔻 Mais barato: R$ {r['Menor preço médio (R$/l)']:.2f} "
                   f"({r['Semana do menor preço']:%d/%m/%Y})")

# ---------------------------------------------------------------- Gráfico 1
st.subheader("1. Preço médio semanal de revenda (R$/litro)")
fig1 = px.line(df, x="Data final", y="Preço médio", color="Combustível",
               color_discrete_map=CORES, labels={"Preço médio": "R$/litro", "Data final": "Semana"})
fig1.update_layout(hovermode="x unified", legend_title_text="", margin=dict(t=50))
st.plotly_chart(linha_marcos(fig1), use_container_width=True)
st.caption("Não houve pesquisa da ANP entre 18/08/2020 e 17/10/2020; a linha une os pontos vizinhos.")

# ---------------------------------------------------------------- Gráfico 2
st.subheader("2. Variação acumulada desde 28/02/2026 (%)")
pos = dfv[dfv["Data final"] >= dados.DATA_BASE]
if pos.empty:
    st.info("O período selecionado não inclui datas posteriores a 28/02/2026.")
else:
    fig2 = px.line(pos, x="Data final", y="Var. desde 28/02 (%)", color="Combustível",
                   color_discrete_map=CORES, labels={"Data final": "Semana"})
    fig2.add_hline(y=0, line_color="black", line_width=1)
    fig2.update_layout(hovermode="x unified", legend_title_text="", margin=dict(t=50))
    st.plotly_chart(linha_marcos(fig2), use_container_width=True)

# ---------------------------------------------------------------- Gráficos 3 e 4
c1, c2 = st.columns(2)
with c1:
    st.subheader("3. Preço médio por ano (R$/l)")
    anual = df.assign(Ano=df["Data final"].dt.year).groupby(["Ano", "Combustível"],
                                                             as_index=False)["Preço médio"].mean()
    fig3 = px.bar(anual, x="Ano", y="Preço médio", color="Combustível", barmode="group",
                  color_discrete_map=CORES, text_auto=".2f")
    fig3.update_layout(legend_title_text="", yaxis_title="R$/litro")
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("2026 inclui apenas as semanas até a data mais recente da base.")

with c2:
    st.subheader("4. Variação semanal (%)")
    comb_sel = st.selectbox("Combustível", combs, key="var_semanal")
    x = dfv[dfv["Combustível"] == comb_sel].dropna(subset=["Variação semanal (%)"])
    fig4 = px.bar(x, x="Data final", y="Variação semanal (%)",
                  color_discrete_sequence=[CORES[comb_sel]], labels={"Data final": "Semana"})
    st.plotly_chart(linha_marcos(fig4), use_container_width=True)
    st.caption("A primeira semana após a pausa de 2020 mostra a variação acumulada de cerca de 10 semanas sem coleta.")

# ---------------------------------------------------------------- Dispersão entre postos
st.subheader("5. Mais caro × mais barato entre postos (semana mais recente)")
ult = df[df["Data final"] == df["Data final"].max()].copy()
fig5 = go.Figure()
for _, r in ult.iterrows():
    fig5.add_trace(go.Scatter(x=[r["Preço mínimo (posto)"], r["Preço médio"], r["Preço máximo (posto)"]],
                              y=[r["Combustível"]] * 3, mode="lines+markers+text",
                              text=[f"R$ {r['Preço mínimo (posto)']:.2f}", f"R$ {r['Preço médio']:.2f}",
                                    f"R$ {r['Preço máximo (posto)']:.2f}"],
                              textposition="top center", name=r["Combustível"],
                              line=dict(color=CORES[r["Combustível"]])))
fig5.update_layout(showlegend=False, xaxis_title="R$/litro (mínimo – média – máximo)")
st.plotly_chart(fig5, use_container_width=True)
st.caption("A base utilizada é nacional: o extremo aqui é o posto mais caro/barato, não o estado ou a região. "
           "Para ranking por estado/região, é necessário o arquivo semanal por estados da ANP.")

# ---------------------------------------------------------------- Tabelas
with st.expander("Ver tabela de indicadores e dados"):
    st.dataframe(tabela_kpi.round(2), use_container_width=True)
    st.dataframe(dfv.round(2), use_container_width=True)
    st.download_button("Baixar dados tratados (CSV)",
                       dfv.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       "dados_tratados.csv", "text/csv")
