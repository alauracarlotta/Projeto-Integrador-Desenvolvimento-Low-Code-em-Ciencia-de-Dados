
import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
PROCESSED = Path("data/processed")

PRODUTOS = {
    "ETANOL HIDRATADO": "Etanol",
    "GASOLINA COMUM": "Gasolina comum",
    "OLEO DIESEL S10": "Diesel S10",
}

INICIO = pd.Timestamp("2026-01-01")
FIM = pd.Timestamp("2026-09-30")


def comparar(nome, arquivo_raw, arquivo_tratado, formato_data, decimal):
    original = pd.read_csv(
        RAW / arquivo_raw,
        skiprows=17,
        encoding="utf-8-sig",
        dtype=str
    )
    original.columns = original.columns.str.strip()

    original["Data inicial"] = pd.to_datetime(
        original["DATA INICIAL"],
        format=formato_data,
        errors="coerce"
    )
    original["Combustível"] = original["PRODUTO"].map(PRODUTOS)
    original["Preço original"] = pd.to_numeric(
        original["PREÇO MÉDIO REVENDA"]
        .str.replace(decimal, ".", regex=False),
        errors="coerce"
    )

    original = original.loc[
        original["Data inicial"].between(INICIO, FIM)
        & original["Combustível"].notna()
    ].copy()

    tratado = pd.read_csv(
        PROCESSED / arquivo_tratado,
        sep=";",
        encoding="utf-8-sig",
        dtype=str
    )
    tratado.columns = tratado.columns.str.strip()

    tratado["Data inicial"] = pd.to_datetime(
        tratado["DATA INICIAL"],
        format="%m/%d/%Y",
        errors="coerce"
    )
    tratado["Combustível"] = tratado["PRODUTO"].map(PRODUTOS)
    tratado["Preço tratado"] = pd.to_numeric(
        tratado["PREÇO MÉDIO REVENDA"],
        errors="coerce"
    )

    chaves = ["Data inicial", "Combustível"]

    if nome == "ANP Estados":
        original["Estado"] = original["ESTADO"].str.strip().str.upper()
        tratado["Estado"] = tratado["ESTADO"].str.strip().str.upper()
        chaves.append("Estado")

    comparacao = original.merge(
        tratado,
        on=chaves,
        how="outer",
        indicator=True,
        suffixes=("_raw", "_processed"),
        validate="one_to_one"
    )

    ambos = comparacao["_merge"].eq("both")
    diferenca = (
        comparacao["Preço original"] - comparacao["Preço tratado"]
    ).abs()

    divergentes = ambos & diferenca.gt(0.001)

    print(f"\n{'=' * 50}")
    print(nome)
    print(f"{'=' * 50}")
    print("Registros originais filtrados:", len(original))
    print("Registros tratados:", len(tratado))
    print("Registros pareados:", int(ambos.sum()))
    print("Preços divergentes:", int(divergentes.sum()))
    print("Somente no original:", int(comparacao["_merge"].eq("left_only").sum()))
    print("Somente no tratado:", int(comparacao["_merge"].eq("right_only").sum()))

    if divergentes.any():
        print("\nExemplos de divergências:")
        print(
            comparacao.loc[
                divergentes,
                chaves + ["Preço original", "Preço tratado"]
            ].head(10).to_string(index=False)
        )


comparar(
    "ANP Brasil",
    "semanal-brasil-desde-2013.csv",
    "Base_Semanal_Brasil_2026_Tratada.csv",
    "%m/%d/%Y",
    "."
)

comparar(
    "ANP Estados",
    "semanal-estados-desde-2013.csv",
    "Base_Semanal_Estados_2026_Tratada.csv",
    "%d/%m/%Y",
    ","
)
