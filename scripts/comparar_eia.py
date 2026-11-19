
import pandas as pd
from pathlib import Path

RAW = Path("data/raw/RBRTEw.csv")
PROCESSED = Path("data/processed/Base_Brent_Weekly_2026_Tratada.csv")

MESES = {
    "jan": "01", "fev": "02", "mar": "03",
    "abr": "04", "mai": "05", "jun": "06",
    "jul": "07", "ago": "08", "set": "09",
    "out": "10", "nov": "11", "dez": "12",
}

def converter_data(valor):
    partes = str(valor).strip().replace(",", "").split()

    if len(partes) != 3:
        return pd.NaT

    mes, dia, ano = partes
    mes = MESES.get(mes.lower())

    if mes is None:
        return pd.NaT

    return pd.to_datetime(
        f"{ano}-{mes}-{int(dia):02d}",
        errors="coerce"
    )


# 1. Ler a EIA original
original = pd.read_csv(
    RAW,
    skiprows=2,
    dtype=str,
    encoding="utf-8-sig"
)

original.columns = ["Data original", "Preço original"]

original["Data"] = original["Data original"].map(converter_data)
original["Preço original"] = pd.to_numeric(
    original["Preço original"].str.replace(",", ".", regex=False),
    errors="coerce"
)

# 2. Ler a EIA tratada
tratado = pd.read_csv(PROCESSED, dtype=str)

tratado["Data"] = (
    tratado["Date"].str.strip()
    + ", "
    + tratado["Ano"].str.strip()
).map(converter_data)

coluna_preco = [
    col for col in tratado.columns
    if "Weekly Europe Brent" in col
][0]

tratado["Preço tratado"] = pd.to_numeric(
    tratado[coluna_preco],
    errors="coerce"
)

# 3. Comparar somente as datas da base tratada
comparacao = tratado[["Data", "Preço tratado"]].merge(
    original[["Data", "Preço original"]],
    on="Data",
    how="left",
    validate="one_to_one",
    indicator=True
)

diferenca = (
    comparacao["Preço tratado"] - comparacao["Preço original"]
).abs()

divergentes = (
    comparacao["_merge"].eq("both")
    & diferenca.gt(0.001)
)

ausentes = comparacao["_merge"].eq("left_only")

print("\n" + "=" * 50)
print("VALIDAÇÃO EIA BRENT")
print("=" * 50)
print("Registros tratados:", len(tratado))
print("Registros pareados:", int(comparacao["_merge"].eq("both").sum()))
print("Preços divergentes:", int(divergentes.sum()))
print("Datas ausentes no original:", int(ausentes.sum()))

if divergentes.any():
    print("\nDIVERGÊNCIAS:")
    print(
        comparacao.loc[
            divergentes,
            ["Data", "Preço original", "Preço tratado"]
        ].to_string(index=False)
    )

if ausentes.any():
    print("\nDATAS NÃO ENCONTRADAS:")
    print(
        comparacao.loc[
            ausentes,
            ["Data", "Preço tratado"]
        ].to_string(index=False)
    )
