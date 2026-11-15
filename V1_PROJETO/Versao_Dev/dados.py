"""Leitura, tratamento e cálculo dos indicadores (sem dependência do Streamlit)."""
import pandas as pd

ARQUIVO = "semanal-brasil-desde-2013.xlsx"
DATA_INICIO = pd.Timestamp("2020-01-01")
DATA_BASE = pd.Timestamp("2026-02-28")   # semana que termina em 28/02/2026 (início do conflito)

PRODUTOS = {
    "GASOLINA COMUM": "Gasolina Comum",
    "ETANOL HIDRATADO": "Etanol Hidratado",
    "OLEO DIESEL S10": "Diesel S-10",
}

MARCOS = {
    "28/02 Início do conflito": pd.Timestamp("2026-02-28"),
    "13/04 Bloqueio naval EUA": pd.Timestamp("2026-04-13"),
    "14/07 Retomada do bloqueio": pd.Timestamp("2026-07-14"),
}


def carregar(caminho: str = ARQUIVO) -> pd.DataFrame:
    """Lê a planilha da ANP e devolve uma base enxuta e tratada (desde 2020)."""
    # O cabeçalho real está na linha 18 (índice 17) da planilha; acima há notas da ANP.
    bruto = pd.read_excel(caminho, header=17)
    bruto.columns = [str(c).strip() for c in bruto.columns]

    df = bruto[bruto["PRODUTO"].isin(PRODUTOS)].copy()
    df["Combustível"] = df["PRODUTO"].map(PRODUTOS)
    df["Data inicial"] = pd.to_datetime(df["DATA INICIAL"])
    df["Data final"] = pd.to_datetime(df["DATA FINAL"])

    # Colunas numéricas: valores ausentes vêm como "-" em algumas linhas
    for origem, destino in {
        "PREÇO MÉDIO REVENDA": "Preço médio",
        "PREÇO MÍNIMO REVENDA": "Preço mínimo (posto)",
        "PREÇO MÁXIMO REVENDA": "Preço máximo (posto)",
        "NÚMERO DE POSTOS PESQUISADOS": "Postos pesquisados",
    }.items():
        df[destino] = pd.to_numeric(df[origem], errors="coerce")

    df = df[df["Data inicial"] >= DATA_INICIO].dropna(subset=["Preço médio"])
    cols = ["Combustível", "Data inicial", "Data final", "Preço médio",
            "Preço mínimo (posto)", "Preço máximo (posto)", "Postos pesquisados"]
    return df[cols].sort_values(["Combustível", "Data final"]).reset_index(drop=True)


def preco_base(df: pd.DataFrame, combustivel: str) -> float:
    """Preço médio na semana que termina em 28/02/2026."""
    x = df[(df["Combustível"] == combustivel) & (df["Data final"] == DATA_BASE)]
    return float(x["Preço médio"].iloc[0])


def kpis(df: pd.DataFrame, ref: pd.DataFrame | None = None) -> pd.DataFrame:
    """Uma linha por combustível com os indicadores do período filtrado.
    `ref` é a base completa, usada para achar o preço de 28/02/2026 mesmo se o filtro o excluir."""
    ref = df if ref is None else ref
    linhas = []
    for comb in PRODUTOS.values():
        x = df[df["Combustível"] == comb].sort_values("Data final")
        if x.empty:
            continue
        atual = x.iloc[-1]
        base = preco_base(ref, comb)
        idx_max, idx_min = x["Preço médio"].idxmax(), x["Preço médio"].idxmin()
        linhas.append({
            "Combustível": comb,
            "Semana mais recente": atual["Data final"],
            "Preço atual (R$/l)": atual["Preço médio"],
            "Preço em 28/02/2026": base,
            "Variação desde 28/02 (%)": (atual["Preço médio"] / base - 1) * 100,
            "Média do período (R$/l)": x["Preço médio"].mean(),
            "Maior preço médio (R$/l)": x.loc[idx_max, "Preço médio"],
            "Semana do maior preço": x.loc[idx_max, "Data final"],
            "Menor preço médio (R$/l)": x.loc[idx_min, "Preço médio"],
            "Semana do menor preço": x.loc[idx_min, "Data final"],
        })
    return pd.DataFrame(linhas)


def com_variacao(df: pd.DataFrame, ref: pd.DataFrame | None = None) -> pd.DataFrame:
    """Acrescenta variação % semana a semana e variação % acumulada desde 28/02/2026."""
    out = df.sort_values(["Combustível", "Data final"]).copy()
    out["Variação semanal (%)"] = out.groupby("Combustível")["Preço médio"].pct_change() * 100
    ref = df if ref is None else ref
    bases = {c: preco_base(ref, c) for c in out["Combustível"].unique()}
    out["Var. desde 28/02 (%)"] = (out["Preço médio"] / out["Combustível"].map(bases) - 1) * 100
    return out


def pico_pos_conflito(df: pd.DataFrame) -> pd.DataFrame:
    """Maior preço médio após 28/02/2026 e variação sobre a base."""
    linhas = []
    for comb in PRODUTOS.values():
        x = df[(df["Combustível"] == comb) & (df["Data final"] > DATA_BASE)]
        if x.empty:
            continue
        i = x["Preço médio"].idxmax()
        base = preco_base(df, comb)
        linhas.append({"Combustível": comb, "Pico pós-conflito (R$/l)": x.loc[i, "Preço médio"],
                       "Semana do pico": x.loc[i, "Data final"],
                       "Alta do pico sobre 28/02 (%)": (x.loc[i, "Preço médio"] / base - 1) * 100})
    return pd.DataFrame(linhas)
