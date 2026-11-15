"""Dashboard ANP/EIA. Execute com: python -m streamlit run app.py."""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
FUELS = {
    'GASOLINA COMUM': 'Gasolina comum',
    'ETANOL HIDRATADO': 'Etanol hidratado',
    'OLEO DIESEL S10': 'Óleo diesel S10',
}
STATES = dict(
    zip([
        'ACRE', 'ALAGOAS', 'AMAPA', 'AMAZONAS', 'BAHIA',
        'CEARA', 'DISTRITO FEDERAL', 'ESPIRITO SANTO', 'GOIAS', 
        'MARANHAO', 'MATO GROSSO', 'MATO GROSSO DO SUL',
        'MINAS GERAIS', 'PARA', 'PARAIBA', 'PARANA', 
        'PERNAMBUCO', 'PIAUI', 'RIO DE JANEIRO', 'RIO GRANDE DO NORTE',
        'RIO GRANDE DO SUL', 'RONDONIA', 'RORAIMA', 'SANTA CATARINA',
        'SAO PAULO', 'SERGIPE', 'TOCANTINS'
    ],
    [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
        'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
        'SP', 'SE', 'TO'
    ])
)
DEFAULT_UFS = ['AM', 'GO', 'PE', 'RS', 'SP']
MONTHS = dict(
    zip([
        'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out',
        'nov', 'dez'
    ], range(1, 13))
)


@st.cache_data(show_spinner='Carregando bases ANP e EIA…')
def load_data(anp_stamp: int, brent_stamp: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lê os arquivos originais, incluindo preâmbulos e formatos brasileiros."""
    anp_path = ROOT / 'data/raw/semanal-estados-desde-2013.csv'
    with anp_path.open(encoding='utf-8-sig') as source:
        header = next(i for i, line in enumerate(source) if line.startswith('DATA INICIAL,'))
    anp = pd.read_csv(anp_path, skiprows=header, dtype=str)
    anp = anp.loc[anp['PRODUTO'].isin(FUELS)].copy()
    anp['Semana'] = pd.to_datetime(anp['DATA INICIAL'], format='%d/%m/%Y', errors='coerce')
    anp['Preço (R$/litro)'] = pd.to_numeric(anp['PREÇO MÉDIO REVENDA'].str.replace(',', '.', regex=False), errors='coerce')
    anp['UF'] = anp['ESTADO'].map(STATES)
    anp['Combustível'] = anp['PRODUTO'].map(FUELS)
    anp = anp[['Semana', 'UF', 'Combustível', 'Preço (R$/litro)']].dropna().sort_values('Semana')
    brent = pd.read_csv(ROOT / 'data/raw/RBRTEw.csv', skiprows=2, dtype=str)
    parts = brent.iloc[:, 0].str.lower().str.extract(r'([a-z]{3})\s+(\d{1,2}),\s*(\d{4})')
    dates = pd.to_datetime(pd.DataFrame({'year': parts[2], 'month': parts[0].map(MONTHS), 'day': parts[1]}), errors='coerce')
    brent = pd.DataFrame({'Data EIA': dates, 'Brent (US$/barril)': pd.to_numeric(brent.iloc[:, 1].str.replace(',', '.', regex=False), errors='coerce')}).dropna()
    # A ANP inicia a semana no domingo; a EIA publica a referência na sexta-feira.
    brent['Semana'] = brent['Data EIA'] - pd.to_timedelta((brent['Data EIA'].dt.day_of_week + 1) % 7, unit='D')
    return anp, brent.sort_values('Semana')


def set_ufs(values: list[str]) -> None:
    st.session_state['ufs'] = values


def line_chart(data: pd.DataFrame, y: str, color: str | None = None) -> alt.Chart:
    enc = {
        'x': alt.X('Semana:T', title='Semanas'),
        'y': alt.Y(f'{y}:Q', scale=alt.Scale(zero=False)),
        'tooltip': [
            alt.Tooltip('Semana:T', format='%d/%m/%Y'), alt.Tooltip(f'{y}:Q', format='.3f')
        ]
    }
    if color:
        enc['color'] = alt.Color(f'{color}:N')
        enc['tooltip'].append(alt.Tooltip(f'{color}:N'))
    return alt.Chart(data).mark_line(point=True).encode(**enc).properties(height=290).interactive()


def main() -> None:
    st.set_page_config(page_title='Combustíveis no Brasil | ANP e EIA', page_icon=':material/local_gas_station:', layout='wide')
    st.title('Instabilidade geopolítica e os preços dos combustíveis no Brasil')
    st.caption('Preços semanais de revenda por UF e petróleo Brent • Projeto Integrador SENAC')
    try:
        paths = [ROOT / 'data/raw' / name for name in ['semanal-estados-desde-2013.csv', 'RBRTEw.csv']]
        anp, brent = load_data(*(path.stat().st_mtime_ns for path in paths))
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        st.error(f'Não foi possível carregar os CSVs em data/raw: {exc}')
        st.stop()
    ufs = sorted(anp['UF'].unique())
    if 'ufs' not in st.session_state:
        st.session_state['ufs'] = DEFAULT_UFS
    months = sorted(anp['Semana'].dt.to_period('M').unique())
    preferred = [pd.Period('2026-02'), pd.Period('2026-08')]
    defaults = tuple(p if p in months else months[-1] for p in preferred)
    with st.container(border=True):
        fuel_col, date_col, uf_col, actions = st.columns([3, 3, 3, 2])
        with fuel_col:
            fuels = st.multiselect('Combustível', list(FUELS.values()), default=list(FUELS.values()), key='fuels')
        with date_col:
            period = st.select_slider('Período', options=months, value=defaults, format_func=lambda p: p.strftime('%m/%Y'), key='period')
        with uf_col:
            selected_ufs = st.multiselect('UFs selecionadas', ufs, key='ufs')
        with actions:
            st.button('Todas as 27 UFs', on_click=set_ufs, args=(ufs,), width='stretch', key='all_ufs')
            st.button('Restaurar seleção', on_click=set_ufs, args=(DEFAULT_UFS,), width='stretch', key='reset_ufs')
        if len(selected_ufs) > 5:
            st.caption('Mais de 5 UFs: a visualização pode ficar carregada. Use a legenda e o zoom para explorar.')
    start, end = period[0].start_time, period[1].end_time
    st.caption(f'Período selecionado: {start:%d/%m/%Y} a {end:%d/%m/%Y}')
    filtered = anp.loc[anp['Semana'].between(start, end) & anp['Combustível'].isin(fuels) & anp['UF'].isin(selected_ufs)]
    oil = brent.loc[brent['Semana'].between(start, end)]
    st.subheader('Evolução semanal dos combustíveis')
    if filtered.empty:
        st.info('Selecione pelo menos um combustível e uma UF com dados no período.')
    else:
        # Séries separadas por produto: não misturar médias de combustíveis diferentes.
        for fuel in fuels:
            subset = filtered.loc[filtered['Combustível'].eq(fuel)]
            if not subset.empty:
                with st.container(border=True):
                    st.markdown(f'**{fuel}**')
                    st.altair_chart(line_chart(subset, 'Preço (R$/litro)', 'UF'), width='stretch', alt=f'Evolução semanal de {fuel} nas UFs selecionadas')
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader('Comparação estadual')
            st.caption('Média aritmética das semanas disponíveis no período; cada combustível é apresentado separadamente.')
            if not filtered.empty:
                comparison = filtered.groupby(['UF', 'Combustível'], as_index=False)['Preço (R$/litro)'].mean()
                for fuel in fuels:
                    subset = comparison.loc[comparison['Combustível'].eq(fuel)]
                    if subset.empty:
                        continue
                    chart = alt.Chart(subset).mark_bar().encode(
                        x=alt.X('Preço (R$/litro):Q'), y=alt.Y('UF:N', sort='-x'),
                        tooltip=['UF:N', alt.Tooltip('Preço (R$/litro):Q', format='.3f')]
                    ).properties(title=fuel, height=max(160, 21 * len(subset)))
                    st.altair_chart(chart, width='stretch', alt=f'Ranking estadual do preço médio de {fuel}')
            else:
                st.info('Sem dados para a comparação estadual.')
    with right:
        with st.container(border=True):
            st.subheader('Evolução semanal do petróleo Brent')
            st.caption('US$/barril • Independente dos filtros de UFs e combustíveis.')
            if oil.empty:
                st.info('A EIA não possui dados no período selecionado.')
            else:
                st.altair_chart(line_chart(oil, 'Brent (US$/barril)'), width='stretch', alt='Cotação semanal do petróleo Brent em dólares por barril')
    st.divider()
    controls, plot = st.columns([1, 3])
    with controls:
        analysis_uf = st.selectbox('UF para análise', ufs, index=ufs.index('SP'), key='analysis_uf')
        st.caption('A UF para associação é independente da seleção dos gráficos acima.')
    with plot:
        with st.container(border=True):
            st.subheader('Associação Brent × combustíveis')
            association = anp.loc[anp['Semana'].between(start, end) & anp['UF'].eq(analysis_uf) & anp['Combustível'].isin(fuels)].merge(oil, on='Semana', how='inner', validate='many_to_one')
            if association.empty:
                st.info('Não há semanas em comum nas duas bases para esta seleção.')
            else:
                scatter = alt.Chart(association).mark_circle(size=65, opacity=.7).encode(
                    x=alt.X('Brent (US$/barril):Q', scale=alt.Scale(zero=False)),
                    y=alt.Y('Preço (R$/litro):Q', title='Combustível (R$/litro)', scale=alt.Scale(zero=False)),
                    color='Combustível:N', tooltip=['UF:N', 'Combustível:N', alt.Tooltip('Semana:T', format='%d/%m/%Y'), alt.Tooltip('Brent (US$/barril):Q', format='.2f'), alt.Tooltip('Preço (R$/litro):Q', format='.3f')]
                ).properties(height=350).interactive()
                st.altair_chart(scatter, width='stretch', alt=f'Associação entre Brent e preços de combustíveis em {analysis_uf}')
                summary = []
                for fuel, group in association.groupby('Combustível'):
                    corr = group['Brent (US$/barril)'].corr(group['Preço (R$/litro)']) if len(group) >= 3 and group['Brent (US$/barril)'].nunique() > 1 and group['Preço (R$/litro)'].nunique() > 1 else float('nan')
                    summary.append({'Combustível': fuel, 'Semanas pareadas': len(group), 'Correlação de Pearson': corr})
                st.dataframe(pd.DataFrame(summary), hide_index=True, column_config={'Correlação de Pearson': st.column_config.NumberColumn(format='%.3f')}, alt='Correlação de Pearson e quantidade de semanas por combustível')
            st.caption('Associação não implica causalidade. Valores nominais; sem conversão cambial ou ajuste de defasagem.')
    with st.expander('Metodologia e dados filtrados'):
        st.markdown('A ANP fornece médias estaduais de revenda em R$/litro. A comparação estadual usa a média simples das semanas disponíveis, sem ponderação por postos. A semana é identificada pelo domingo inicial da ANP; a referência da EIA é associada ao domingo da mesma semana. Somente semanas presentes nas duas bases entram na associação; lacunas não são preenchidas.')
        st.caption(f'ANP: {anp["Semana"].min():%d/%m/%Y} a {anp["Semana"].max():%d/%m/%Y} • EIA: {brent["Data EIA"].min():%d/%m/%Y} a {brent["Data EIA"].max():%d/%m/%Y}')
        st.dataframe(filtered, hide_index=True, alt='Registros ANP correspondentes aos filtros selecionados')
        st.download_button('Baixar dados filtrados (CSV)', filtered.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig'), file_name='combustiveis_filtrados.csv', mime='text/csv', key='download')
    st.caption('Fontes: ANP e EIA | Projeto Integrador SENAC')


if __name__ == '__main__':
    main()
