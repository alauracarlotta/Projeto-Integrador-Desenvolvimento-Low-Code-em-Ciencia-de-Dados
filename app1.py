"""Apresentação integrada do Projeto Integrador: combustíveis no Brasil × petróleo Brent."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
MODULE_DIR = ROOT / "V1_PROJETO" / "Versao_Oficial" / "01.Python" / "15_11_2026"
DATA_DIR = ROOT / "V1_PROJETO" / "Versao_Oficial" / "00.Bases" / "01.Tratadas"
sys.path.insert(0, str(MODULE_DIR))

import analises as an
import carregamento as cg
import config
import graficos as gr

st.set_page_config(page_title="Combustíveis no Brasil × Brent", page_icon="⛽", layout="wide")

st.markdown("""
<style>
:root { --bg:#100f13; --panel:#1b1820; --panel2:#232029; --border:#4e4657; --text:#f5f1f8; --muted:#bfb6c7; }
.stApp { background:var(--bg); color:var(--text); }
.block-container { max-width:1600px; padding:0.65rem 1.25rem 0.8rem; }
header[data-testid="stHeader"] { background:transparent; }
.dashboard-title { background:#241a2a; border:1px solid #55465e; border-radius:10px; margin-bottom:8px; padding:10px 16px; }
.dashboard-title h1 { font-size:30px !important; margin:0; line-height:1.05; }
.dashboard-title p { margin:3px 0 0; color:#bfb6c7; font-size:13px; }
.topnav { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:6px 0 8px; }
.navcard { background:#211e26; border:1px solid #514759; border-radius:8px; padding:8px 11px; min-height:54px; }
.navcard b { color:#f8f5fa; }
.navcard span { display:block; color:#aaa0b3; font-size:12px; margin-top:3px; }
[data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(120deg,#1d1a21,#17151a); border:1px solid #4c4452 !important; border-radius:10px; }
[data-testid="stMetric"] { background:#24212a; border:1px solid #514858; border-radius:9px; }
[data-testid="stMetricValue"] { font-size:24px; color:#fff; }
[data-testid="stWidgetLabel"], .stCaption, [data-testid="stCaptionContainer"] { color:#d1c7d8; }
[data-baseweb="select"] > div { background:#292530; color:white; }
.stButton button { background:#292430; color:#fff; border-color:#745d81; }
section[data-testid="stSidebar"] { background:#17141b; border-right:1px solid #403847; }
h2 { font-size:20px !important; margin-top:8px !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Lendo e validando as bases...")
def carregar():
    brasil, av_b = cg.carregar_brasil(DATA_DIR)
    estados, av_e = cg.carregar_estados(DATA_DIR)
    brent, av_o = cg.carregar_brent(DATA_DIR)
    alinhado, descartadas = an.alinhar_semanas(brasil, brent)
    return brasil, estados, brent, alinhado, av_b + av_e + av_o, descartadas


brasil, estados, brent, alinhado, avisos, descartadas = carregar()

# ---------------------------------------------------------------- cabeçalho
top_left, top_right = st.columns([8.5, 1.5])
with top_left:
    st.markdown("""<div class="dashboard-title"><h1>⛽ Instabilidade geopolítica e os preços dos combustíveis no Brasil</h1>
    <p>Preços semanais de revenda por UF e petróleo Brent · Projeto Integrador SENAC</p></div>""", unsafe_allow_html=True)
with top_right:
    st.caption("Projeto Integrador")
    st.caption("SENAC · 2026")

st.markdown("""
<div class="topnav">
  <div class="navcard"><b>1. Cenário nacional</b><span>Como os preços evoluíram?</span></div>
  <div class="navcard"><b>2. Diferenças regionais</b><span>O comportamento é uniforme?</span></div>
  <div class="navcard"><b>3. Cenário internacional</b><span>Como o Brent se comportou?</span></div>
  <div class="navcard"><b>4. Relação estatística</b><span>Há associação com o Brent?</span></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
d_min = min(brasil["Data final"].min(), estados["Data final"].min(), brent["Data"].min())
d_max = max(brasil["Data final"].max(), estados["Data final"].max(), brent["Data"].max())
periodo = st.sidebar.date_input("Período", value=(d_min, d_max), min_value=d_min, max_value=d_max, format="DD/MM/YYYY")
if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.info("Selecione a data inicial e a data final.")
    st.stop()
ini, fim = pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1])
marcos = st.sidebar.checkbox("Mostrar marcos geopolíticos", value=True)
combustivel = st.sidebar.selectbox("Combustível regional", config.ORDEM_COMBUSTIVEIS, index=0)

st.sidebar.markdown("**Qualidade e alinhamento**")
st.sidebar.caption(f"Pasta das bases: `{DATA_DIR.relative_to(ROOT)}`")
if avisos:
    for aviso in avisos:
        st.sidebar.warning(aviso)
else:
    st.sidebar.success("Nenhum valor nulo, duplicado ou inconsistente encontrado.")
st.sidebar.caption(f"Brasil: {brasil['Data final'].nunique()} semanas · Estados: {estados['Estado'].nunique()} UFs · Brent: {len(brent)} semanas")

br_f = brasil[(brasil["Data final"] >= ini) & (brasil["Data final"] <= fim)]
es_f = estados[(estados["Data final"] >= ini) & (estados["Data final"] <= fim)]
bt_f = brent[(brent["Data"] >= ini) & (brent["Data"] <= fim)]
al_f = alinhado[(alinhado["Data Brent"] >= ini) & (alinhado["Data Brent"] <= fim)]

# ---------------------------------------------------------------- indicadores
with st.container(border=True):
    st.subheader("▥ Indicadores-chave (Brasil)")
    if br_f.empty:
        st.info("Nenhum dado nacional no período selecionado.")
    else:
        kp = an.kpis(br_f, ref=brasil)
        cols = st.columns(len(kp))
        for col, (_, r) in zip(cols, kp.iterrows()):
            variacao = r["Variação desde 28/02 (%)"]
            col.metric(r["Combustível"], f"R$ {r['Preço atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                       f"{an.fmt_sinal(variacao, 2)}% desde 28/02", delta_color="inverse")

# ---------------------------------------------------------------- seção 1
with st.container(border=True):
    st.subheader("1. Cenário nacional: evolução semanal dos preços")
    if br_f.empty:
        st.info("Nenhum dado de preços do Brasil no período selecionado.")
    else:
        st.plotly_chart(gr.grafico_brasil(br_f, marcos, ini, fim), width="stretch")

# ---------------------------------------------------------------- seção 2
with st.container(border=True):
    st.subheader("2. Diferenças regionais e ranking dos estados")
    left, right = st.columns([1.55, 1])
    with left:
        st.markdown("**2.1 Evolução por região**")
        reg = an.preco_por_regiao(es_f, combustivel)
        if reg.empty:
            st.info("Sem dados regionais no período selecionado.")
        else:
            st.plotly_chart(gr.grafico_regioes(reg, combustivel, marcos, ini, fim), width="stretch")
    with right:
        mes, semanas_mes, completo, top6 = an.ranking_ultimo_mes(estados, combustivel)
        st.markdown(f"**2.2 Três mais baratos e caros — {an.rotulo_mes(mes)}**")
        if top6 is None:
            st.warning("Não há estados suficientes para montar o ranking.")
        else:
            st.plotly_chart(gr.grafico_ranking(top6, combustivel), width="stretch")

# ---------------------------------------------------------------- seção 3
with st.container(border=True):
    st.subheader("3. Cenário internacional: petróleo Brent")
    if bt_f.empty:
        st.info("Nenhuma cotação do Brent no período selecionado.")
    else:
        m1, m2 = st.columns(2)
        ultima = bt_f.iloc[-1]
        m1.metric("Última cotação", f"US$ {ultima[config.COL_BRENT]:,.2f}".replace(".", ",").replace(",", ".", 1))
        base = bt_f.iloc[0][config.COL_BRENT]
        variacao = (ultima[config.COL_BRENT] / base - 1) * 100
        m2.metric("Variação no período", f"{variacao:+.2f}%".replace(".", ","), delta_color="off")
        st.plotly_chart(gr.grafico_brent(bt_f, marcos, ini, fim), width="stretch")

# ---------------------------------------------------------------- seção 4
with st.container(border=True):
    st.subheader("4. Relação estatística: Brent × preços dos combustíveis")
    comb4 = st.selectbox("Combustível da associação", config.ORDEM_COMBUSTIVEIS, index=0)
    if al_f.empty:
        st.info("Nenhuma semana com dados válidos nas duas bases no período selecionado.")
    else:
        resultados = an.regressoes(al_f)
        res = resultados[comb4]
        d4 = al_f[al_f["Combustível"] == comb4]
        if res is None:
            st.warning("Observações insuficientes para estimar a regressão.")
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Coef. angular", f"{res['slope']:.4f} R$/l por US$ 1")
            c2.metric("Intercepto", f"{res['intercept']:.3f} R$/l")
            c3.metric("R²", f"{res['r2']:.3f}")
            c4.metric("Correlação de Pearson", f"{res['r']:.3f}")
            c5.metric("Semanas pareadas", str(res["n"]))
        st.plotly_chart(gr.grafico_dispersao(d4, res, comb4), width="stretch")

with st.expander("▣ Metodologia e fontes"):
    st.markdown("**Fontes:** ANP, para os preços semanais de revenda no Brasil e nos estados, e EIA, para o petróleo Brent. "
                "Os arquivos são lidos exclusivamente da pasta `V1_PROJETO/Versao_Oficial/00.Bases/01.Tratadas`.")
    st.markdown("A associação usa apenas semanas válidas nas duas bases. A cotação do Brent é associada à semana ANP que a contém; "
                "não há interpolação, preenchimento ou afirmação de causalidade.")
