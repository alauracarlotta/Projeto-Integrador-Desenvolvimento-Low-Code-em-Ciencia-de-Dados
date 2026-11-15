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


DATA_DIR = ROOT / 'data' / 'processed'
FILES = ['Base_Semanal_Estados_2026.csv', 'Base_Semanal_Brasil_2026.csv', 'Base_Brent_Weekly_2026.csv']
PRICE = 'Preço (R$/litro)'
BRENT = 'Brent (US$/barril)'
CHANGE = 'Variação acumulada (%)'
COLORS = {'AM': '#24c77a', 'GO': '#ff943b', 'PE': '#ffd43b', 'RS': '#48a6ff', 'SP': '#fb5869', 'Brasil (média)': '#e6e0ec'}
EVENTS = pd.DataFrame({'Semana': pd.to_datetime(['2026-02-28', '2026-04-13', '2026-06-21']), 'Marco': ['28/02 · Início do conflito (EUA × Irã)', '13/04 · Escalada das tensões', '21/06 · Cessar-fogo (parcial)']})


@st.cache_data(show_spinner='Carregando bases tratadas ANP e EIA…')
def load_data(*stamps: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Os timestamps invalidam o cache quando um CSV tratado é atualizado."""
    tables = []
    for filename in FILES[:2]:
        path = DATA_DIR / filename
        with path.open(encoding='utf-8-sig') as source:
            header = next(i for i, line in enumerate(source) if line.startswith('DATA INICIAL;'))
        frame = pd.read_csv(path, sep=';', skiprows=header, dtype=str)
        frame = frame.loc[frame['PRODUTO'].isin(FUELS)].copy()
        frame['Semana'] = pd.to_datetime(frame['DATA INICIAL'], format='%m/%d/%Y', errors='coerce')
        frame[PRICE] = pd.to_numeric(frame['PREÇO MÉDIO REVENDA'].str.replace(',', '.', regex=False), errors='coerce')
        frame['Combustível'] = frame['PRODUTO'].map(FUELS)
        frame['UF'] = frame['ESTADO'].map(STATES) if 'ESTADO' in frame else 'Brasil (média)'
        tables.append(frame[['Semana', 'UF', 'Combustível', PRICE]].dropna().sort_values('Semana'))
    source = pd.read_csv(DATA_DIR / FILES[2], sep=';', dtype=str)
    parts = source['Date'].str.lower().str.extract(r'([a-z]{3})\s+(\d{1,2}),\s*(\d{4})')
    dates = pd.to_datetime(pd.DataFrame({'year': parts[2], 'month': parts[0].map(MONTHS), 'day': parts[1]}), errors='coerce')
    oil = pd.DataFrame({'Data EIA': dates, BRENT: pd.to_numeric(source.iloc[:, 1].str.replace(',', '.', regex=False), errors='coerce')}).dropna()
    oil['Semana'] = oil['Data EIA'] - pd.to_timedelta((oil['Data EIA'].dt.day_of_week + 1) % 7, unit='D')
    for frame in [*tables, oil]:
        if frame.empty:
            raise ValueError('Uma das bases tratadas não contém registros válidos.')
    if oil['Semana'].duplicated().any():
        raise ValueError('A base Brent contém semanas duplicadas.')
    return *tables, oil.sort_values('Semana')


def set_ufs(values: list[str]) -> None:
    st.session_state['ufs'] = values


def br_number(value: float, digits: int = 2) -> str:
    return f'{value:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def accumulated(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values('Semana').copy()
    baseline = frame.groupby(['UF', 'Combustível'])[PRICE].transform('first')
    frame[CHANGE] = (frame[PRICE] / baseline.where(baseline.ne(0)) - 1) * 100
    return frame


def uf_color(uf: str) -> str:
    """Use the same stable, distinct colors in the charts and their legends."""
    palette = ['#79c6d0', '#c2ad8d', '#bc8df5', '#ffb55a', '#ef77cf', '#a5d65b',
               '#e1cf58', '#a4a0ff', '#db9d74', '#ee91a8', '#8ed7bf', '#c4b4e9',
               '#f2bd8e', '#75a5e3', '#d0dc9c', '#bdb8ff', '#dcaf65', '#9cc7ef',
               '#f0a4ca', '#c8cf77', '#8bd0ab', '#b69bdc', '#91bfea', '#d0a692',
               '#f6a8a0', '#b6c9db', '#86c8b5']
    return COLORS.get(uf, palette[sorted(STATES.values()).index(uf)]) if uf != 'Brasil (média)' else COLORS[uf]


def uf_legend(values) -> None:
    # Render outside Vega's canvas so 27 UFs cannot consume the plot height.
    items = []
    for uf in sorted(set(values)):
        dash = 'dashed' if uf == 'Brasil (média)' else 'solid'
        items.append(f'<span style="display:inline-flex;align-items:center;gap:7px;white-space:nowrap"><span style="width:22px;border-top:3px {dash} {uf_color(uf)}"></span>{uf}</span>')
    st.markdown('<div aria-label="Legenda das UFs" style="display:flex;flex-wrap:wrap;gap:12px 20px;padding:8px 4px 16px;color:#eee8f4;font-size:13px">' + ''.join(items) + '</div>', unsafe_allow_html=True)


def styled(chart: alt.TopLevelMixin, height: int = 260) -> alt.TopLevelMixin:
    return chart.properties(height=height, autosize=alt.AutoSizeParams(type='fit-x', contains='padding')).configure(background='#17151b').configure_view(stroke=None).configure_axis(labelColor='#e6e0ec', titleColor='#e6e0ec', gridColor='#38323e', domainColor='#867b90', labelFontSize=11)


def timeline(data: pd.DataFrame, field: str, events: bool, national: bool = False) -> alt.TopLevelMixin:
    enc = dict(x=alt.X('Semana:T', title='Semanas', axis=alt.Axis(format='%m/%Y', tickCount='month', labelOverlap=True)), y=alt.Y(field+':Q', scale=alt.Scale(zero=False)), tooltip=[alt.Tooltip('Semana:T', format='%d/%m/%Y'), alt.Tooltip(field+':Q', format='.2f')])
    if 'UF' in data:
        domain = sorted(data['UF'].unique())
        enc['color'] = alt.Color('UF:N', scale=alt.Scale(domain=domain, range=[uf_color(uf) for uf in domain]), legend=None)
        enc['detail'] = alt.Detail('UF:N')
        enc['tooltip'].append(alt.Tooltip('UF:N'))
        if national:
            enc['strokeDash'] = alt.condition(alt.datum.UF == 'Brasil (média)', alt.value([6, 4]), alt.value([1, 0]))
    base = alt.Chart(data).mark_line(point=alt.OverlayMarkDef(size=22), color='#7fc9f5', strokeWidth=2).encode(**enc)
    if events:
        visible = EVENTS.loc[EVENTS['Semana'].between(data['Semana'].min(), data['Semana'].max())]
        rules = alt.Chart(visible).mark_rule(color='#bb75ec', strokeDash=[6, 4]).encode(x='Semana:T', tooltip=['Marco:N'])
        labels = alt.Chart(visible).mark_text(align='left', angle=270, dx=7, dy=8, color='#d9a5ff', fontSize=10).encode(x='Semana:T', y=alt.value(6), text='Marco:N')
        base = base + rules + labels
    return styled(base.interactive(), 360 if 'UF' in data else 260)


def main() -> None:
    st.set_page_config(page_title='Combustíveis no Brasil | ANP e EIA', page_icon='⛽', layout='wide')
    st.markdown("""<style>
    .stApp {background: #100f13; color: #f5f1f8; color-scheme: dark;}
    .block-container {max-width: 1600px; padding: 1.2rem 1.4rem 1rem;}
    h1 {font-size: clamp(1.5rem, 2.6vw, 2.5rem) !important; padding-bottom: .1rem !important;}
    h3 {font-size: 1.18rem !important; padding-top: 0 !important;}
    [data-testid="stVerticalBlockBorderWrapper"] > div {border-color: #706476 !important; border-radius: 12px; background: linear-gradient(120deg,#1c1920,#161419);}
    [data-testid="stMetric"] {background: #211d25; border: 1px solid #66596e; border-radius: 12px; padding: 12px 18px;}
    [data-testid="stMetricValue"] {font-size: 1.9rem; color: #fff;}
    [data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"] {color: #ded0eb;}
    [data-baseweb="select"] > div {background-color: #29232f; color: #fff; border-color: #796987;}
    [data-baseweb="tag"] {background-color: #803147; color: #fff;}
    .stButton button, .stDownloadButton button {background: #292130; color: #f5edff; border: 1px solid #9876ad;}
    [data-testid="stExpander"] {background: #1b171f; border-color: #796987;}
    </style>""", unsafe_allow_html=True)
    st.title('⛽ Instabilidade geopolítica e os preços dos combustíveis no Brasil')
    st.caption('Preços semanais de revenda por UF e petróleo Brent • Projeto Integrador SENAC')
    try:
        anp, brasil, brent = load_data(*( (DATA_DIR / name).stat().st_mtime_ns for name in FILES))
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        st.error(f'Não foi possível carregar os CSVs em data/processed: {exc}')
        st.stop()
    ufs = sorted(anp['UF'].unique())
    if 'ufs' not in st.session_state:
        st.session_state['ufs'] = [uf for uf in DEFAULT_UFS if uf in ufs]
    months = sorted(anp['Semana'].dt.to_period('M').unique())
    defaults = tuple(min(months, key=lambda p: abs(p.ordinal - target.ordinal)) for target in [pd.Period('2026-02'), pd.Period('2026-08')])
    # Reserve the indicators' position; populate after reading the current filters.
    indicators = st.container(border=True)
    with st.container(border=True):
        st.subheader('☷ Filtros')
        fc, dc, uc, actions = st.columns([3, 2, 2.5, 2])
        fuels = fc.multiselect('Combustível', list(FUELS.values()), default=list(FUELS.values()), key='fuels')
        period = dc.select_slider('Período', options=months, value=defaults, format_func=lambda p: p.strftime('%m/%Y'), key='period')
        selected_ufs = uc.multiselect('UFs selecionadas', ufs, key='ufs')
        actions.button('Todas as 27 UFs', on_click=set_ufs, args=(ufs,), width='stretch', key='all_ufs')
        actions.button('Restaurar seleção', on_click=set_ufs, args=(DEFAULT_UFS,), width='stretch', key='reset_ufs')
        with st.expander('Filtros avançados'):
            evolution_fuel = st.selectbox('Combustível da evolução semanal', fuels, key='evolution_fuel') if fuels else None
            st.caption('A evolução exibe um combustível por vez. O Brent depende apenas do período; a associação permite escolher sua própria UF.')
    start, end = period[0].start_time, period[1].end_time
    st.caption(f'Período analisado: {start:%d/%m/%Y} – {end:%d/%m/%Y}')
    filtered = anp.loc[anp['Semana'].between(start, end) & anp['Combustível'].isin(fuels) & anp['UF'].isin(selected_ufs)]
    national = brasil.loc[brasil['Semana'].between(start, end) & brasil['Combustível'].isin(fuels)]
    oil = brent.loc[brent['Semana'].between(start, end)]
    with indicators:
        st.subheader('▥ Indicadores-chave (Brasil)')
        st.caption('Preço nacional da última semana disponível e variação em relação à primeira semana do período, por combustível.')
        if not fuels:
            st.info('Selecione pelo menos um combustível.')
        else:
            for col, fuel in zip(st.columns(len(fuels)), fuels):
                series = national.loc[national['Combustível'].eq(fuel)].sort_values('Semana')
                if series.empty:
                    col.info(f'{fuel}: sem dados.')
                    continue
                first, last = series.iloc[0], series.iloc[-1]
                change = (last[PRICE] / first[PRICE] - 1) * 100 if first[PRICE] else None
                col.metric(fuel, f'R$ {br_number(last[PRICE])}', f'{br_number(change)}% desde {first["Semana"]:%d/%m}' if change is not None else None, delta_color='inverse', help=f'Última observação: {last["Semana"]:%d/%m/%Y}. Fonte: base semanal Brasil da ANP.')
    with st.container(border=True):
        st.subheader('〽 1. Evolução semanal dos preços de revenda por UF')
        st.caption(f'{evolution_fuel or "Selecione um combustível"} • Selecione o indicador, a referência nacional e os marcos geopolíticos.')
        a, b, c = st.columns([2, 1, 1.5])
        indicator = a.radio('Indicador', [PRICE, CHANGE], horizontal=True, label_visibility='collapsed', key='evolution_indicator')
        show_brasil = b.checkbox('Mostrar referência Brasil', value=True)
        show_events = c.checkbox('Mostrar marcos geopolíticos', value=True)
        series = filtered.loc[filtered['Combustível'].eq(evolution_fuel)]
        if show_brasil:
            series = pd.concat([series, national.loc[national['Combustível'].eq(evolution_fuel)]], ignore_index=True)
        if series.empty:
            st.info('Selecione um combustível e UFs com dados no período.')
        else:
            st.altair_chart(timeline(accumulated(series), indicator, show_events, show_brasil), width='stretch', theme=None)
            uf_legend(series['UF'])
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader('▥ 2. Comparação estadual')
        st.caption('Preço médio no período selecionado ou variação entre a primeira e a última semana disponível.')
        a, b = st.columns(2)
        comparison_fuel = a.selectbox('Combustível', fuels, key='comparison_fuel') if fuels else None
        comparison_indicator = b.selectbox('Indicador', [PRICE, CHANGE], key='comparison_indicator')
        all_states = st.radio('Abrangência', ['UFs selecionadas', 'Todas as UFs'], horizontal=True, label_visibility='collapsed') == 'Todas as UFs'
        state_data = anp.loc[anp['Semana'].between(start, end) & anp['Combustível'].eq(comparison_fuel) & (anp['UF'].isin(ufs if all_states else selected_ufs))]
        if state_data.empty:
            st.info('Sem dados para a comparação estadual.')
        else:
            frame = accumulated(state_data)
            comparison = frame.groupby('UF', as_index=False)[PRICE].mean() if comparison_indicator == PRICE else frame.groupby('UF', as_index=False).tail(1)
            color_domain = sorted(comparison['UF'].unique())
            color_range = [uf_color(uf) for uf in color_domain]
            bars = alt.Chart(comparison).mark_bar(cornerRadiusEnd=3).encode(x=alt.X(comparison_indicator+':Q', scale=alt.Scale(zero=False)), y=alt.Y('UF:N', sort='-x', title=None), color=alt.Color('UF:N', scale=alt.Scale(domain=color_domain, range=color_range), legend=None), tooltip=['UF:N', alt.Tooltip(comparison_indicator+':Q', format='.2f')])
            labels = bars.mark_text(align='right', dx=-6, color='white').encode(text=alt.Text(comparison_indicator+':Q', format='.2f'))
            st.altair_chart(styled(bars + labels, max(240, 26 * len(comparison))), width='stretch', theme=None)
            uf_legend(comparison['UF'])
    with right, st.container(border=True):
        st.subheader('♧ 3. Evolução semanal do petróleo Brent')
        st.caption('Cotação semanal em US$/barril • Fonte: EIA')
        if oil.empty:
            st.info('A EIA não possui dados no período selecionado.')
        else:
            st.altair_chart(timeline(oil, BRENT, show_events), width='stretch')
    with st.container(border=True):
        st.subheader('⁙ 4. Associação Brent × combustíveis')
        st.caption('Relação entre a cotação do Brent (US$/barril) e o preço do combustível (R$/litro) por UF selecionada.')
        controls, plot, stats = st.columns([1, 3.4, 1.2])
        analysis_uf = controls.selectbox('UF para análise', ufs, index=ufs.index('SP') if 'SP' in ufs else 0, key='analysis_uf')
        analysis_fuel = controls.selectbox('Combustível', fuels, key='analysis_fuel') if fuels else None
        association = anp.loc[anp['Semana'].between(start, end) & anp['UF'].eq(analysis_uf) & anp['Combustível'].eq(analysis_fuel)].merge(oil, on='Semana', how='inner', validate='many_to_one')
        if association.empty:
            plot.info('Não há semanas em comum para esta seleção.')
        else:
            scatter = alt.Chart(association).mark_circle(size=55, color='#fb6879', opacity=.9).encode(x=alt.X(BRENT+':Q', scale=alt.Scale(zero=False)), y=alt.Y(PRICE+':Q', scale=alt.Scale(zero=False)), tooltip=[alt.Tooltip('Semana:T', format='%d/%m/%Y'), alt.Tooltip(BRENT+':Q', format='.2f'), alt.Tooltip(PRICE+':Q', format='.3f')])
            valid = len(association) >= 3 and association[BRENT].nunique() > 1 and association[PRICE].nunique() > 1
            chart = scatter + scatter.transform_regression(BRENT, PRICE).mark_line(color='#e9deef', strokeDash=[4, 4]) if valid else scatter
            plot.altair_chart(styled(chart, 200), width='stretch')
            stats.metric('Correlação de Pearson', br_number(association[BRENT].corr(association[PRICE]), 3) if valid else 'Indisponível')
            stats.metric('Semanas pareadas', len(association))
        stats.caption('Associação não implica causalidade. Valores nominais, sem conversão cambial ou ajuste de defasagem.')
    with st.expander('▣ Metodologia e fontes'):
        st.markdown('As três fontes são lidas exclusivamente de `data/processed`. Os indicadores e a referência Brasil usam a **base nacional da ANP**, sem calcular uma média das UFs. O ranking estadual usa a média simples das semanas disponíveis, sem ponderação por postos. A variação acumulada parte da primeira observação disponível de cada série no período. Lacunas não são preenchidas.')
        st.markdown('As datas dos CSVs ANP seguem **mês/dia/ano**. A referência semanal EIA é associada ao domingo inicial da mesma semana ANP; apenas semanas presentes nas duas fontes entram na associação. Correlação e regressão são exibidas quando há pelo menos três pares e variabilidade nas duas séries.')
        st.caption('Os marcos geopolíticos reproduzem as datas e os rótulos fornecidos na imagem de referência; são anotações de contexto, sem validação histórica nesta implementação e sem inferência causal.')
        st.caption('Fontes: ANP (preços de combustíveis) e EIA (Brent). Os números exibidos são calculados dos CSVs e podem diferir do protótipo.')
    with st.expander('⇩ Dados filtrados e download'):
        st.dataframe(filtered, hide_index=True)
        for label, frame, filename in [('Combustíveis por UF', filtered, 'combustiveis_filtrados.csv'), ('Referência Brasil', national, 'brasil_filtrado.csv'), ('Petróleo Brent', oil, 'brent_filtrado.csv')]:
            st.download_button(f'Baixar {label} (CSV)', frame.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig'), file_name=filename, mime='text/csv', key=filename)
    st.caption(f'Fontes: ANP e EIA | Projeto Integrador SENAC • Bases locais atualizadas em {pd.Timestamp(max((DATA_DIR / name).stat().st_mtime for name in FILES), unit="s").strftime("%d/%m/%Y")}')


if __name__ == '__main__':
    main()
