"""Auditoria não destrutiva das bases tratadas ANP/EIA do Projeto Integrador.
Execute da raiz do repositório: python scripts/auditar_bases.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
import carregamento as cg

OUT = ROOT / 'docs' / 'validacao'
OUT.mkdir(parents=True, exist_ok=True)
RESULTADOS = []

def registrar(base, teste, status, detalhe):
    RESULTADOS.append({'base': base, 'teste': teste, 'status': status, 'detalhe': str(detalhe)})
    print(f'[{status}] {base}: {teste} | {detalhe}')

def auditar_anp(df, nome, chave):
    registrar(nome, 'carregamento', 'PASSOU' if len(df) else 'FALHOU', f'{len(df)} registros')
    datas = pd.to_datetime(df['Data inicial'], errors='coerce')
    invalidas = int(datas.isna().sum())
    registrar(nome, 'datas válidas', 'PASSOU' if not invalidas else 'FALHOU', invalidas)
    inicio, fim = pd.Timestamp('2026-01-01'), pd.Timestamp('2026-09-30')
    fora = int((~datas.between(inicio, fim)).sum())
    registrar(nome, 'jan-set/2026', 'PASSOU' if not fora else 'ATENÇÃO', f'{fora} datas fora da janela')
    preco = pd.to_numeric(df['Preço médio'], errors='coerce')
    ruins = int((preco.isna() | (preco <= 0)).sum())
    registrar(nome, 'preços positivos', 'PASSOU' if not ruins else 'FALHOU', ruins)
    dup = df.duplicated(chave, keep=False)
    registrar(nome, 'chaves únicas', 'PASSOU' if not dup.any() else 'FALHOU', int(dup.sum()))
    if dup.any():
        df.loc[dup].to_csv(OUT / f'duplicados_{nome.lower()}.csv', index=False, sep=';', decimal=',', encoding='utf-8-sig')
    meses = sorted(datas.dropna().dt.strftime('%Y-%m').unique().tolist())
    registrar(nome, 'meses encontrados', 'ATENÇÃO', ', '.join(meses))
    if nome == 'Estados':
        registrar(nome, 'UFs distintas', 'ATENÇÃO', df['Estado'].nunique())
        registrar(nome, 'regiões distintas', 'ATENÇÃO', df['Região'].nunique())
    registrar(nome, 'combustíveis encontrados', 'ATENÇÃO', ', '.join(sorted(df['Combustível'].dropna().unique())))
    return df

def main():
    pasta = config.pasta_bases()
    if pasta is None:
        print('FALHOU: três CSVs não encontrados. Configure PI_BASES_DIR ou use bases/.')
        sys.exit(2)
    print('Pasta das bases:', pasta)
    try:
        brasil, wb = cg.carregar_brasil(pasta)
        estados, we = cg.carregar_estados(pasta)
        brent, wt = cg.carregar_brent(pasta)
    except Exception as exc:
        print('FALHOU ao carregar:', exc)
        sys.exit(2)
    for nome, avisos in [('Brasil', wb), ('Estados', we), ('Brent', wt)]:
        registrar(nome, 'avisos do carregador', 'ATENÇÃO' if avisos else 'PASSOU', ' | '.join(avisos) if avisos else 'nenhum')
    auditar_anp(brasil, 'Brasil', ['Data inicial', 'Combustível'])
    auditar_anp(estados, 'Estados', ['Data inicial', 'Estado', 'Combustível'])
    registrar('Brent', 'carregamento', 'PASSOU' if len(brent) else 'FALHOU', f'{len(brent)} registros')
    registrar('Brent', 'datas únicas', 'PASSOU' if not brent['Data'].duplicated().any() else 'FALHOU', int(brent['Data'].duplicated().sum()))
    registrar('Brent', 'datas em sexta-feira', 'PASSOU' if brent['Data'].dt.day_of_week.eq(4).all() else 'ATENÇÃO', int(brent['Data'].dt.day_of_week.ne(4).sum()))
    registrar('Brent', 'preços positivos', 'PASSOU' if brent[config.COL_BRENT].gt(0).all() else 'FALHOU', int(brent[config.COL_BRENT].le(0).sum()))
    brent = brent.copy()
    brent['Semana ANP'] = brent['Data'] - pd.to_timedelta((brent['Data'].dt.day_of_week + 1) % 7, unit='D')
    registrar('Brent', 'semana ANP única', 'PASSOU' if not brent['Semana ANP'].duplicated().any() else 'FALHOU', int(brent['Semana ANP'].duplicated().sum()))
    brent[['Data', 'Semana ANP', config.COL_BRENT]].to_csv(OUT / 'auditoria_eia.csv', index=False, sep=';', decimal=',', encoding='utf-8-sig')
    amostra = brasil.merge(brent, left_on='Data inicial', right_on='Semana ANP', how='inner', validate='many_to_one')
    amostra[['Data inicial', 'Combustível', 'Preço médio', 'Data', config.COL_BRENT]].to_csv(OUT / 'pareamento_anp_eia.csv', index=False, sep=';', decimal=',', encoding='utf-8-sig')
    registrar('ANP × EIA', 'pareamento', 'PASSOU' if len(amostra) else 'FALHOU', f'{len(amostra)} pares Brasil/combustível')
    relatorio = pd.DataFrame(RESULTADOS)
    relatorio.to_csv(OUT / 'resultado_auditoria.csv', index=False, sep=';', encoding='utf-8-sig')
    falhas = (relatorio.status == 'FALHOU').sum()
    print(f'\nRESUMO: {len(relatorio)} verificações; {falhas} falha(s). Relatórios em {OUT}')
    sys.exit(1 if falhas else 0)

if __name__ == '__main__':
    main()
