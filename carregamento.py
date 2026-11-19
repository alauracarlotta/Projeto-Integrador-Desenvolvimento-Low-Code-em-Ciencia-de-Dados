"""Leitura, validação e padronização das três bases tratadas.

Cada função devolve (DataFrame, avisos). Os avisos descrevem qualquer inconsistência encontrada
(linhas descartadas, datas fora do padrão etc.); nenhum valor é inventado ou preenchido.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import config


class ErroDados(Exception):
    """Problema de leitura ou de conteúdo das bases (mensagem pronta para o usuário)."""


# ---------------------------------------------------------------- utilidades
def _ler_csv(caminho: Path, **kw) -> pd.DataFrame:
    if not caminho.exists():
        raise ErroDados(f"Arquivo não encontrado: {caminho}")
    for enc in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(caminho, encoding=enc, **kw)
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:  # arquivo corrompido, separador errado etc.
            raise ErroDados(f"Não foi possível ler {caminho.name}: {type(e).__name__}: {e}") from e
    else:
        raise ErroDados(f"Não foi possível decodificar {caminho.name} (UTF-8/Latin-1).")
    if df.empty:
        raise ErroDados(f"O arquivo {caminho.name} está vazio.")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _exigir(df: pd.DataFrame, colunas: list[str], nome: str) -> None:
    faltam = [c for c in colunas if c not in df.columns]
    if faltam:
        raise ErroDados(f"{nome}: colunas ausentes {faltam}. Colunas encontradas: {list(df.columns)}")


def _datas_mdy(serie: pd.Series, coluna: str, nome: str) -> pd.Series:
    """Datas no formato M/D/AAAA (padrão das bases ANP tratadas)."""
    d = pd.to_datetime(serie.astype(str).str.strip(), format="%m/%d/%Y", errors="coerce")
    if d.isna().any():
        raise ErroDados(f"{nome}: {int(d.isna().sum())} valor(es) inválido(s) em '{coluna}' "
                        "(esperado M/D/AAAA).")
    return d.astype("datetime64[ns]")


def _preparar_anp(df: pd.DataFrame, nome: str, chave: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Padronização comum às bases ANP (Brasil e Estados)."""
    avisos: list[str] = []
    obrig = ["DATA INICIAL", "DATA FINAL", "PRODUTO", "NÚMERO DE POSTOS PESQUISADOS", "UNIDADE DE MEDIDA",
             "PREÇO MÉDIO REVENDA", "PREÇO MÍNIMO REVENDA", "PREÇO MÁXIMO REVENDA"]
    _exigir(df, obrig, nome)
    df = df.copy()

    df["PRODUTO"] = df["PRODUTO"].astype(str).str.strip().str.upper()
    desconhecidos = sorted(set(df["PRODUTO"]) - set(config.PRODUTOS))
    if desconhecidos:
        avisos.append(f"{nome}: produtos fora do escopo ignorados: {desconhecidos}.")
        df = df[df["PRODUTO"].isin(config.PRODUTOS)]
    df["Combustível"] = df["PRODUTO"].map(config.PRODUTOS)

    df["Data inicial"] = _datas_mdy(df["DATA INICIAL"], "DATA INICIAL", nome)
    df["Data final"] = _datas_mdy(df["DATA FINAL"], "DATA FINAL", nome)
    semanas_irreg = int(((df["Data final"] - df["Data inicial"]).dt.days != 6).sum())
    if semanas_irreg:
        avisos.append(f"{nome}: {semanas_irreg} linha(s) com período diferente de 7 dias.")

    for origem, destino in {"PREÇO MÉDIO REVENDA": "Preço médio",
                            "PREÇO MÍNIMO REVENDA": "Preço mínimo (posto)",
                            "PREÇO MÁXIMO REVENDA": "Preço máximo (posto)",
                            "NÚMERO DE POSTOS PESQUISADOS": "Postos pesquisados"}.items():
        df[destino] = pd.to_numeric(df[origem], errors="coerce")

    invalidos = df["Preço médio"].isna() | (df["Preço médio"] <= 0)
    if invalidos.any():
        avisos.append(f"{nome}: {int(invalidos.sum())} linha(s) com preço médio ausente/não positivo descartada(s).")
        df = df[~invalidos]

    unidades = set(df["UNIDADE DE MEDIDA"].astype(str).str.strip().str.lower())
    if unidades - {"r$/l"}:
        avisos.append(f"{nome}: unidades diferentes de R$/l encontradas: {sorted(unidades)}.")

    dup = df.duplicated(chave, keep="first")
    if dup.any():
        avisos.append(f"{nome}: {int(dup.sum())} linha(s) duplicada(s) em {chave} descartada(s) (mantida a primeira).")
        df = df[~dup]
    return df, avisos


# ---------------------------------------------------------------- bases
def carregar_brasil(pasta: Path) -> tuple[pd.DataFrame, list[str]]:
    nome = "Base Brasil"
    df = _ler_csv(Path(pasta) / config.ARQ_BRASIL, sep=";")
    df, avisos = _preparar_anp(df, nome, ["Data final", "Combustível"])
    cols = ["Combustível", "Data inicial", "Data final", "Preço médio",
            "Preço mínimo (posto)", "Preço máximo (posto)", "Postos pesquisados"]
    out = df[cols].sort_values(["Combustível", "Data final"]).reset_index(drop=True)
    if out.empty:
        raise ErroDados(f"{nome}: nenhuma linha válida após o tratamento.")
    return out, avisos


def carregar_estados(pasta: Path) -> tuple[pd.DataFrame, list[str]]:
    nome = "Base Estados"
    df = _ler_csv(Path(pasta) / config.ARQ_ESTADOS, sep=";")
    _exigir(df, ["REGIÃO", "ESTADO"], nome)
    df, avisos = _preparar_anp(df, nome, ["Data final", "Combustível", "ESTADO"])

    df["Região"] = df["REGIÃO"].astype(str).str.strip().str.upper().map(config.REGIOES_BRUTO)
    sem_regiao = df["Região"].isna()
    if sem_regiao.any():
        avisos.append(f"{nome}: {int(sem_regiao.sum())} linha(s) com região não reconhecida descartada(s).")
        df = df[~sem_regiao]
    df["ESTADO"] = df["ESTADO"].astype(str).str.strip().str.upper()
    df["Estado"] = df["ESTADO"].map(config.NOMES_UF).fillna(df["ESTADO"].str.title())

    multi = df.groupby("Estado")["Região"].nunique()
    if (multi > 1).any():
        avisos.append(f"{nome}: estados associados a mais de uma região: {list(multi[multi > 1].index)}.")

    cols = ["Combustível", "Estado", "Região", "Data inicial", "Data final", "Preço médio",
            "Preço mínimo (posto)", "Preço máximo (posto)", "Postos pesquisados"]
    out = df[cols].sort_values(["Combustível", "Estado", "Data final"]).reset_index(drop=True)
    if out.empty:
        raise ErroDados(f"{nome}: nenhuma linha válida após o tratamento.")
    return out, avisos


def carregar_brent(pasta: Path) -> tuple[pd.DataFrame, list[str]]:
    """Brent semanal. A coluna 'Date' vem como 'jan 02' (mês em português + dia); o ano está em 'Ano'."""
    nome = "Base Brent"
    avisos: list[str] = []
    df = _ler_csv(Path(pasta) / config.ARQ_BRENT)
    _exigir(df, ["Date", "Ano"], nome)
    col_preco = [c for c in df.columns if "brent" in c.lower()]
    if len(col_preco) != 1:
        raise ErroDados(f"{nome}: não foi possível identificar a coluna de preço (colunas: {list(df.columns)}).")
    col_preco = col_preco[0]

    partes = df["Date"].astype(str).str.strip().str.lower().str.split(r"\s+", expand=True)
    if partes.shape[1] < 2:
        raise ErroDados(f"{nome}: formato de 'Date' inesperado (esperado 'mês dia', ex.: 'jan 02').")
    mes = partes[0].map(config.MESES_PT)
    dia = pd.to_numeric(partes[1], errors="coerce")
    ano = pd.to_numeric(df["Ano"], errors="coerce")
    data = pd.to_datetime({"year": ano, "month": mes, "day": dia}, errors="coerce")
    if data.isna().any():
        raise ErroDados(f"{nome}: {int(data.isna().sum())} data(s) não puderam ser interpretadas.")

    out = pd.DataFrame({"Data": data.astype("datetime64[ns]"),
                        config.COL_BRENT: pd.to_numeric(df[col_preco], errors="coerce")})
    ruins = out[config.COL_BRENT].isna() | (out[config.COL_BRENT] <= 0)
    if ruins.any():
        avisos.append(f"{nome}: {int(ruins.sum())} linha(s) com preço ausente/não positivo descartada(s).")
        out = out[~ruins]
    dup = out.duplicated("Data", keep="first")
    if dup.any():
        avisos.append(f"{nome}: {int(dup.sum())} data(s) duplicada(s) descartada(s).")
        out = out[~dup]
    nao_sexta = int((out["Data"].dt.weekday != 4).sum())
    if nao_sexta:
        avisos.append(f"{nome}: {nao_sexta} data(s) que não caem em sexta-feira.")
    out = out.sort_values("Data").reset_index(drop=True)
    if out.empty:
        raise ErroDados(f"{nome}: nenhuma linha válida após o tratamento.")
    return out, avisos
