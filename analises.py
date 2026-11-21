"""Cálculos do dashboard: KPIs, agregações regionais, ranking, alinhamento semanal com o Brent,
regressão linear e texto da conclusão. Nenhuma dependência de Streamlit/Plotly."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config

try:  # opcional: só usado para o p-valor
    from scipy import stats as _stats
except Exception:  # pragma: no cover
    _stats = None


# ---------------------------------------------------------------- formatação pt-BR
def fmt(x: float, casas: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl(x: float, casas: int = 2) -> str:
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"R$ {fmt(x, casas)}"


def fmt_sinal(x: float, casas: int = 2) -> str:
    return "—" if x is None or np.isnan(x) else f"{'+' if x >= 0 else '−'}{fmt(abs(x), casas)}"


# ---------------------------------------------------------------- Gráfico 1: KPIs nacionais
def kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula os indicadores nacionais no período filtrado."""

    preco = config.COL_PRECO
    linhas = []

    for comb in config.ORDEM_COMBUSTIVEIS:

        d = (
            df[df["Combustível"] == comb]
            .sort_values("Semana")
        )

        if d.empty:
            continue

        first, last = d.iloc[0], d.iloc[-1]

        delta = (
            (last[preco] / first[preco] - 1) * 100
            if first[preco]
            else np.nan
        )

        linhas.append({
            "Combustível": comb,
            "Semana inicial": first["Semana"],
            "Semana mais recente": last["Semana"],
            "Preço atual": last[preco],
            config.COL_VARIACAO: delta
        })

    return pd.DataFrame(
        linhas,
        columns=[
            "Combustível",
            "Semana inicial",
            "Semana mais recente",
            "Preço atual",
            config.COL_VARIACAO
        ]
    )


# ---------------------------------------------------------------- Gráfico 2: regiões e ranking
def preco_por_regiao(
        est: pd.DataFrame,
        comb: str
    ) -> pd.DataFrame:
        """Calcula a média simples dos preços estaduais por região e semana."""

        preco = config.COL_PRECO

        return (
            est[est["Combustível"] == comb]
            .groupby(["Semana", "Região"], as_index=False)[preco]
            .mean()
        )


def ranking_estadual(
    est: pd.DataFrame,
    comb: str
) -> pd.DataFrame:
    """Calcula os indicadores estaduais no período selecionado."""

    preco = config.COL_PRECO

    state = (
        est[est["Combustível"] == comb]
        .sort_values("Semana")
    )

    grouped = state.groupby("UF", as_index=False).agg(
        **{
            "Média": (preco, "mean"),
            "Inicial": (preco, "first"),
            "Final": (preco, "last"),
            "Semanas": ("Semana", "nunique")
        }
    )

    grouped["Variação (%)"] = (
        grouped["Final"] / grouped["Inicial"] - 1
    ) * 100

    return grouped

def ranking_extremos(
    df: pd.DataFrame,
    metric: str,
    n: int = 3
) -> pd.DataFrame:
    """Seleciona as UFs com maiores e menores valores."""

    ordered = df.sort_values([metric, "UF"])

    menores = ordered.head(n).copy()
    maiores = ordered.tail(n).copy()

    menores["Grupo"] = "3 menores valores"
    maiores["Grupo"] = "3 maiores valores"

    return (
        pd.concat([maiores, menores])
        .drop_duplicates("UF")
    )


# ---------------------------------------------------------------- Gráfico 3: petróleo Brent

def variacao_brent(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a variação acumulada do Brent no período selecionado."""

    oil = df.sort_values("Semana").copy()

    preco = config.COL_BRENT
    variacao = config.COL_VARIACAO

    if oil.empty:
        oil[variacao] = pd.Series(dtype=float)
        return oil

    oil[variacao] = (
        oil[preco] / oil[preco].iloc[0] - 1
    ) * 100

    return oil

def media_movel_brent(
    df: pd.DataFrame,
    coluna: str
) -> pd.DataFrame:
    """Calcula a média móvel do Brent em uma janela de quatro semanas."""

    return (
        df.sort_values("Semana")
        .set_index("Semana")[coluna]
        .rolling("28D", min_periods=4)
        .mean()
        .reset_index(name="Média móvel")
    )

# ---------------------------------------------------------------- Alinhamento Brasil × Brent
def parear_semanas(
    combustiveis: pd.DataFrame,
    brent: pd.DataFrame,
    validacao: str = "many_to_one"
) -> pd.DataFrame:
    """Pareia observações da ANP e da EIA pela semana de referência."""

    return (
        combustiveis
        .merge(
            brent,
            on="Semana",
            how="inner",
            validate=validacao
        )
        .dropna(
            subset=[
                config.COL_PRECO,
                config.COL_BRENT
            ]
        )
        .sort_values("Semana")
        .reset_index(drop=True)
    )


def fases_conflito(
        datas: pd.Series
    ) -> tuple[pd.Series, list[str]]:
    """Rótulo de fase (antes/depois de cada marco) para colorir os pontos do gráfico 4."""
    d1, d2, d3 = [m["data"] for m in config.MARCOS]
    rot = [
        f"Antes do conflito (até {(d1 - pd.Timedelta(days=1)):%d/%m})",
        f"Conflito, antes do bloqueio ({d1:%d/%m}–{(d2 - pd.Timedelta(days=1)):%d/%m})",
        f"Bloqueio naval ({d2:%d/%m}–{(d3 - pd.Timedelta(days=1)):%d/%m})",
        f"Persistência do bloqueio (a partir de {d3:%d/%m})"
    ]
    idx = np.select([datas < d1, datas < d2, datas < d3], [0, 1, 2], default=3)
    return pd.Series(np.array(rot)[idx], index=datas.index), rot

def preparar_dispersao(
        pairs: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[str]]:
        """Prepara as datas e fases geopolíticas da dispersão."""

        dados = pairs.copy()

        dados["Data final"] = (
            dados["Semana"] + pd.Timedelta(days=6)
        )

        fases, rotulos = fases_conflito(
            dados["Data Brent"]
        )

        dados["Fase"] = fases

        return dados, rotulos


# ---------------------------------------------------------------- Regressão linear simples
def regressao(x: pd.Series, y: pd.Series) -> dict | None:
    """MQO de y sobre x. Devolve None se houver menos de 3 pontos ou x constante."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 3 or np.isclose(np.ptp(x), 0):
        return None
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    slope = ((x - xm) * (y - ym)).sum() / sxx
    intercept = ym - slope * xm
    resid = y - (intercept + slope * x)
    sst = ((y - ym) ** 2).sum()
    r2 = 1 - (resid ** 2).sum() / sst if sst > 0 else np.nan
    r = np.corrcoef(x, y)[0, 1] if sst > 0 else np.nan
    se = np.sqrt((resid ** 2).sum() / (n - 2) / sxx)
    p = np.nan
    if _stats is not None and se > 0:
        p = float(2 * _stats.t.sf(abs(slope / se), n - 2))
    return {"n": n, "slope": float(slope), "intercept": float(intercept), "r2": float(r2), "r": float(r),
            "se_slope": float(se), "p": p, "x_min": float(x.min()), "x_max": float(x.max())}


def tabela_regressoes(
    dados: pd.DataFrame,
    combustiveis: list[str]
) -> pd.DataFrame:
    """Calcula e organiza os resultados das regressões por combustível."""

    linhas = []

    for comb in combustiveis:

        d = dados[dados["Combustível"] == comb]

        resultado = regressao(
            d[config.COL_BRENT],
            d[config.COL_PRECO]
        )

        linhas.append({
            "Combustível": comb,
            "Coef. angular (R$/l por US$ 1)":
                resultado["slope"] if resultado else None,
            "Intercepto (R$/l)":
                resultado["intercept"] if resultado else None,
            "R²":
                resultado["r2"] if resultado else None,
            "r de Pearson":
                resultado["r"] if resultado else None,
            "p-valor":
                resultado["p"] if resultado else None,
            "n": len(d)
        })

    return pd.DataFrame(linhas)


def tabela_dados_pareados(
    dados: pd.DataFrame
) -> pd.DataFrame:
    """Organiza os dados semanais pareados entre ANP e Brent."""

    tabela = (
        dados.pivot(
            index=[
                "Semana",
                "Data Brent",
                config.COL_BRENT
            ],
            columns="Combustível",
            values=config.COL_PRECO
        )
        .reset_index()
        .sort_values("Semana")
    )

    tabela.columns.name = None

    tabela["Data final"] = (
        tabela["Semana"] + pd.Timedelta(days=6)
    )

    combustiveis_disponiveis = [
        comb
        for comb in config.ORDEM_COMBUSTIVEIS
        if comb in tabela.columns
    ]

    colunas = [
        "Data Brent",
        "Data final",
        config.COL_BRENT,
        *combustiveis_disponiveis
    ]

    return tabela[colunas].reset_index(drop=True)


def equacao(res: dict) -> str:
    sinal = "+" if res["intercept"] >= 0 else "−"
    return f"y = {fmt(res['slope'], 4)}·x {sinal} {fmt(abs(res['intercept']), 4)}"


def forca_r(r: float) -> str:
    a = abs(r)
    return ("muito fraca" if a < 0.2 else "fraca" if a < 0.4 else "moderada" if a < 0.6
            else "forte" if a < 0.8 else "muito forte")


# ---------------------------------------------------------------- Conclusão dinâmica
def conclusao(comb: str, res: dict[str, dict | None], alin: pd.DataFrame) -> str:
    r = res.get(comb)
    if r is None:
        return ("Não há observações semanais válidas suficientes (mínimo de 3, com variação do Brent) "
                "no período selecionado para estimar a regressão.")
    if abs(r["r"]) < 0.2:
        sentido = f"praticamente inexistente (sinal {'positivo' if r['r'] > 0 else 'negativo'}, sem relevância prática)"
    elif r["r"] > 0:
        sentido = "positiva (preços mais altos do combustível acompanham Brent mais alto)"
    else:
        sentido = "negativa (preços mais baixos do combustível acompanham Brent mais alto)"
    d10 = r["slope"] * 10
    txt = [
        f"**{comb} × Brent.** Em {r['n']} semanas com dados válidos nas duas bases, a associação linear é "
        f"**{sentido}** e de intensidade **{forca_r(r['r'])}** (r = {fmt_sinal(r['r'], 2)}).",
        f"**Coeficiente angular:** em média, cada US$ 1,00 a mais no barril de Brent esteve associado a uma "
        f"variação de {'−' if r['slope'] < 0 else '+'}{brl(abs(r['slope']), 4)} por litro no preço médio nacional "
        f"(≈ {'−' if d10 < 0 else '+'}{brl(abs(d10), 3)}/l para cada US$ 10,00 de diferença no Brent). É uma relação entre os níveis "
        f"observados, não uma previsão do repasse efetivo.",
        f"**Poder explicativo:** R² = {fmt(r['r2'], 2)}; o Brent, sozinho, responde por cerca de "
        f"{fmt(r['r2'] * 100, 0)}% da variabilidade semanal do preço nacional ({comb.lower()}) neste modelo linear, "
        f"e os {fmt((1 - r['r2']) * 100, 0)}% restantes não são explicados por ele.",
    ]
    if r["p"] == r["p"]:
        txt[-1] += (f" O coeficiente angular {'é' if r['p'] < 0.05 else 'não é'} estatisticamente distinto de zero "
                    f"ao nível de 5% ({'p < 0,0001' if r['p'] < 0.0001 else 'p = ' + fmt(r['p'], 4)}), considerando as semanas como independentes.")

    validos = {c: v for c, v in res.items() if v is not None}
    if len(validos) > 1:
        partes = [
            f"{c}: r = {fmt(v['r'], 2)}, R² = {fmt(v['r2'], 2)}, {fmt_sinal(v['slope'] * 10, 3)} R$/l por +US$ 10"
            for c, v in validos.items()
        ]
        melhor = max(validos, key=lambda c: validos[c]["r2"])
        sinais = {c: v["r"] > 0 for c, v in validos.items()}
        comp = "**Comparação entre os combustíveis.** " + "; ".join(partes) + ". "
        comp += f"O maior R² é o de **{melhor}** ({fmt(validos[melhor]['r2'], 2)}). "
        if len(set(sinais.values())) > 1:
            pos = [c for c, s in sinais.items() if s]
            neg = [c for c, s in sinais.items() if not s]
            comp += (
                f"O sinal da associação difere: positivo para {', '.join(pos)} e negativo para "
                f"{', '.join(neg)}."
            )
        txt.append(comp.strip())

    brent_min, brent_max = alin[config.COL_BRENT].min(), alin[config.COL_BRENT].max()
    txt.append(
        f"**Contexto temporal.** O período pareado vai de {alin['Data final'].min():%d/%m/%Y} a "
        f"{alin['Data final'].max():%d/%m/%Y}, com Brent entre US$ {fmt(brent_min)} e US$ {fmt(brent_max)} por "
        "barril, e inclui os três marcos geopolíticos (os pontos do gráfico estão coloridos por fase).")
    txt.append(
        "**Limitações.** (i) Regressão mostra associação estatística, **não causalidade**: não se afirma que o "
        "Brent cause a alta ou a queda dos preços. (ii) As séries são analisadas em nível, com tendência e "
        "autocorrelação, o que pode inflar r e R²; as semanas consecutivas não são independentes. "
        f"(iii) Amostra pequena ({r['n']} semanas). (iv) O preço dos combustíveis é a média nacional de revenda, em "
        "R$/l, e o Brent está em US$/barril, sem conversão cambial nem defasagem entre os dois. "
        "(v) Outros fatores (câmbio, tributos, política de preços, mistura de etanol, safra, demanda) não "
        "estão nas bases e não entram no modelo.")
    return "\n\n".join(txt)
