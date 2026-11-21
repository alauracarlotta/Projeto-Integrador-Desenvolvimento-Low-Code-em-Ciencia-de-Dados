"""Configuração centralizada do dashboard (caminhos, nomes, cores e marcos geopolíticos)."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

PASTA_APP = Path(__file__).resolve().parent

# ---------------------------------------------------------------- Arquivos de dados
ARQ_BRASIL = "Base_Semanal_Brasil_2026_Tratada.csv"
ARQ_ESTADOS = "Base_Semanal_Estados_2026_Tratada.csv"
ARQ_BRENT = "Base_Brent_Weekly_2026_Tratada.csv"
ARQUIVOS = (ARQ_BRASIL, ARQ_ESTADOS, ARQ_BRENT)

# Pastas onde as bases tratadas são procuradas, em ordem de prioridade.
# 1) variável PI_BASES_DIR, se definida  2) data/processed do projeto
# 3) bases legadas do projeto  4) subpasta "bases" e pasta do app
PASTA_BASES_PROJETO = PASTA_APP.parents[1] / "00.Bases" / "01.Tratadas"
PASTA_BASES_PROCESSADAS = PASTA_APP / "data" / "processed"


def pastas_candidatas() -> list[Path]:
    env = os.environ.get("PI_BASES_DIR")
    cand = [Path(env).expanduser()] if env else []
    cand += [PASTA_BASES_PROCESSADAS, PASTA_BASES_PROJETO, PASTA_APP / "data" / "processed", PASTA_APP]
    return cand


def pasta_bases() -> Path | None:
    """Primeira pasta candidata que contém os três arquivos; None se nenhuma contém."""
    for p in pastas_candidatas():
        try:
            if all((p / a).is_file() for a in ARQUIVOS):
                return p
        except OSError:
            continue
    return None


# ---------------------------------------------------------------- Combustíveis
# valor bruto na base ANP -> nome exibido no dashboard
PRODUTOS = {
    "ETANOL HIDRATADO": "Etanol",
    "GASOLINA COMUM": "Gasolina comum",
    "OLEO DIESEL S10": "Diesel S10",
}
ORDEM_COMBUSTIVEIS = ["Gasolina comum", "Etanol", "Diesel S10"]
CORES_COMBUSTIVEIS = {
    "Gasolina comum": "#FF993D",
    "Etanol": "#29D87C",
    "Diesel S10": "#48A6FF",
}

# ---------------------------------------------------------------- Regiões
REGIOES_BRUTO = {
    "NORTE": "Norte", "NORDESTE": "Nordeste", "CENTRO OESTE": "Centro-Oeste",
    "CENTRO-OESTE": "Centro-Oeste", "SUDESTE": "Sudeste", "SUL": "Sul",
}
ORDEM_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
CORES_REGIOES = {
    "Norte": "#27935C",
    "Nordeste": "#E7B82D",
    "Centro-Oeste": "#E58A38",
    "Sudeste": "#D95B5B",
    "Sul": "#4385C6",
}

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

# ---------------------------------------------------------------- Unidades federativas

UF_SIGLAS = {
    "Acre": "AC",
    "Alagoas": "AL",
    "Amapá": "AP",
    "Amazonas": "AM",
    "Bahia": "BA",
    "Ceará": "CE",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    "Goiás": "GO",
    "Maranhão": "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    "Pará": "PA",
    "Paraíba": "PB",
    "Paraná": "PR",
    "Pernambuco": "PE",
    "Piauí": "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    "Rondônia": "RO",
    "Roraima": "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    "Sergipe": "SE",
    "Tocantins": "TO",
}

UFS_PADRAO = ["AM", "GO", "PE", "RS", "SP"]

UFS_POR_REGIAO = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}

UF_REGIAO = {
    uf: regiao
    for regiao, ufs in UFS_POR_REGIAO.items()
    for uf in ufs
}

# ---------------------------------------------------------------- Brent
MESES_PT = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
            "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
COL_BRENT = "Brent (US$/barril)"
UNIDADE_BRENT = "US$ por barril (Europe Brent Spot Price FOB, semanal)"
COR_BRENT = "#57C9FF"
COR_MEDIA_MOVEL_BRENT = "#FFC267"

# ---------------------------------------------------------------- Marcos geopolíticos
DATA_BASE = pd.Timestamp("2026-02-28")   # início do conflito: referência das variações

MARCOS = [
    {
        "data": pd.Timestamp("2026-02-28"),
        "descricao": "Início do conflito (EUA × Irã)",
        "cor": "#6A1B9A",
        "dash": "dash"
    },
    {
        "data": pd.Timestamp("2026-04-13"),
        "descricao": "Início do bloqueio naval",
        "cor": "#BF360C",
        "dash": "dot"
    },
    {
        "data": pd.Timestamp("2026-08-30"),
        "descricao": "Persistência do bloqueio naval",
        "cor": "#263238",
        "dash": "dashdot"
    },
]

CORES_FASES = [
    "#7F8C8D",
    *[marco["cor"] for marco in MARCOS]
]

# ---------------------------------------------------------------- Ranking estadual

CORES_RANKING = {
    "3 maiores valores": "#D94A55",
    "3 menores valores": "#27AE60",
}

# ---------------------------------------------------------------- Indicadores e período

COL_PRECO = "Preço médio"
COL_VARIACAO = "Variação acumulada (%)"

ANO_PROJETO = 2026
MES_INICIAL = 1
MES_FINAL = 9

MESES_PT_BR = tuple(mes.upper() for mes in MESES_PT)

# ---------------------------------------------------------------- Textos fixos do roteiro
TXT_G1 = "Evolução do preço dos combustíveis a nível Brasil."
PERGUNTA_G1 = "Esse comportamento de preço varia por região do Brasil?"
TXT_G2 = (
    "Apesar de o preço médio dos combustíveis apresentar um comportamento semelhante ao observado "
    "no cenário nacional, identificamos diferenças importantes entre as regiões. Destacamos também "
    "os três estados com os menores preços e os três estados com os maiores preços."
)
PERGUNTA_G2 = "As variações de preço ao longo do tempo têm relação com o preço do petróleo?"
TXT_G3 = (
    "Conseguimos observar flutuações em momentos semelhantes entre o preço do Petróleo Brent "
    "e os preços dos combustíveis no Brasil."
)
PERGUNTA_G3 = (
    "Qual é o incremento no preço dos combustíveis (etanol, gasolina e diesel) associado "
    "à variação do preço do petróleo?"
)
