"""app_2.py – Complemento do app.py: análise por estado + IPCA e câmbio x gasolina.

Como rodar (na mesma pasta de app.py, dados.py e das duas planilhas da ANP):
    streamlit run app_2.py

Fontes externas (baixadas na hora, sem chave de API):
    Banco Central do Brasil – SGS  https://api.bcb.gov.br
      · série 433 = IPCA, variação mensal (%)  (índice calculado pelo IBGE)
      · série 1   = Dólar americano (venda), cotação diária (R$)
Se a internet falhar, o app usa a última cópia salva em cache_sgs_<série>.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

import dados

ARQ_ESTADOS = "semanal-estados-desde-2013.xlsx"
SGS_IPCA, SGS_DOLAR = 433, 1
PASTA = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

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


# =============================================================== LEITURA
def carregar_estados(caminho: str = ARQ_ESTADOS) -> pd.DataFrame:
    """Lê a planilha de estados da ANP (mesmo padrão de dados.carregar) – desde 2020."""
    p = PASTA / caminho
    p = p if p.exists() else Path(caminho)
    pkl = p.with_suffix(".cache.pkl")          # a planilha tem ~12 MB: guarda uma cópia rápida
    if pkl.exists() and pkl.stat().st_mtime >= p.stat().st_mtime:
        try:
            return pd.read_pickle(pkl)
        except Exception:                      # cópia gerada por outra versão do pandas: relê a planilha
            pass

    bruto = pd.read_excel(p, header=17)
    bruto.columns = [str(c).strip() for c in bruto.columns]
    df = bruto[bruto["PRODUTO"].isin(dados.PRODUTOS)].copy()
    df["Combustível"] = df["PRODUTO"].map(dados.PRODUTOS)
    df["Estado"] = df["ESTADO"].map(NOMES_UF).fillna(df["ESTADO"].str.title())
    df["Região"] = df["REGIÃO"].str.title()
    df["Data inicial"] = pd.to_datetime(df["DATA INICIAL"])
    df["Data final"] = pd.to_datetime(df["DATA FINAL"])
    for origem, destino in {"PREÇO MÉDIO REVENDA": "Preço médio",
                            "PREÇO MÍNIMO REVENDA": "Preço mínimo (posto)",
                            "PREÇO MÁXIMO REVENDA": "Preço máximo (posto)",
                            "NÚMERO DE POSTOS PESQUISADOS": "Postos pesquisados"}.items():
        df[destino] = pd.to_numeric(df[origem], errors="coerce")
    df = df[df["Data inicial"] >= dados.DATA_INICIO].dropna(subset=["Preço médio"])
    cols = ["Combustível", "Estado", "Região", "Data inicial", "Data final", "Preço médio",
            "Preço mínimo (posto)", "Preço máximo (posto)", "Postos pesquisados"]
    out = df[cols].sort_values(["Combustível", "Estado", "Data final"]).reset_index(drop=True)
    try:
        out.to_pickle(pkl)
    except OSError:
        pass
    return out


def _baixar_sgs(serie: int, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    r = requests.get(
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados",
        params={"formato": "json", "dataInicial": inicio.strftime("%d/%m/%Y"),
                "dataFinal": fim.strftime("%d/%m/%Y")},
        headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df.dropna().sort_values("data").reset_index(drop=True)


@st.cache_data(ttl=6 * 3600, show_spinner="Baixando dados do Banco Central...")
def serie_sgs(serie: int, inicio: pd.Timestamp, fim: pd.Timestamp):
    """Devolve (DataFrame data/valor, origem) ou (None, mensagem de erro)."""
    cache = PASTA / f"cache_sgs_{serie}.csv"
    try:
        df = _baixar_sgs(serie, inicio, fim)
        df.to_csv(cache, index=False)
        return df, "Banco Central (SGS) – online"
    except Exception as e:                                    # sem internet, bloqueio, API fora...
        if cache.exists():
            df = pd.read_csv(cache, parse_dates=["data"])
            return df, f"cópia local de {cache.name} (download falhou: {type(e).__name__})"
        return None, f"{type(e).__name__}: {e}"


# =============================================================== ANÁLISES – ESTADOS
def ranking_semana(df: pd.DataFrame, data: pd.Timestamp) -> pd.DataFrame:
    """Preço médio por estado em uma semana, do mais caro ao mais barato."""
    x = df[df["Data final"] == data].sort_values("Preço médio", ascending=False).reset_index(drop=True)
    x.insert(0, "Posição", x.index + 1)
    return x


def extremos_por_semana(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada semana: estado mais caro, mais barato e o spread entre eles."""
    g = df.groupby("Data final")
    i_max, i_min = g["Preço médio"].idxmax(), g["Preço médio"].idxmin()
    out = pd.DataFrame({
        "Mais caro": df.loc[i_max, "Estado"].values, "Preço mais caro": df.loc[i_max, "Preço médio"].values,
        "Mais barato": df.loc[i_min, "Estado"].values, "Preço mais barato": df.loc[i_min, "Preço médio"].values,
    }, index=i_max.index)
    out["Spread (R$/l)"] = out["Preço mais caro"] - out["Preço mais barato"]
    out["Spread (%)"] = (out["Preço mais caro"] / out["Preço mais barato"] - 1) * 100
    out["Média entre estados"] = g["Preço médio"].mean()
    out["Coef. de variação (%)"] = g["Preço médio"].std() / out["Média entre estados"] * 100
    return out.reset_index()


def variacao_por_estado(df: pd.DataFrame, data_ref: pd.Timestamp, data_fim: pd.Timestamp) -> pd.DataFrame:
    """Variação % do preço médio de cada estado entre data_ref e data_fim."""
    a = df[df["Data final"] == data_ref].set_index("Estado")["Preço médio"]
    b = df[df["Data final"] == data_fim].set_index("Estado")["Preço médio"]
    out = pd.DataFrame({"Preço inicial": a, "Preço final": b}).dropna()
    out["Variação (R$/l)"] = out["Preço final"] - out["Preço inicial"]
    out["Variação (%)"] = (out["Preço final"] / out["Preço inicial"] - 1) * 100
    return out.sort_values("Variação (%)", ascending=False).reset_index()


# =============================================================== ANÁLISES – IPCA / CÂMBIO
def gasolina_mensal(nacional: pd.DataFrame) -> pd.Series:
    g = nacional[nacional["Combustível"] == "Gasolina Comum"]
    mes = g["Data final"].dt.to_period("M").dt.to_timestamp()
    return g.groupby(mes)["Preço médio"].mean().rename("gasolina")


def painel_macro(gas_m: pd.Series, ipca: pd.DataFrame, dolar: pd.DataFrame) -> pd.DataFrame:
    """Tabela mensal: preço da gasolina, IPCA (var. e índice), dólar médio do mês."""
    p = pd.DataFrame({"gasolina": gas_m})
    ip = ipca.assign(mes=ipca["data"].dt.to_period("M").dt.to_timestamp()).set_index("mes")["valor"]
    p["ipca_var"] = ip
    dl = dolar.assign(mes=dolar["data"].dt.to_period("M").dt.to_timestamp()).groupby("mes")["valor"].mean()
    p["dolar"] = dl
    p = p.reindex(pd.date_range(p.index.min(), p.index.max(), freq="MS"))   # mês sem coleta vira NaN
    p["ipca_idx"] = (1 + p["ipca_var"].fillna(0) / 100).cumprod().where(p["ipca_var"].notna())
    # preço real: em reais do último mês com IPCA divulgado
    ult = p["ipca_idx"].last_valid_index()
    p["gasolina_real"] = p["gasolina"] * p.loc[ult, "ipca_idx"] / p["ipca_idx"]
    p["gasolina_var"] = p["gasolina"].pct_change(fill_method=None) * 100
    p["dolar_var"] = p["dolar"].pct_change(fill_method=None) * 100
    return p


def correlacao(p: pd.DataFrame, col: str, defasagem: int):
    """Correlação entre a variação mensal da gasolina e a de `col` defasada em `defasagem` meses."""
    x = pd.DataFrame({"gasolina": p["gasolina_var"], col: p[col].shift(defasagem)}).dropna()
    if len(x) < 6:
        return np.nan, len(x), x
    return x["gasolina"].corr(x[col]), len(x), x


def forca(r: float) -> str:
    if np.isnan(r):
        return "dados insuficientes"
    a = abs(r)
    txt = "fraca" if a < 0.3 else "moderada" if a < 0.6 else "forte"
    return f"{txt} {'positiva' if r > 0 else 'negativa'}"


# =============================================================== APP
st.set_page_config(page_title="Combustíveis por estado, IPCA e câmbio", layout="wide")
COMB_CORES = {"Gasolina Comum": "#E4572E", "Etanol Hidratado": "#2E9E5B", "Diesel S-10": "#2B59C3"}


@st.cache_data(show_spinner="Lendo planilha de estados (só na primeira vez)...")
def base_estados():
    return carregar_estados()


@st.cache_data
def base_nacional():
    return dados.carregar(str(PASTA / dados.ARQUIVO) if (PASTA / dados.ARQUIVO).exists() else dados.ARQUIVO)


est, nac = base_estados(), base_nacional()

st.title("⛽ Combustíveis por estado e a relação com IPCA e câmbio")
st.caption("Fontes: ANP (levantamento semanal de preços de revenda) · Banco Central do Brasil – SGS "
           "(IPCA/IBGE e dólar). Análise descritiva de associação; não afirma causa e efeito.")

# ---------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
d_min, d_max = est["Data final"].min().date(), est["Data final"].max().date()
periodo = st.sidebar.date_input("Período (data final da semana)", value=(d_min, d_max),
                                min_value=d_min, max_value=d_max)
if len(periodo) != 2:
    st.info("Selecione a data inicial e a final no filtro lateral.")
    st.stop()
comb = st.sidebar.selectbox("Combustível (análise por estado)", list(dados.PRODUTOS.values()))
marcos = st.sidebar.checkbox("Mostrar marcos do conflito", value=True)
if st.sidebar.button("🔄 Recarregar IPCA e câmbio"):
    serie_sgs.clear()

ref_comb = est[est["Combustível"] == comb]                      # base completa do combustível
df = ref_comb[(ref_comb["Data final"].dt.date >= periodo[0]) & (ref_comb["Data final"].dt.date <= periodo[1])]
if df.empty:
    st.warning("Nenhum dado para os filtros escolhidos.")
    st.stop()


def marcos_vline(fig):
    if marcos:
        for nome, d in dados.MARCOS.items():
            if periodo[0] <= d.date() <= periodo[1]:
                fig.add_vline(x=d, line_dash="dot", line_color="gray")
                fig.add_annotation(x=d, y=1.04, yref="paper", text=nome, showarrow=False,
                                   textangle=-30, font=dict(size=9, color="gray"))
    return fig


aba1, aba2 = st.tabs(["📍 Estados: mais caro × mais barato", "📈 IPCA e câmbio × gasolina"])

# ================================================================ ABA 1 – ESTADOS
with aba1:
    ult_data = df["Data final"].max()
    rk = ranking_semana(df, ult_data)
    caro, barato = rk.iloc[0], rk.iloc[-1]
    media_uf = rk["Preço médio"].mean()

    st.subheader(f"{comb} – semana de {ult_data:%d/%m/%Y}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔺 Estado mais caro", caro["Estado"], f"R$ {caro['Preço médio']:.2f}/l", delta_color="off")
    c2.metric("🔻 Estado mais barato", barato["Estado"], f"R$ {barato['Preço médio']:.2f}/l", delta_color="off")
    c3.metric("Diferença entre eles", f"R$ {caro['Preço médio'] - barato['Preço médio']:.2f}/l",
              f"{(caro['Preço médio'] / barato['Preço médio'] - 1) * 100:.1f}% acima", delta_color="off")
    c4.metric("Média entre estados", f"R$ {media_uf:.2f}/l",
              f"desvio-padrão R$ {rk['Preço médio'].std():.2f}", delta_color="off")

    # --- 1. ranking
    st.subheader("1. Ranking de preço médio por estado (semana mais recente)")
    rk_plot = rk.sort_values("Preço médio")
    rk_plot["Destaque"] = np.where(rk_plot["Estado"] == caro["Estado"], "Mais caro",
                                   np.where(rk_plot["Estado"] == barato["Estado"], "Mais barato", "Demais"))
    fig1 = px.bar(rk_plot, x="Preço médio", y="Estado", orientation="h", color="Destaque", text_auto=".2f",
                  color_discrete_map={"Mais caro": "#C0392B", "Mais barato": "#1E8449", "Demais": "#9AA5B1"},
                  hover_data={"Região": True, "Postos pesquisados": True, "Destaque": False})
    fig1.add_vline(x=media_uf, line_dash="dash", line_color="black",
                   annotation_text=f"média R$ {media_uf:.2f}", annotation_position="top")
    fig1.update_layout(height=720, legend_title_text="", xaxis_title="R$/litro", yaxis_title="",
                       xaxis_range=[rk["Preço médio"].min() * 0.95, rk["Preço médio"].max() * 1.02])
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("Estados com poucos postos pesquisados (ex.: Amapá, Roraima) têm médias mais voláteis – "
               "passe o mouse na barra para ver o nº de postos.")

    # --- 2. histórico dos extremos
    ext = extremos_por_semana(df)
    st.subheader("2. Estado mais caro × mais barato ao longo do tempo")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=ext["Data final"], y=ext["Preço mais caro"], name="Mais caro", mode="lines",
                              line=dict(color="#C0392B"), customdata=ext["Mais caro"],
                              hovertemplate="%{customdata}: R$ %{y:.2f}<extra>Mais caro</extra>"))
    fig2.add_trace(go.Scatter(x=ext["Data final"], y=ext["Média entre estados"], name="Média entre estados",
                              mode="lines", line=dict(color="gray", dash="dash")))
    fig2.add_trace(go.Scatter(x=ext["Data final"], y=ext["Preço mais barato"], name="Mais barato", mode="lines",
                              line=dict(color="#1E8449"), customdata=ext["Mais barato"],
                              hovertemplate="%{customdata}: R$ %{y:.2f}<extra>Mais barato</extra>"))
    fig2.update_layout(hovermode="x unified", legend_title_text="", yaxis_title="R$/litro", margin=dict(t=50))
    st.plotly_chart(marcos_vline(fig2), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Quantas semanas cada estado foi o mais caro / mais barato (no período)**")
        cont = pd.concat([ext["Mais caro"].value_counts().rename("Semanas como mais caro"),
                          ext["Mais barato"].value_counts().rename("Semanas como mais barato")],
                         axis=1).fillna(0).astype(int)
        cont = cont[(cont > 0).any(axis=1)].sort_values(["Semanas como mais caro", "Semanas como mais barato"],
                                                        ascending=False)
        st.dataframe(cont, use_container_width=True)
    with c2:
        st.markdown("**Spread entre o mais caro e o mais barato**")
        fig2b = px.line(ext, x="Data final", y="Spread (R$/l)", labels={"Data final": "Semana"})
        fig2b.update_traces(line_color="#7D3C98")
        st.plotly_chart(marcos_vline(fig2b), use_container_width=True)
        st.caption(f"Spread médio no período: R$ {ext['Spread (R$/l)'].mean():.2f}/l "
                   f"({ext['Spread (%)'].mean():.1f}%) · máximo R$ {ext['Spread (R$/l)'].max():.2f} "
                   f"em {ext.loc[ext['Spread (R$/l)'].idxmax(), 'Data final']:%d/%m/%Y}.")

    # --- 3. variação entre estados
    st.subheader("3. Variação de preço entre os estados")
    modo = st.radio("Referência da variação", ["Desde 28/02/2026 (início do conflito)", "Desde o início do período filtrado"],
                    horizontal=True)
    if modo.startswith("Desde 28/02"):
        data_ref, rotulo = dados.DATA_BASE, "28/02/2026"
    else:
        data_ref = df["Data final"].min()
        rotulo = f"{data_ref:%d/%m/%Y}"
    var = variacao_por_estado(ref_comb, data_ref, ult_data)
    if var.empty or data_ref >= ult_data:
        st.info("O período filtrado precisa terminar depois da data de referência "
                f"({rotulo}) para calcular a variação.")
        var = var.iloc[0:0]
    else:
        sobe, desce = var.iloc[0], var.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Maior alta", sobe["Estado"], f"{sobe['Variação (%)']:+.1f}% (R$ {sobe['Variação (R$/l)']:+.2f})",
                  delta_color="off")
        c2.metric("Menor alta / maior queda", desce["Estado"],
                  f"{desce['Variação (%)']:+.1f}% (R$ {desce['Variação (R$/l)']:+.2f})", delta_color="off")
        c3.metric("Variação média entre estados", f"{var['Variação (%)'].mean():+.1f}%",
                  f"amplitude {sobe['Variação (%)'] - desce['Variação (%)']:.1f} p.p.", delta_color="off")
        fig3 = px.bar(var.sort_values("Variação (%)"), x="Variação (%)", y="Estado", orientation="h",
                      color="Variação (%)", color_continuous_scale="RdYlGn_r", text_auto=".1f")
        fig3.update_layout(height=720, coloraxis_showscale=False, yaxis_title="",
                           xaxis_title=f"Variação % do preço médio: {rotulo} → {ult_data:%d/%m/%Y}")
        st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Ver tabelas e baixar dados"):
        st.markdown("**Ranking da semana mais recente**")
        st.dataframe(rk[["Posição", "Estado", "Região", "Preço médio", "Preço mínimo (posto)",
                         "Preço máximo (posto)", "Postos pesquisados"]].round(2), use_container_width=True)
        st.markdown("**Mais caro / mais barato por semana**")
        st.dataframe(ext.round(2), use_container_width=True)
        st.download_button("Baixar extremos por semana (CSV)",
                           ext.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           f"extremos_{comb}.csv", "text/csv")

# ================================================================ ABA 2 – IPCA E CÂMBIO
with aba2:
    st.subheader("Gasolina comum (Brasil) × IPCA × dólar – visão mensal")
    ini_ext, fim_ext = pd.Timestamp(dados.DATA_INICIO), pd.Timestamp.today().normalize()
    ipca, org_ipca = serie_sgs(SGS_IPCA, ini_ext, fim_ext)
    dolar, org_dol = serie_sgs(SGS_DOLAR, ini_ext, fim_ext)

    if ipca is None or dolar is None:
        st.error("Não consegui baixar os dados do Banco Central e não há cópia local. "
                 "Verifique a conexão (ou proxy/firewall liberando api.bcb.gov.br) e clique em "
                 "'Recarregar IPCA e câmbio' na barra lateral.")
        st.code(f"IPCA: {org_ipca}\nDólar: {org_dol}")
        st.stop()
    st.caption(f"IPCA: {org_ipca} · Dólar: {org_dol}")

    p_full = painel_macro(gasolina_mensal(nac), ipca, dolar)
    ini_m = pd.Timestamp(periodo[0]).to_period("M").to_timestamp()
    fim_m = pd.Timestamp(periodo[1]).to_period("M").to_timestamp()
    p = p_full[(p_full.index >= ini_m) & (p_full.index <= fim_m)]
    if p.dropna(subset=["gasolina", "ipca_idx", "dolar"]).empty:
        st.warning("Sem meses em comum entre gasolina, IPCA e dólar no período escolhido.")
        st.stop()
    ult_ipca = p_full["ipca_idx"].last_valid_index()
    st.caption(f"Último IPCA divulgado: {ult_ipca:%m/%Y}. O mês corrente da gasolina e do dólar é parcial "
               "(média até a última coleta).")

    # --- KPIs desde fev/2026
    mes_base = pd.Timestamp("2026-02-01")
    if mes_base in p_full.index:
        fim_k = p_full[["gasolina", "dolar", "ipca_idx"]].dropna().index.max()
        b, u = p_full.loc[mes_base], p_full.loc[fim_k]
        st.markdown(f"**Variação de fev/2026 até {fim_k:%m/%Y}** (médias mensais)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Gasolina", f"R$ {u['gasolina']:.2f}", f"{(u['gasolina'] / b['gasolina'] - 1) * 100:+.1f}%",
                  delta_color="inverse")
        c2.metric("Dólar (média)", f"R$ {u['dolar']:.2f}", f"{(u['dolar'] / b['dolar'] - 1) * 100:+.1f}%",
                  delta_color="inverse")
        c3.metric("IPCA acumulado", f"{(u['ipca_idx'] / b['ipca_idx'] - 1) * 100:+.1f}%",
                  help="Inflação acumulada entre fev/2026 e o último mês comum.", delta_color="off")

    # --- 1. números-índice
    st.subheader("1. Evolução comparada (base 100 no 1º mês com os três dados)")
    comum = p.dropna(subset=["gasolina", "ipca_idx", "dolar"])
    base = comum.iloc[0]
    idx = pd.DataFrame({"Gasolina": p["gasolina"] / base["gasolina"] * 100,
                        "Dólar": p["dolar"] / base["dolar"] * 100,
                        "IPCA (inflação acumulada)": p["ipca_idx"] / base["ipca_idx"] * 100})
    idx.index.name = "Mês"
    fig_i = px.line(idx.reset_index().melt("Mês", var_name="Série", value_name="Índice"),
                    x="Mês", y="Índice", color="Série",
                    color_discrete_map={"Gasolina": COMB_CORES["Gasolina Comum"], "Dólar": "#2B59C3",
                                        "IPCA (inflação acumulada)": "#555555"})
    fig_i.add_hline(y=100, line_color="black", line_width=1)
    fig_i.update_layout(hovermode="x unified", legend_title_text="", margin=dict(t=50))
    st.plotly_chart(marcos_vline(fig_i), use_container_width=True)
    st.caption(f"Base 100 = {comum.index[0]:%m/%Y}. Se a gasolina fica acima do IPCA, ela subiu mais que a "
               "inflação geral; se fica abaixo, perdeu poder de compra relativo.")

    # --- 2. preço real
    st.subheader("2. Preço da gasolina: nominal × real (descontada a inflação)")
    real = p.dropna(subset=["gasolina_real"])
    fig_r = go.Figure()
    fig_r.add_trace(go.Scatter(x=real.index, y=real["gasolina"], name="Nominal", line=dict(color="#E4572E")))
    fig_r.add_trace(go.Scatter(x=real.index, y=real["gasolina_real"],
                               name=f"Real (R$ de {ult_ipca:%m/%Y})", line=dict(color="#7D3C98", dash="dash")))
    fig_r.update_layout(hovermode="x unified", legend_title_text="", yaxis_title="R$/litro", margin=dict(t=50))
    st.plotly_chart(marcos_vline(fig_r), use_container_width=True)
    if len(real) >= 2:
        v_nom = (real["gasolina"].iloc[-1] / real["gasolina"].iloc[0] - 1) * 100
        v_real = (real["gasolina_real"].iloc[-1] / real["gasolina_real"].iloc[0] - 1) * 100
        st.caption(f"No período, a gasolina variou {v_nom:+.1f}% em termos nominais e {v_real:+.1f}% em termos reais.")

    # --- 3. dólar x gasolina
    st.subheader("3. Dólar × preço da gasolina")
    fig_d = go.Figure()
    fig_d.add_trace(go.Scatter(x=p.index, y=p["gasolina"], name="Gasolina (R$/l)",
                               line=dict(color=COMB_CORES["Gasolina Comum"])))
    fig_d.add_trace(go.Scatter(x=p.index, y=p["dolar"], name="Dólar (R$)", yaxis="y2",
                               line=dict(color="#2B59C3")))
    fig_d.update_layout(hovermode="x unified", legend_title_text="", margin=dict(t=50),
                        yaxis=dict(title="Gasolina (R$/l)"),
                        yaxis2=dict(title="Dólar (R$)", overlaying="y", side="right", showgrid=False))
    st.plotly_chart(marcos_vline(fig_d), use_container_width=True)

    # --- 4. correlação
    st.subheader("4. Associação entre as variações mensais")
    st.caption("Usamos variações mensais (%), não os níveis: duas séries que apenas sobem com o tempo "
               "parecem correlacionadas mesmo sem relação real.")
    lag = st.slider("Defasagem (meses): variação do IPCA/dólar no mês t − n  ×  variação da gasolina no mês t",
                    0, 6, 0)
    r_ip, n_ip, xy_ip = correlacao(p, "ipca_var", lag)
    r_dl, n_dl, xy_dl = correlacao(p, "dolar_var", lag)
    c1, c2 = st.columns(2)
    for col, nome, r, n, xy, cname, cor in [(c1, "IPCA", r_ip, n_ip, xy_ip, "ipca_var", "#555555"),
                                           (c2, "Dólar", r_dl, n_dl, xy_dl, "dolar_var", "#2B59C3")]:
        with col:
            st.metric(f"Correlação gasolina × {nome}", "—" if np.isnan(r) else f"{r:+.2f}",
                      f"{forca(r)} · {n} meses", delta_color="off")
            if n >= 6:
                fig_s = px.scatter(xy, x=cname, y="gasolina", color_discrete_sequence=[cor],
                                   labels={cname: f"Var. mensal {nome} (%)", "gasolina": "Var. mensal gasolina (%)"},
                                   hover_data={cname: ":.2f", "gasolina": ":.2f"})
                a, b0 = np.polyfit(xy[cname], xy["gasolina"], 1)
                xs = np.array([xy[cname].min(), xy[cname].max()])
                fig_s.add_trace(go.Scatter(x=xs, y=a * xs + b0, mode="lines", name="tendência",
                                           line=dict(color="black", dash="dash")))
                fig_s.update_layout(showlegend=False, margin=dict(t=20))
                st.plotly_chart(fig_s, use_container_width=True)
    st.info("Leitura simplificada: correlação mede se as séries andam juntas, não se uma causa a outra. "
            "O preço da gasolina é afetado também por petróleo, impostos, política de preços da Petrobras "
            "e mistura de etanol, que não estão nesta análise.")

    with st.expander("Ver tabela mensal e baixar dados"):
        tab = p.rename(columns={"gasolina": "Gasolina (R$/l)", "gasolina_real": "Gasolina real (R$/l)",
                                "ipca_var": "IPCA mensal (%)", "ipca_idx": "IPCA índice",
                                "dolar": "Dólar médio (R$)", "gasolina_var": "Var. gasolina (%)",
                                "dolar_var": "Var. dólar (%)"})
        st.dataframe(tab.round(3), use_container_width=True)
        st.download_button("Baixar tabela mensal (CSV)",
                           tab.reset_index(names="Mês").to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           "gasolina_ipca_cambio_mensal.csv", "text/csv")
