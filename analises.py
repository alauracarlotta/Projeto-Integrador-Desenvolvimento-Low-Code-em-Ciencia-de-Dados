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

MESES_NOME = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
    "setembro", "outubro", "novembro", "dezembro"
]


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
def kpis(df: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Indicadores por combustível no recorte `df`; a referência de 28/02 vem da base completa `ref`."""
    linhas = []
    for comb in config.ORDEM_COMBUSTIVEIS:
        d = df[df["Combustível"] == comb].sort_values("Data final")
        if d.empty:
            continue
        r = ref[(ref["Combustível"] == comb) & (ref["Data final"] == config.DATA_BASE)]
        base = float(r["Preço médio"].iloc[0]) if not r.empty else np.nan
        atual = d.iloc[-1]
        imax, imin = d["Preço médio"].idxmax(), d["Preço médio"].idxmin()
        linhas.append({
            "Combustível": comb,
            "Semana mais recente": atual["Data final"],
            "Preço atual": float(atual["Preço médio"]),
            "Preço em 28/02": base,
            "Variação desde 28/02 (%)": (atual["Preço médio"] / base - 1) * 100 if base == base else np.nan,
            "Média do período": float(d["Preço médio"].mean()),
            "Maior preço": float(d.loc[imax, "Preço médio"]), "Semana do maior": d.loc[imax, "Data final"],
            "Menor preço": float(d.loc[imin, "Preço médio"]), "Semana do menor": d.loc[imin, "Data final"],
        })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- Gráfico 2: regiões e ranking
def preco_por_regiao(est: pd.DataFrame, comb: str) -> pd.DataFrame:
    """Média simples dos preços médios dos estados de cada região, por semana (dados válidos de cada semana)."""
    d = est[est["Combustível"] == comb]
    out = (d.groupby(["Data final", "Região"], as_index=False).agg(**{"Preço médio": ("Preço médio", "mean"), "Estados": ("Estado", "nunique")}))
    out["Região"] = pd.Categorical(out["Região"], config.ORDEM_REGIOES, ordered=True)
    return out.sort_values(["Região", "Data final"]).reset_index(drop=True)


def ranking_ultimo_mes(est: pd.DataFrame, comb: str, n: int = 3):
    """Três estados mais baratos e três mais caros no último mês/ano da base (mês da DATA INICIAL da semana).

    Devolve (periodo_mensal, semanas_incluidas, tabela_completa, top6 ou None).
    O preço de cada estado é a média dos preços médios semanais das semanas do mês.
    """
    mes = est["Data inicial"].dt.to_period("M").max()
    no_mes = est[est["Data inicial"].dt.to_period("M") == mes]
    semanas = sorted(no_mes["Data inicial"].unique())
    d = no_mes[no_mes["Combustível"] == comb]
    g = (
        d.groupby(["Estado", "Região"], as_index=False)
        .agg(**{"Preço médio": ("Preço médio", "mean"), "Semanas": ("Data final", "nunique")})
        .sort_values("Preço médio").reset_index(drop=True)
    )
    if len(g) < 2 * n:
        return mes, semanas, g, None
    caros = g.tail(n).sort_values("Preço médio", ascending=False).assign(Grupo="Mais caros")
    baratos = g.head(n).assign(Grupo="Mais baratos")      # já em ordem crescente
    return mes, semanas, g, pd.concat([caros, baratos], ignore_index=True)


def rotulo_mes(periodo: pd.Period) -> str:
    return f"{MESES_NOME[periodo.month - 1]}/{periodo.year}"


def variacao_por_estado(est: pd.DataFrame, comb: str, data_ref: pd.Timestamp, data_fim: pd.Timestamp) -> pd.DataFrame:
    """Variação % do preço médio de cada estado entre duas semanas (função herdada do app de regiões)."""
    d = est[est["Combustível"] == comb]
    a = d[d["Data final"] == data_ref].set_index("Estado")["Preço médio"]
    b = d[d["Data final"] == data_fim].set_index("Estado")["Preço médio"]
    out = pd.DataFrame({"Preço inicial": a, "Preço final": b}).dropna()
    out["Variação (R$/l)"] = out["Preço final"] - out["Preço inicial"]
    out["Variação (%)"] = (out["Preço final"] / out["Preço inicial"] - 1) * 100
    return out.sort_values("Variação (%)", ascending=False).reset_index()


# ---------------------------------------------------------------- Alinhamento Brasil × Brent
def alinhar_semanas(brasil: pd.DataFrame, brent: pd.DataFrame):
    """Associa cada observação do Brent (sexta-feira) à semana ANP (domingo–sábado) que a contém.

    Só ficam as semanas com observação válida nas duas bases; nada é preenchido ou interpolado.
    Devolve (tabela longa por combustível, lista de datas do Brent sem semana correspondente).
    """
    semanas = (brasil[["Data inicial", "Data final"]].drop_duplicates().sort_values("Data inicial"))
    b = pd.merge_asof(brent.sort_values("Data"), semanas, left_on="Data", right_on="Data inicial", direction="backward")
    ok = b["Data final"].notna() & (b["Data"] <= b["Data final"])
    descartadas = list(b.loc[~ok, "Data"])
    b = b[ok]
    if b.duplicated("Data final").any():
        raise ValueError("Mais de uma observação do Brent cai na mesma semana ANP; alinhamento ambíguo.")
    alin = b.merge(
        brasil[["Combustível", "Data inicial", "Data final", "Preço médio"]],
        on=["Data inicial", "Data final"], how="inner"
    )
    alin = alin.rename(columns={"Data": "Data Brent"}).sort_values(["Combustível", "Data final"])
    return alin.reset_index(drop=True), descartadas


def fases_conflito(datas: pd.Series) -> pd.Series:
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


def regressoes(alin: pd.DataFrame) -> dict[str, dict | None]:
    """Uma regressão independente por combustível: preço médio nacional (y) ~ Brent (x)."""
    out = {}
    for comb in config.ORDEM_COMBUSTIVEIS:
        d = alin[alin["Combustível"] == comb]
        out[comb] = regressao(d[config.COL_BRENT], d["Preço médio"]) if not d.empty else None
    return out


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
