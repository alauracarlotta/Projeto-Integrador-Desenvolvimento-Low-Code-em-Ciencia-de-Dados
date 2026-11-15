"""Dashboard integrado – Combustíveis no Brasil × petróleo Brent (2026).

Consolida app_brasil.py (visão nacional, KPIs, marcos) e app_brasil_regiao.py (regiões e estados)
e acrescenta a análise com o Brent. Como rodar, nesta pasta:

    pip install streamlit plotly pandas numpy      (scipy é opcional: só para o p-valor)
    streamlit run app_dashboard.py

Os CSVs tratados são procurados em config.pasta_bases() (veja config.py; também aceita a
variável de ambiente PI_BASES_DIR).
"""
from __future__ import annotations

import inspect
import importlib

import pandas as pd
import streamlit as st

import analises as an
import carregamento as cg
import config
import graficos as gr

st.set_page_config(page_title="Combustíveis × Petróleo Brent – 2026", page_icon="⛽", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1400px;}
h2 {border-bottom: 2px solid rgba(128,128,128,.25); padding-bottom: .3rem; margin-top: 2.2rem;}
div[data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
""", unsafe_allow_html=True)

# compatibilidade entre versões do Streamlit (use_container_width x width="stretch")
_PLOT_W = "width" in inspect.signature(st.plotly_chart).parameters
_DF_W = "width" in inspect.signature(st.dataframe).parameters


def mostrar(fig) -> None:
    st.plotly_chart(fig, **({"width": "stretch"} if _PLOT_W else {"use_container_width": True}))


def tabela(df: pd.DataFrame) -> None:
    st.dataframe(df, hide_index=True, **({"width": "stretch"} if _DF_W else {"use_container_width": True}))


def csv_br(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


# ================================================================ carga (cacheada)
@st.cache_data(show_spinner="Lendo e validando as bases...")
def preparar(pasta: str):
    brasil, a1 = cg.carregar_brasil(pasta)
    estados, a2 = cg.carregar_estados(pasta)
    brent, a3 = cg.carregar_brent(pasta)
    alin, descartadas = an.alinhar_semanas(brasil, brent)
    return {"brasil": brasil, "estados": estados, "brent": brent, "alinhado": alin,
            "descartadas": descartadas, "avisos": a1 + a2 + a3}


pasta = config.pasta_bases()
if pasta is None:
    # O Streamlit pode manter o módulo importado antes da correção dos caminhos.
    # Atualize a configuração em disco antes de declarar as bases ausentes.
    importlib.invalidate_caches()
    importlib.reload(config)
    pasta = config.pasta_bases()
if pasta is None:
    st.error("Não encontrei as três bases tratadas. Procurei em:")
    st.code("\n".join(str(p) for p in config.pastas_candidatas()) + "\n\nArquivos esperados:\n"
            + "\n".join(config.ARQUIVOS))
    st.info("Coloque os três CSVs tratados em `V1_PROJETO/Versao_Oficial/00.Bases/01.Tratadas` "
            "ou defina a variável de ambiente `PI_BASES_DIR` com a pasta que contém esses arquivos.")
    st.stop()
try:
    D = preparar(str(pasta))
except cg.ErroDados as e:
    st.error(f"Erro ao carregar as bases: {e}")
    st.stop()
except Exception as e:  # inconsistência inesperada
    st.error(f"Erro inesperado no tratamento das bases: {type(e).__name__}: {e}")
    st.stop()
brasil, estados, brent, alinhado = D["brasil"], D["estados"], D["brent"], D["alinhado"]

# ================================================================ barra lateral
st.sidebar.header("Filtros")
d_min = min(brasil["Data final"].min(), estados["Data final"].min(), brent["Data"].min()).date()
d_max = max(brasil["Data final"].max(), estados["Data final"].max(), brent["Data"].max()).date()
periodo = st.sidebar.date_input("Período (data final da semana / data da cotação)", value=(d_min, d_max),
                                min_value=d_min, max_value=d_max, format="DD/MM/YYYY")
if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.info("Selecione a data inicial e a final no filtro lateral.")
    st.stop()
ini, fim = pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1])
marcos = st.sidebar.checkbox("Mostrar marcos geopolíticos", value=True)

st.sidebar.markdown("**Marcos geopolíticos**")
for m in config.MARCOS:
    st.sidebar.markdown(
        f"<span style='color:{m['cor']};font-weight:700'>┆</span> **{m['data']:%d/%m/%Y}** – {m['descricao']}",
        unsafe_allow_html=True)

with st.sidebar.expander("Qualidade e alinhamento dos dados"):
    st.caption(f"Pasta das bases: `{pasta}`")
    if D["avisos"]:
        for a in D["avisos"]:
            st.warning(a)
    else:
        st.success("Nenhum valor nulo, duplicado ou inconsistente encontrado nas três bases.")
    st.caption(
        f"Brasil: {brasil['Data final'].nunique()} semanas · Estados: {estados['Estado'].nunique()} UFs · "
        f"Brent: {len(brent)} semanas. Brent × Brasil: {alinhado['Data final'].nunique()} semanas pareadas.")
    if D["descartadas"]:
        st.caption("Semanas do Brent sem semana ANP correspondente (não usadas no gráfico 4): "
                   + ", ".join(d.strftime("%d/%m") for d in D["descartadas"]) + ".")

# recortes pelo período
br_f = brasil[(brasil["Data final"] >= ini) & (brasil["Data final"] <= fim)]
es_f = estados[(estados["Data final"] >= ini) & (estados["Data final"] <= fim)]
bt_f = brent[(brent["Data"] >= ini) & (brent["Data"] <= fim)]
al_f = alinhado[(alinhado["Data Brent"] >= ini) & (alinhado["Data Brent"] <= fim)]

# ================================================================ cabeçalho
st.title("⛽ Combustíveis no Brasil e o petróleo Brent em 2026")
st.caption("Fontes: ANP (levantamento semanal de preços de revenda, Brasil e estados) · Brent: Europe Brent Spot "
           "Price FOB, semanal (US$/barril). Análise descritiva de associação; não afirma relação de causa e efeito.")
c1, c2, c3, c4 = st.columns(4)
c1.markdown("**1. Cenário nacional**  \nComo os preços evoluíram?")
c2.markdown("**2. Diferenças regionais**  \nO comportamento é uniforme?")
c3.markdown("**3. Cenário internacional**  \nComo o Brent se comportou?")
c4.markdown("**4. Relação estatística**  \nHá associação com o Brent?")

# ================================================================ 1. Brasil
st.header("1. Cenário nacional")
if br_f.empty:
    st.warning("Nenhum dado de preços do Brasil no período selecionado.")
else:
    kp = an.kpis(br_f, ref=brasil)
    cols = st.columns(len(kp))
    for col, (_, r) in zip(cols, kp.iterrows()):
        with col:
            st.markdown(f"**{r['Combustível']}**")
            st.metric(f"Preço atual ({r['Semana mais recente']:%d/%m/%Y})", an.brl(r["Preço atual"]),
                      f"{an.fmt_sinal(r['Variação desde 28/02 (%)'], 1)}% desde 28/02/2026"
                      if r["Variação desde 28/02 (%)"] == r["Variação desde 28/02 (%)"] else None,
                      delta_color="inverse")
            st.caption(f"Em 28/02/2026: {an.brl(r['Preço em 28/02'])} · Média do período: {an.brl(r['Média do período'])}")
            st.caption(f"🔺 Mais caro: {an.brl(r['Maior preço'])} ({r['Semana do maior']:%d/%m/%Y}) · "
                       f"🔻 Mais barato: {an.brl(r['Menor preço'])} ({r['Semana do menor']:%d/%m/%Y})")
    mostrar(gr.grafico_brasil(br_f, marcos, ini, fim))
    st.markdown(f"_{config.TXT_G1}_")
st.info(f"**Pergunta investigativa:** {config.PERGUNTA_G1}")

# ================================================================ 2. Regiões e estados
st.header("2. Diferenças regionais e ranking dos estados")
comb2 = st.selectbox("Combustível", config.ORDEM_COMBUSTIVEIS, index=0, key="comb_g2",
                     help="Atualiza a evolução por região e o ranking de estados.")
esq, dire = st.columns([3, 2])
with esq:
    st.subheader("2.1 Evolução do preço médio por região")
    reg = an.preco_por_regiao(es_f, comb2)
    if reg.empty:
        st.warning("Sem dados de estados no período selecionado.")
    else:
        mostrar(gr.grafico_regioes(reg, comb2, marcos, ini, fim))
        st.caption("Cada ponto é a média simples dos preços médios semanais dos estados da região com dado "
                   "válido na semana (sem ponderar pelo número de postos).")
with dire:
    mes, semanas_mes, rk_todos, top6 = an.ranking_ultimo_mes(estados, comb2)
    st.subheader(f"2.2 Três mais baratos e três mais caros – {an.rotulo_mes(mes)}")
    if top6 is None:
        st.warning("Há menos de 6 estados com dados no último mês da base; ranking indisponível.")
    else:
        mostrar(gr.grafico_ranking(top6, comb2))
        st.caption(f"Preço de cada estado = média dos preços médios semanais das {len(semanas_mes)} semanas "
                   f"iniciadas em {an.rotulo_mes(mes)} ({pd.Timestamp(semanas_mes[0]):%d/%m} a "
                   f"{pd.Timestamp(semanas_mes[-1]):%d/%m}), com {len(rk_todos)} estados com dados. "
                   "Estados com poucos postos pesquisados (ex.: Amapá, Roraima) têm médias mais voláteis. "
                   "O ranking usa o último mês da base, independentemente do filtro de período.")
st.markdown(f"_{config.TXT_G2}_")

with st.expander("Aprofundamento: variação por estado desde 28/02/2026 e tabela do ranking"):
    ult = estados["Data final"].max()
    var = an.variacao_por_estado(estados, comb2, config.DATA_BASE, ult)
    if var.empty:
        st.info("Sem dados para calcular a variação.")
    else:
        st.markdown(f"**{comb2}: variação do preço médio entre 28/02/2026 e {ult:%d/%m/%Y}**")
        v = var.copy()
        v.columns = ["Estado", "Preço em 28/02 (R$/l)", f"Preço em {ult:%d/%m} (R$/l)", "Variação (R$/l)", "Variação (%)"]
        tabela(v.round(2))
    st.markdown(f"**Ranking completo de {an.rotulo_mes(mes)} – {comb2}**")
    tabela(rk_todos.sort_values("Preço médio", ascending=False).round(2))
st.info(f"**Pergunta investigativa:** {config.PERGUNTA_G2}")

# ================================================================ 3. Brent
st.header("3. Cenário internacional: petróleo Brent")
if bt_f.empty:
    st.warning("Nenhuma cotação do Brent no período selecionado.")
else:
    mostrar(gr.grafico_brent(bt_f, marcos, ini, fim))
    st.caption(f"Unidade original da base: {config.UNIDADE_BRENT}. A base do Brent vai até "
               f"{brent['Data'].max():%d/%m/%Y}, enquanto os preços ANP vão até {brasil['Data final'].max():%d/%m/%Y}; "
               "só as semanas presentes nas duas bases entram na regressão.")
    st.markdown(f"_{config.TXT_G3}_")
st.info(f"**Pergunta investigativa:** {config.PERGUNTA_G3}")

# ================================================================ 4. Regressão
st.header("4. Relação estatística: Brent × preço dos combustíveis")
comb4 = st.selectbox("Combustível", config.ORDEM_COMBUSTIVEIS, index=0, key="comb_g4",
                     help="Atualiza pontos, reta, coeficientes e conclusão.")
st.caption("Cada ponto é uma semana com observação válida nas duas bases: a cotação do Brent (sexta-feira) é "
           "associada à semana ANP (domingo a sábado) que a contém. Sem interpolação nem preenchimento.")
if al_f.empty:
    st.warning("Nenhuma semana com dados válidos nas duas bases no período selecionado.")
else:
    resultados = an.regressoes(al_f)
    res = resultados[comb4]
    d4 = al_f[al_f["Combustível"] == comb4]
    if res is None:
        st.warning("Observações insuficientes (mínimo de 3 semanas) para estimar a regressão neste período.")
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Coef. angular (R$/l por US$ 1)", an.fmt(res["slope"], 4),
                  help="Variação média do preço do combustível para cada US$ 1 de diferença no Brent.")
        m2.metric("Intercepto (R$/l)", an.fmt(res["intercept"], 3),
                  help="Valor estimado quando Brent = 0; pode não ter interpretação econômica prática.")
        m3.metric("R²", an.fmt(res["r2"], 3), help="Proporção da variabilidade do preço explicada pelo modelo linear.")
        m4.metric("Correlação de Pearson (r)", an.fmt(res["r"], 3),
                  help="Intensidade e direção da associação linear.")
        m5.metric("Semanas (n)", str(res["n"]),
                  f"p = {'< 0,0001' if res['p'] < 0.0001 else an.fmt(res['p'], 4)}" if res["p"] == res["p"] else None,
                  delta_color="off")
    mostrar(gr.grafico_dispersao(d4, res, comb4))
    st.markdown("#### Conclusão")
    st.markdown(an.conclusao(comb4, resultados, al_f[al_f["Combustível"] == comb4]))

    with st.expander("Regressões dos três combustíveis e dados pareados"):
        linhas = [{"Combustível": c, "Coef. angular (R$/l por US$ 1)": v["slope"], "Intercepto (R$/l)": v["intercept"],
                   "R²": v["r2"], "r de Pearson": v["r"], "p-valor (slope)": v["p"], "n": v["n"]}
                  for c, v in resultados.items() if v is not None]
        tabela(pd.DataFrame(linhas).round(4))
        largo = (al_f.pivot(index=["Data Brent", "Data final", config.COL_BRENT], columns="Combustível",
                            values="Preço médio").reset_index())
        largo.columns.name = None
        tabela(largo)
        st.download_button("Baixar dados pareados (CSV)", csv_br(largo), "brent_combustiveis_semanal.csv", "text/csv")
