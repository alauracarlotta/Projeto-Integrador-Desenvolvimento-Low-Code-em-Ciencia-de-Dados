"""app_3.py – Combustíveis em 2026: evolução semanal, variação %, comparação e ranking entre estados.

Como rodar (na mesma pasta deste arquivo e das duas bases CSV da ANP):
    streamlit run app_3.py

Bases (apenas 2026, separador ';', datas no formato mês/dia/ano):
    Base_Semanal_Brasil_2026.csv    – preço médio semanal nacional por combustível
    Base_Semanal_Estados_2026.csv   – preço médio semanal por estado e combustível

Os marcos do conflito Irã × EUA e a data-base (28/02/2026) são lidos de dados.py (dados.MARCOS e
dados.DATA_BASE) quando o módulo está na pasta; caso contrário, o app usa apenas 28/02/2026.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ARQ_BRASIL = "Base_Semanal_Brasil_2026.csv"
ARQ_ESTADOS = "Base_Semanal_Estados_2026.csv"
INICIO_2026 = pd.Timestamp("2026-01-01")
PASTA = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

# ---------------------------------------------------------------- marcos do conflito (mantidos do app original)
DATA_BASE = pd.Timestamp("2026-02-28")
MARCOS = {"Início do conflito": DATA_BASE}
try:
    import dados  # mesmo módulo do app.py / app_2.py

    DATA_BASE = pd.Timestamp(getattr(dados, "DATA_BASE", DATA_BASE))
    MARCOS = {nome: pd.Timestamp(d) for nome, d in dados.MARCOS.items()}
except Exception:  # dados.py ausente ou sem MARCOS: segue só com a data-base
    pass

PRODUTOS = {
    "GASOLINA COMUM": "Gasolina Comum",
    "GASOLINA ADITIVADA": "Gasolina Aditivada",
    "ETANOL HIDRATADO": "Etanol Hidratado",
    "OLEO DIESEL S10": "Diesel S-10",
    "OLEO DIESEL": "Diesel Comum",
    "GLP": "GLP (botijão 13 kg)",
    "GNV": "GNV",
}
PADRAO = ["Gasolina Comum", "Etanol Hidratado", "Diesel S-10"]
CORES = {"Gasolina Comum": "#E4572E", "Gasolina Aditivada": "#F2A541", "Etanol Hidratado": "#2E9E5B",
         "Diesel S-10": "#2B59C3", "Diesel Comum": "#7FA3E0", "GLP (botijão 13 kg)": "#7D3C98",
         "GNV": "#17A2B8"}

NOMES_UF = {
    "ACRE": "Acre", "ALAGOAS": "Alagoas", "AMAPA": "Amapá", "AMAZONAS": "Amazonas", "BAHIA": "Bahia",
    "CEARA": "Ceará", "DISTRITO FEDERAL": "Distrito Federal", "ESPIRITO SANTO": "Espírito Santo",
    "GOIAS": "Goiás", "MARANHAO": "Maranhão", "MATO GROSSO": "Mato Grosso",
    "MATO GROSSO DO SUL": "Mato Grosso do Sul", "MINAS GERAIS": "Minas Gerais", "PARA": "Pará",
    "PARAIBA": "Paraíba", "PARANA": "Paraná", "PERNAMBUCO": "Pernambuco", "PIAUI": "Piauí",
    "RIO DE JANEIRO": "Rio de Janeiro", "RIO GRANDE DO NORTE": "Rio Grande do Norte",
    "RIO GRANDE DO SUL": "Rio Grande do Sul", "RONDONIA": "Rondônia", "RORAIMA": "Roraima",
    "SANTA CATARINA": "Santa Catarina", "SAO PAULO": "São Paulo", "SERGIPE": "Sergipe",
    "TOCANTINS": "Tocantins",
}
REGIOES = {"NORTE": "Norte", "NORDESTE": "Nordeste", "CENTRO OESTE": "Centro-Oeste",
           "SUDESTE": "Sudeste", "SUL": "Sul"}


# =============================================================== LEITURA (sem Streamlit)
def _ler_csv_anp(nome: str) -> pd.DataFrame:
    """Lê um CSV da ANP: pula linhas antes do cabeçalho 'DATA INICIAL', separador ';'."""
    p = PASTA / nome
    if not p.exists():
        raise FileNotFoundError(f"Base não encontrada: {p}")

    with open(p, encoding="utf-8-sig") as f:
        linhas = f.readlines()

    cab = next(
        (i for i, linha in enumerate(linhas)
         if linha.strip().upper().startswith("DATA INICIAL")),
        None
    )
    if cab is None:
        raise ValueError(
            f"O cabeçalho 'DATA INICIAL' não foi encontrado no arquivo {p.name}."
        )

    # A ANP normalmente utiliza vírgula como separador decimal.
    df = pd.read_csv(
        p,
        sep=";",
        skiprows=cab,
        encoding="utf-8-sig",
        decimal=","
    )
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _padronizar(df: pd.DataFrame) -> pd.DataFrame:
    obrigatorias = [
        "PRODUTO", "UNIDADE DE MEDIDA", "DATA INICIAL", "DATA FINAL",
        "PREÇO MÉDIO REVENDA", "PREÇO MÍNIMO REVENDA",
        "PREÇO MÁXIMO REVENDA", "NÚMERO DE POSTOS PESQUISADOS"
    ]
    faltantes = [col for col in obrigatorias if col not in df.columns]
    if faltantes:
        raise ValueError(
            "Colunas obrigatórias ausentes na base da ANP: "
            + ", ".join(faltantes)
        )

    df = df.copy()
    df["PRODUTO"] = df["PRODUTO"].astype(str).str.strip().str.upper()
    df = df[df["PRODUTO"].isin(PRODUTOS)].copy()
    df["Combustível"] = df["PRODUTO"].map(PRODUTOS)
    df["Unidade"] = df["UNIDADE DE MEDIDA"].astype(str).str.strip()

    # O formato informado para os arquivos é mês/dia/ano.
    df["Data inicial"] = pd.to_datetime(
        df["DATA INICIAL"], format="%m/%d/%Y", errors="coerce"
    )
    df["Data final"] = pd.to_datetime(
        df["DATA FINAL"], format="%m/%d/%Y", errors="coerce"
    )

    for origem, destino in {
        "PREÇO MÉDIO REVENDA": "Preço médio",
        "PREÇO MÍNIMO REVENDA": "Preço mínimo (posto)",
        "PREÇO MÁXIMO REVENDA": "Preço máximo (posto)",
        "NÚMERO DE POSTOS PESQUISADOS": "Postos pesquisados"
    }.items():
        df[destino] = pd.to_numeric(df[origem], errors="coerce")

    return (
        df[
            (df["Data inicial"] >= INICIO_2026)
            & df["Data final"].notna()
        ]
        .dropna(subset=["Preço médio"])
    )


def carregar_brasil(nome: str = ARQ_BRASIL) -> pd.DataFrame:
    df = _padronizar(_ler_csv_anp(nome))
    cols = ["Combustível", "Unidade", "Data inicial", "Data final", "Preço médio",
            "Preço mínimo (posto)", "Preço máximo (posto)", "Postos pesquisados"]
    return df[cols].sort_values(["Combustível", "Data final"]).reset_index(drop=True)


def carregar_estados(nome: str = ARQ_ESTADOS) -> pd.DataFrame:
    df = _padronizar(_ler_csv_anp(nome))
    df["Estado"] = df["ESTADO"].map(NOMES_UF).fillna(df["ESTADO"].str.title())
    df["Região"] = df["REGIÃO"].map(REGIOES).fillna(df["REGIÃO"].str.title())
    cols = ["Combustível", "Unidade", "Estado", "Região", "Data inicial", "Data final", "Preço médio",
            "Preço mínimo (posto)", "Preço máximo (posto)", "Postos pesquisados"]
    return df[cols].sort_values(["Combustível", "Estado", "Data final"]).reset_index(drop=True)


# =============================================================== ANÁLISES (sem Streamlit)
def com_variacao(df: pd.DataFrame, data_ref: pd.Timestamp) -> pd.DataFrame:
    """Calcula a variação usando a última semana disponível até data_ref, por combustível."""
    df = df.sort_values(["Combustível", "Data final"]).copy()

    base = (
        df[df["Data final"] <= data_ref]
        .sort_values("Data final")
        .groupby("Combustível", as_index=False)
        .tail(1)
        .set_index("Combustível")
    )

    df["Preço de referência"] = df["Combustível"].map(base["Preço médio"])
    df["Data de referência"] = df["Combustível"].map(base["Data final"])

    df["Var. acumulada (%)"] = (
        (df["Preço médio"] / df["Preço de referência"]) - 1
    ) * 100

    df.loc[df["Preço de referência"] <= 0, "Var. acumulada (%)"] = np.nan
    return df


def resumo_periodo(df: pd.DataFrame, data_ref: pd.Timestamp, data_fim: pd.Timestamp) -> pd.DataFrame:
    """Compara a última semana disponível até cada data, por combustível."""
    ordenado = df.sort_values(["Combustível", "Data final"])

    a = (
        ordenado[ordenado["Data final"] <= data_ref]
        .groupby("Combustível", as_index=False)
        .tail(1)[["Combustível", "Unidade", "Data final", "Preço médio"]]
        .rename(columns={
            "Data final": "Data inicial",
            "Preço médio": "Preço inicial"
        })
    )
    b = (
        ordenado[ordenado["Data final"] <= data_fim]
        .groupby("Combustível", as_index=False)
        .tail(1)[["Combustível", "Data final", "Preço médio"]]
        .rename(columns={
            "Data final": "Data final",
            "Preço médio": "Preço final"
        })
    )

    out = a.merge(b, on="Combustível", how="inner")
    out = out[
        (out["Preço inicial"] > 0)
        & (out["Data final"] > out["Data inicial"])
    ].copy()
    out["Variação (abs.)"] = out["Preço final"] - out["Preço inicial"]
    out["Variação (%)"] = (
        out["Preço final"] / out["Preço inicial"] - 1
    ) * 100
    return out


def ranking(est: pd.DataFrame, comb: str, modo: str, data: pd.Timestamp | None = None,
            min_postos: int = 1) -> pd.DataFrame:
    """Ranking dos estados (1 = mais caro) em uma semana ('semana') ou na média do período ('media')."""
    x = est[(est["Combustível"] == comb) & (est["Postos pesquisados"] >= min_postos)]
    if modo == "semana":
        x = x[x["Data final"] == data][["Estado", "Região", "Preço médio", "Postos pesquisados"]]
    else:
        x = x.groupby(["Estado", "Região"], as_index=False).agg(
            **{"Preço médio": ("Preço médio", "mean"), "Postos pesquisados": ("Postos pesquisados", "mean")})
    x = x.sort_values("Preço médio", ascending=False).reset_index(drop=True)
    x.insert(0, "Posição", x.index + 1)
    return x


def variacao_estados(est: pd.DataFrame, comb: str, data_ref: pd.Timestamp, data_fim: pd.Timestamp,
                     min_postos: int = 1) -> pd.DataFrame:
    """Variação por estado usando a última semana disponível até cada data."""
    x = est[
        (est["Combustível"] == comb)
        & (est["Postos pesquisados"] >= min_postos)
    ].sort_values(["Estado", "Data final"])

    a = (
        x[x["Data final"] <= data_ref]
        .groupby("Estado", as_index=False)
        .tail(1)[["Estado", "Data final", "Preço médio"]]
        .rename(columns={
            "Data final": "Data inicial",
            "Preço médio": "Preço inicial"
        })
    )
    b = (
        x[x["Data final"] <= data_fim]
        .groupby("Estado", as_index=False)
        .tail(1)[["Estado", "Região", "Data final", "Preço médio"]]
        .rename(columns={
            "Data final": "Data final",
            "Preço médio": "Preço final"
        })
    )

    out = a.merge(b, on="Estado", how="inner")
    out = out[
        (out["Preço inicial"] > 0)
        & (out["Data final"] > out["Data inicial"])
    ].copy()
    out["Variação (abs.)"] = out["Preço final"] - out["Preço inicial"]
    out["Variação (%)"] = (
        out["Preço final"] / out["Preço inicial"] - 1
    ) * 100
    return out.sort_values("Variação (%)", ascending=False).reset_index(drop=True)


# ======================================================================= APP (Streamlit / Plotly)
st.set_page_config(page_title="Combustíveis 2026 – Brasil e estados", layout="wide")


@st.cache_data(show_spinner="Lendo as bases de 2026...")
def bases():
    brasil = carregar_brasil()
    estados = carregar_estados()

    if brasil.empty:
        raise ValueError("A base nacional não possui registros válidos de 2026.")
    if estados.empty:
        raise ValueError("A base de estados não possui registros válidos de 2026.")

    return brasil, estados


try:
    nac, est = bases()
except FileNotFoundError as e:
    st.error(
        f"{e}. Coloque {ARQ_BRASIL} e {ARQ_ESTADOS} na mesma pasta do app_3.py."
    )
    st.stop()
except (ValueError, KeyError, pd.errors.ParserError) as e:
    st.error(f"Não foi possível tratar as bases da ANP: {e}")
    st.stop()

# Atribuição explícita e validação antes de usar nac e est no restante do app.
if not isinstance(nac, pd.DataFrame) or not isinstance(est, pd.DataFrame):
    st.error("O carregamento não retornou DataFrames válidos.")
    st.stop()

st.title("⛽ Combustíveis em 2026: Brasil, estados e a instabilidade geopolítica")
st.caption("Fonte: ANP – levantamento semanal de preços de revenda, bases de 2026 (Brasil e estados). "
           "Análise descritiva de comportamento e associação; não afirma relação de causa e efeito.")

# ---------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
d_min, d_max = nac["Data final"].min().date(), nac["Data final"].max().date()
periodo = st.sidebar.date_input("Período (data final da semana)", value=(d_min, d_max),
                                min_value=d_min, max_value=d_max)
if len(periodo) != 2:
    st.info("Selecione a data inicial e a final no filtro lateral.")
    st.stop()
combs = st.sidebar.multiselect("Combustíveis", list(PRODUTOS.values()), default=PADRAO)
if not combs:
    st.info("Escolha ao menos um combustível no filtro lateral.")
    st.stop()
min_postos = st.sidebar.number_input("Mínimo de postos pesquisados por estado", min_value=1, value=1, step=1,
                                     help="Estados com poucos postos (ex.: Amapá, Roraima) têm médias mais "
                                          "voláteis. Vale para as análises por estado.")
marcos = st.sidebar.checkbox("Mostrar marcos do conflito", value=True)

ini, fim = pd.Timestamp(periodo[0]), pd.Timestamp(periodo[1])
no_periodo = lambda d: d[(d["Data final"] >= ini) & (d["Data final"] <= fim) & (d["Combustível"].isin(combs))]
df = no_periodo(nac)
df_est = no_periodo(est)
if df.empty:
    st.warning("Nenhum dado para os filtros escolhidos.")
    st.stop()
semanas = sorted(df["Data final"].unique())
ult_data, prim_data = pd.Timestamp(semanas[-1]), pd.Timestamp(semanas[0])


def linha_marcos(fig, facetas=False):
    """Linhas verticais pontilhadas com os marcos do conflito que caem dentro do período."""
    if marcos:
        for nome, d in MARCOS.items():
            if ini <= d <= fim:
                if facetas:
                    fig.add_vline(x=d, line_dash="dot", line_color="gray", row="all", col="all")
                else:
                    fig.add_vline(x=d, line_dash="dot", line_color="gray")
                fig.add_annotation(x=d, y=1.04, yref="paper", text=nome, showarrow=False,
                                   textangle=-30, font=dict(size=9, color="gray"))
    return fig


# ---------------------------------------------------------------- KPIs
st.subheader("Indicadores-chave (Brasil)")
completo = com_variacao(nac[nac["Combustível"].isin(combs)], DATA_BASE)
kpi = completo[completo["Data final"] == ult_data].set_index("Combustível")
cols = st.columns(len(combs))
for col, c in zip(cols, combs):
    with col:
        st.markdown(f"**{c}**")
        if c not in kpi.index:
            st.caption("Sem dados na última semana do período.")
            continue
        r = kpi.loc[c]
        sufixo = r["Unidade"]
        data_ref_kpi = r["Data de referência"]
        delta = (
            None if pd.isna(r["Var. acumulada (%)"])
            else f"{r['Var. acumulada (%)']:+.1f}% desde {data_ref_kpi:%d/%m}"
        )
        st.metric(f"Preço em {ult_data:%d/%m/%Y}", f"R$ {r['Preço médio']:.2f}", delta, delta_color="inverse",
                  help=f"Unidade: {sufixo}")
        st.caption(f"Unidade: {sufixo}")

# ================================================================ 1. EVOLUÇÃO SEMANAL
st.subheader("1. Evolução semanal dos preços médios de revenda")
n_un = df["Unidade"].nunique()
fig1 = px.line(df, x="Data final", y="Preço médio", color="Combustível", color_discrete_map=CORES,
               facet_row="Unidade" if n_un > 1 else None,
               labels={"Preço médio": "Preço médio (R$)", "Data final": "Semana"},
               category_orders={"Unidade": sorted(df["Unidade"].unique())})
if n_un > 1:
    fig1.update_yaxes(matches=None)
    fig1.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
fig1.update_layout(hovermode="x unified", legend_title_text="", margin=dict(t=50),
                   height=420 if n_un == 1 else 330 * n_un)
st.plotly_chart(linha_marcos(fig1, facetas=n_un > 1), use_container_width=True)
if n_un > 1:
    st.caption("Combustíveis com unidades diferentes (R$/l, R$/m³, R$/13 kg) ficam em painéis separados.")

# ================================================================ 2. VARIAÇÃO PERCENTUAL
st.subheader("2. Variação percentual dos preços no período")
modo_var = st.radio("Referência da variação", [f"Desde {DATA_BASE:%d/%m/%Y} (início do conflito)",
                                               f"Desde a primeira semana do período ({prim_data:%d/%m/%Y})"],
                    horizontal=True, key="ref_nac")
ref_nac = DATA_BASE if modo_var.startswith("Desde " + f"{DATA_BASE:%d/%m/%Y}") else prim_data
if ref_nac >= ult_data:
    st.info("O período filtrado precisa terminar depois da data de referência para calcular a variação.")
else:
    base_var = nac[nac["Combustível"].isin(combs)]
    dfv = com_variacao(base_var, ref_nac)
    dfv = dfv[(dfv["Data final"] >= max(ini, ref_nac)) & (dfv["Data final"] <= fim)]
    resumo = resumo_periodo(base_var, ref_nac, ult_data)

    if resumo.empty:
        st.info(
            "Não há semanas disponíveis suficientes para calcular a variação "
            "entre a referência escolhida e o final do período."
        )
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            if dfv["Var. acumulada (%)"].notna().any():
                fig2 = px.line(
                    dfv, x="Data final", y="Var. acumulada (%)",
                    color="Combustível", color_discrete_map=CORES,
                    labels={"Data final": "Semana"}
                )
                fig2.add_hline(y=0, line_color="black", line_width=1)
                fig2.update_layout(
                    hovermode="x unified", legend_title_text="", margin=dict(t=50),
                    yaxis_title=f"Variação acumulada desde {ref_nac:%d/%m/%Y} (%)"
                )
                st.plotly_chart(linha_marcos(fig2), use_container_width=True)
            else:
                st.info("Não há preços de referência disponíveis para os combustíveis selecionados.")
        with c2:
            fig2b = px.bar(
                resumo.sort_values("Variação (%)"),
                x="Variação (%)", y="Combustível", orientation="h",
                color="Combustível", color_discrete_map=CORES, text_auto="+.1f"
            )
            fig2b.update_layout(
                showlegend=False, margin=dict(t=50), yaxis_title="",
                xaxis_title=f"Variação % total: {ref_nac:%d/%m/%Y} → {ult_data:%d/%m/%Y}"
            )
            st.plotly_chart(fig2b, use_container_width=True)

        with st.expander("Ver tabela de variação"):
            st.dataframe(resumo.round(2), use_container_width=True)

# ================================================================ 3. COMPARAÇÃO ENTRE ESTADOS
st.subheader("3. Comparação dos preços entre os estados")
c1, c2, c3 = st.columns(3)
comb3 = c1.selectbox("Combustível", combs, key="comb3")
sem3 = c2.selectbox("Semana (data final)", [pd.Timestamp(s) for s in semanas[::-1]],
                    format_func=lambda d: f"{d:%d/%m/%Y}", key="sem3")
ind3 = c3.radio("Indicador", ["Preço médio na semana", "Variação % no período"], key="ind3")

est3 = df_est[df_est["Combustível"] == comb3]
un3 = est3["Unidade"].iloc[0] if not est3.empty else ""
if ind3 == "Preço médio na semana":
    rk = ranking(df_est, comb3, "semana", sem3, int(min_postos))
    if rk.empty:
        st.warning(f"Não há dados de {comb3} por estado na semana de {sem3:%d/%m/%Y}.")
    else:
        pn = nac[(nac["Combustível"] == comb3) & (nac["Data final"] == sem3)]["Preço médio"]
        media_uf = rk["Preço médio"].mean()
        plot = rk.sort_values("Preço médio")
        fig3 = px.bar(plot, x="Preço médio", y="Estado", orientation="h", color="Região", text_auto=".2f",
                      hover_data={"Postos pesquisados": True, "Região": False},
                      category_orders={"Estado": list(plot["Estado"])})
        fig3.add_vline(x=media_uf, line_dash="dash", line_color="black",
                       annotation_text=f"média dos estados R$ {media_uf:.2f}", annotation_position="top left")
        if not pn.empty:
            fig3.add_vline(x=float(pn.iloc[0]), line_dash="dot", line_color="#C0392B",
                           annotation_text=f"Brasil R$ {float(pn.iloc[0]):.2f}", annotation_position="top right")
        fig3.update_layout(height=760, yaxis_title="", xaxis_title=f"Preço médio ({un3}) – {sem3:%d/%m/%Y}",
                           legend_title_text="", xaxis_range=[plot["Preço médio"].min() * 0.95,
                                                              plot["Preço médio"].max() * 1.03])
        st.plotly_chart(fig3, use_container_width=True)
else:
    modo_ref3 = st.radio("Referência", [f"Desde {DATA_BASE:%d/%m/%Y}", f"Desde {prim_data:%d/%m/%Y} (início do período)"],
                         horizontal=True, key="ref3")
    ref3 = DATA_BASE if modo_ref3.startswith(f"Desde {DATA_BASE:%d/%m/%Y}") else prim_data
    var3 = variacao_estados(est[est["Combustível"] == comb3], comb3, ref3, ult_data, int(min_postos))
    if var3.empty or ref3 >= ult_data:
        st.info("Sem dados suficientes: o período precisa terminar depois da data de referência "
                f"({ref3:%d/%m/%Y}) e o combustível precisa ter preço nas duas semanas.")
    else:
        sobe, desce = var3.iloc[0], var3.iloc[-1]
        m1, m2, m3 = st.columns(3)
        m1.metric("Maior alta", sobe["Estado"], f"{sobe['Variação (%)']:+.1f}%", delta_color="off")
        m2.metric("Menor alta / maior queda", desce["Estado"], f"{desce['Variação (%)']:+.1f}%", delta_color="off")
        m3.metric("Média entre estados", f"{var3['Variação (%)'].mean():+.1f}%",
                  f"amplitude {sobe['Variação (%)'] - desce['Variação (%)']:.1f} p.p.", delta_color="off")
        fig3 = px.bar(var3.sort_values("Variação (%)"), x="Variação (%)", y="Estado", orientation="h",
                      color="Variação (%)", color_continuous_scale="RdYlGn_r", text_auto=".1f",
                      hover_data={"Preço inicial": ":.2f", "Preço final": ":.2f", "Região": True})
        fig3.update_layout(height=760, coloraxis_showscale=False, yaxis_title="",
                           xaxis_title=f"Variação % do preço médio: {ref3:%d/%m/%Y} → {ult_data:%d/%m/%Y}")
        st.plotly_chart(fig3, use_container_width=True)

# --- evolução de estados escolhidos x Brasil
st.markdown(f"**Evolução semanal de estados escolhidos – {comb3}**")
ufs = sorted(est3["Estado"].unique())
if ufs:
    rk_ref = ranking(df_est, comb3, "media", None, int(min_postos))
    padrao_uf = [u for u in ([rk_ref.iloc[0]["Estado"], rk_ref.iloc[-1]["Estado"], "São Paulo"] if not rk_ref.empty else [])
                 if u in ufs]
    padrao_uf = list(dict.fromkeys(padrao_uf))
    sel = st.multiselect("Estados para comparar (com a média do Brasil)", ufs, default=padrao_uf, key="ufs3")
    linhas = est3[est3["Estado"].isin(sel)]
    figE = px.line(linhas, x="Data final", y="Preço médio", color="Estado",
                   labels={"Preço médio": f"Preço médio ({un3})", "Data final": "Semana"})
    br = df[df["Combustível"] == comb3]
    figE.add_trace(go.Scatter(x=br["Data final"], y=br["Preço médio"], name="Brasil", mode="lines",
                              line=dict(color="black", dash="dash", width=3)))
    figE.update_layout(hovermode="x unified", legend_title_text="", margin=dict(t=50))
    st.plotly_chart(linha_marcos(figE), use_container_width=True)
    st.caption("Na base de estados, o preço de cada estado vem da pesquisa semanal da ANP; "
               "estados com poucos postos pesquisados oscilam mais.")

# ================================================================ 4. RANKING POR COMBUSTÍVEL
st.subheader("4. Ranking dos estados: maior e menor preço por combustível")
c1, c2 = st.columns(2)
modo4 = c1.radio("Base do ranking", [f"Semana mais recente ({ult_data:%d/%m/%Y})", "Média das semanas do período"],
                 horizontal=True, key="modo4")
top_n = c2.slider("Quantos estados mostrar em cada ponta", 3, 10, 5, key="topn")
chave = "semana" if modo4.startswith("Semana") else "media"

resumo_rank, rankings = [], {}
for c in combs:
    rk = ranking(df_est, c, chave, ult_data, int(min_postos))
    rankings[c] = rk
    if rk.empty:
        continue
    caro, barato = rk.iloc[0], rk.iloc[-1]
    resumo_rank.append({"Combustível": c, "Unidade": df_est[df_est["Combustível"] == c]["Unidade"].iloc[0],
                        "Estado mais caro": caro["Estado"], "Preço mais caro": caro["Preço médio"],
                        "Estado mais barato": barato["Estado"], "Preço mais barato": barato["Preço médio"],
                        "Diferença": caro["Preço médio"] - barato["Preço médio"],
                        "Diferença (%)": (caro["Preço médio"] / barato["Preço médio"] - 1) * 100})
if resumo_rank:
    st.dataframe(pd.DataFrame(resumo_rank).round(2), use_container_width=True, hide_index=True)
else:
    st.info("Sem dados por estado para os combustíveis e período escolhidos.")

abas = st.tabs(combs)
for aba, c in zip(abas, combs):
    with aba:
        rk = rankings[c]
        if rk.empty:
            st.info(f"Sem dados de {c} por estado para este filtro.")
            continue
        un = df_est[df_est["Combustível"] == c]["Unidade"].iloc[0]
        n = min(top_n, len(rk) // 2) or 1
        caros = rk.head(n).sort_values("Preço médio")
        baratos = rk.tail(n).sort_values("Preço médio", ascending=False)
        a, b = st.columns(2)
        with a:
            st.markdown(f"**🔺 {n} estados mais caros**")
            f = px.bar(caros, x="Preço médio", y="Estado", orientation="h", text_auto=".2f",
                       color_discrete_sequence=["#C0392B"], hover_data={"Região": True, "Postos pesquisados": ":.0f"},
                       category_orders={"Estado": list(caros["Estado"])})
            f.update_layout(yaxis_title="", xaxis_title=f"Preço médio ({un})",
                            xaxis_range=[rk["Preço médio"].min() * 0.9, rk["Preço médio"].max() * 1.03])
            st.plotly_chart(f, use_container_width=True)
        with b:
            st.markdown(f"**🔻 {n} estados mais baratos**")
            f = px.bar(baratos, x="Preço médio", y="Estado", orientation="h", text_auto=".2f",
                       color_discrete_sequence=["#1E8449"], hover_data={"Região": True, "Postos pesquisados": ":.0f"},
                       category_orders={"Estado": list(baratos["Estado"])})
            f.update_layout(yaxis_title="", xaxis_title=f"Preço médio ({un})",
                            xaxis_range=[rk["Preço médio"].min() * 0.9, rk["Preço médio"].max() * 1.03])
            st.plotly_chart(f, use_container_width=True)
        with st.expander(f"Ranking completo – {c}"):
            st.dataframe(rk.round(2), use_container_width=True, hide_index=True)
            st.download_button("Baixar ranking (CSV)",
                               rk.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                               f"ranking_{c.replace(' ', '_')}.csv", "text/csv", key=f"dl_{c}")

# ---------------------------------------------------------------- tabelas
with st.expander("Ver dados tratados"):
    st.markdown("**Brasil (período e combustíveis filtrados)**")
    st.dataframe(df.round(2), use_container_width=True)
    st.markdown("**Estados (período e combustíveis filtrados)**")
    st.dataframe(df_est.round(2), use_container_width=True)
    st.download_button("Baixar base de estados filtrada (CSV)",
                       df_est.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       "estados_2026_filtrado.csv", "text/csv")
