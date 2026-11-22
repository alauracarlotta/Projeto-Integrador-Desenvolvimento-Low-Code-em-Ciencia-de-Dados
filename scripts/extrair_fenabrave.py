import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
PASTA_PDFS = RAIZ_PROJETO / "data" / "raw" / "fenabrave"
PASTA_SAIDA = RAIZ_PROJETO / "data" / "processed"

ARQUIVO_SAIDA = PASTA_SAIDA / "Base_Mensal_Eletricos_2026.csv"

registros = []

for arquivo in sorted(PASTA_PDFS.glob("*.pdf")):

    leitor = PdfReader(arquivo)

    # Identifica o mês de referência pelo nome do arquivo.
    mes = pd.to_datetime(
        arquivo.name[:7],
        format="%Y_%m"
    ).strftime("%Y-%m")

    for numero, pagina in enumerate(leitor.pages, start=1):

        texto = pagina.extract_text() or ""

        # Seleciona exclusivamente a categoria de automóveis.
        if "Mercado de Eletrificados Autos" not in texto:
            continue

        if "Mercado de Eletrificados Autos e Comerciais Leves" in texto:
            continue

        # Extrai o primeiro valor da linha B) Elétricos.
        resultado = re.search(
            r"B\)\s*Elétricos\s+([\d.]+)",
            texto
        )

        if resultado:
            quantidade = int(resultado.group(1).replace(".", ""))

            registros.append({
                "Mes": mes,
                "Emplacamentos_Eletricos": quantidade,
                "Arquivo_Origem": arquivo.name,
                "Pagina": numero
            })

            print(f"[OK] {mes}: {quantidade:,} unidades")

            break

    else:
        print(f"[ERRO] Registro não localizado: {arquivo.name}")

# Consolidação dos dados.
df = pd.DataFrame(
    registros,
    columns=[
        "Mes",
        "Emplacamentos_Eletricos",
        "Arquivo_Origem",
        "Pagina"
    ]
).sort_values("Mes")

# Validação da cobertura temporal.
meses_esperados = pd.period_range(
    "2026-01", "2026-09", freq="M"
).astype(str).tolist()

if df["Mes"].tolist() != meses_esperados:
    raise ValueError(
        "Base incompleta, com meses duplicados ou fora do período esperado."
    )

if (df["Emplacamentos_Eletricos"] <= 0).any():
    raise ValueError("Foram encontradas quantidades inválidas.")

# Exportação do CSV.
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

df.to_csv(
    ARQUIVO_SAIDA,
    index=False,
    encoding="utf-8"
)

print("\nBASE CONSOLIDADA:")
print(df.to_string(index=False))

print(f"\nTotal de registros: {len(df)}")
print(f"Arquivo gerado: {ARQUIVO_SAIDA}")
