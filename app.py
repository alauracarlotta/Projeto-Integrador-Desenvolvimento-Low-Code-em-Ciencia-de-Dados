"""Dashboard integrado SENAC | executar: streamlit run app.py"""
from __future__ import annotations
import pandas as pd
import graficos as gr
import streamlit as st
import config
import carregamento as cg
import analises as an

st.set_page_config(page_title='Instabilidade geopolítica | SENAC', page_icon='⛽', layout='wide')

CSS_PATH = config.PASTA_APP / 'assets' / 'css' / 'styles.css'

st.markdown(
    f'<style>{CSS_PATH.read_text(encoding="utf-8")}</style>',
    unsafe_allow_html=True
)

DEFAULT = config.UFS_PADRAO
UF_REGION = config.UF_REGIAO

REGION_COLORS = config.CORES_REGIOES
FUEL_COLORS = config.CORES_COMBUSTIVEIS

EVENTS = [
    (
        marco["data"].strftime("%Y-%m-%d"),
        marco["descricao"],
        marco["cor"]
    )
    for marco in config.MARCOS
]

PRICE = config.COL_PRECO
CHANGE = config.COL_VARIACAO
MESES_PT_BR = config.MESES_PT_BR


def formatar_mes_ano(data):
    return f"{MESES_PT_BR[data.month - 1]}/{data.year}"

def fmt(v,n=2):
    return an.fmt(float(v),n) if pd.notna(v) else '—'

def render_legend(items, title=None):
    legend_items = "".join(
        f'''
        <span class="chart-legend-item">
            <span class="chart-legend-dot"
                style="background-color: {color};">
            </span>
            <span>{label}</span>
        </span>
        '''
        for label, color in items.items()
    )

    legend_title = (
        f'<div class="chart-legend-title">{title}</div>'
        if title else ""
    )

    st.markdown(
        f'''
        {legend_title}
        <div class="chart-legend">
            {legend_items}
        </div>
        ''',
        unsafe_allow_html=True
    )

@st.cache_data(show_spinner='Lendo e validando bases ANP/EIA…')
def load(folder):
    return cg.carregar_bases(folder)

folder=config.pasta_bases()
if folder is None:
    st.error('As três bases tratadas não foram encontradas em `data/processed/`. Verifique os arquivos ou defina `PI_BASES_DIR`.')
    st.code('\n'.join(config.ARQUIVOS))
    st.stop()
try:
    brasil,estados,brent,warnings=load(str(folder))
except Exception as exc:
    st.error(f'Falha ao ler as bases: {exc}')
    st.stop()


ufs = sorted(estados['UF'].dropna().unique().tolist())
fuels = list(config.ORDEM_COMBUSTIVEIS)
if 'ufs' not in st.session_state:
    st.session_state.ufs = [u for u in DEFAULT if u in ufs]
if 'fuels' not in st.session_state:
    st.session_state.fuels = fuels.copy()


def select_all():
    st.session_state.ufs = ufs.copy()


def reset():
    st.session_state.ufs = [u for u in DEFAULT if u in ufs]

st.title(
    "⛽ Instabilidade geopolítica e os preços dos combustíveis no Brasil",
)

st.caption(
    "Preços semanais de revenda por UF e petróleo Brent "
    "• Projeto Integrador SENAC • Jan/2026 a Set/2026",
    help=(
        "Para personalizar a aparência do dashboard, "
        "clique nos três pontos (⋮) no canto superior direito "
        "e selecione o tema desejado:\n\n"
        "- ☀️ Light: tema claro.\n"
        "- 🌙 Dark: tema escuro.\n"
        "- 💻 System: tema do dispositivo."
    )
)

indicators=st.container(border=True)
with st.container(border=True):
    st.subheader('⚑ Filtros')
    c1,c2,c3,c4=st.columns([3,2.2,3,1.8])
    selected_fuels=c1.multiselect('Combustível',fuels,key='fuels')
    # Limites Jan–Set são a janela do projeto; dados não existentes nunca são interpolados.
    months = [
    pd.Period(f'{config.ANO_PROJETO}-{m:02d}')
    for m in range(config.MES_INICIAL, config.MES_FINAL + 1)
]
    selected_period = c2.select_slider('Período',options=months,value=(months[0], months[-1]),format_func=formatar_mes_ano)
    selected_ufs=c3.multiselect('UFs selecionadas',ufs,key='ufs')
    c4.button('Todas as 27 UFs',on_click=select_all)
    c4.button('Restaurar seleção',on_click=reset)
    with st.expander('Filtros avançados'):
        st.caption('O indicador de cada gráfico pode ser alterado na própria seção. A análise Brent × combustíveis permite escolher uma UF independente dos demais gráficos.')
    show_events=st.checkbox('Mostrar marcos geopolíticos',value=True,key='global_events')
    if show_events:
        cols=st.columns(3)
        for col,(date,title,color) in zip(cols,EVENTS):
            col.markdown(f'<span style="color:{color}">●</span> **{pd.Timestamp(date):%d/%m/%Y}** · {title}',unsafe_allow_html=True)

start = selected_period[0].start_time
end = selected_period[1].end_time

b, e, o = cg.filtrar_bases(
    brasil,
    estados,
    brent,
    start,
    end,
    selected_fuels
)
with indicators:
    st.subheader('▥ Indicadores-chave (Brasil)')

    st.caption(
        'Preço médio da última semana disponível e variação '
        'desde a primeira semana disponível no período filtrado.'
    )

    indicadores = an.kpis(b).set_index('Combustível')

    cols = st.columns(3)

    for col, fuel in zip(cols, fuels):

        if fuel not in indicadores.index:
            col.metric(fuel, 'Sem dados')
            continue

        dados = indicadores.loc[fuel]

        preco_atual = dados['Preço atual']
        variacao = dados[CHANGE]
        semana_inicial = dados['Semana inicial']

        col.metric(
            fuel,
            f'R$ {fmt(preco_atual)}',
            f'{fmt(variacao)}% desde {semana_inicial:%d/%m}',
            delta_color='inverse'
        )

with st.container(border=True):
    st.markdown('**Questões da análise**')

    cols = st.columns(4)

    titles = [
        '1. Cenário nacional',
        '2. Diferenças regionais',
        '3. Cenário internacional',
        '4. Relação estatística'
    ]

    questions = [
        'Como os preços evoluíram?',
        'O comportamento é uniforme?',
        'Como o Brent se comportou?',
        'Há associação com o Brent?'
    ]

    for col, title, question in zip(cols, titles, questions):
        col.markdown(
            f"""
            <div class="analysis-title">
                {title}
            </div>
            <div class="analysis-question">
                {question}
            </div>
            """,
            unsafe_allow_html=True
        )

with st.container(border=True):
    st.subheader('1. Cenário nacional: evolução semanal dos preços')

    if b.empty:
        st.info('Não há dados nacionais no período e combustíveis selecionados.')
    else:
        fig = gr.grafico_brasil(b, show_events, start, end)

        st.altair_chart(
            fig,
            use_container_width=True,
            theme="streamlit"
        )

        render_legend(FUEL_COLORS)

st.subheader('2. Diferenças regionais')
left,right=st.columns(2)

with left, st.container(border=True):
    st.markdown('#### 2.1 Evolução do preço médio por região')

    reg_fuel = st.selectbox(
        'Combustível (regiões)',
        selected_fuels if selected_fuels else fuels,
        key='region_fuel'
    )

    region = an.preco_por_regiao(e, reg_fuel)

    if region.empty:
        st.info('Sem dados regionais.')
    else:
        fig = gr.grafico_regioes(region, show_events, start, end)

        st.altair_chart(
            fig,
            use_container_width=True,
            theme="streamlit"
        )

        render_legend(REGION_COLORS, title='Região')

        st.caption(
            'Média simples dos preços médios estaduais disponíveis '
            'em cada região. Não ponderada pelo número de postos.'
        )

with right,st.container(border=True):
    st.markdown('#### 2.2 Comparação estadual')
    a1,a2,a3=st.columns(3)
    rank_mode=a1.selectbox('Indicador',['Preço médio (R$/litro)','Variação no período (%)'],key='rank_mode')
    rank_scope = a2.selectbox('Visualização', ['3 mais caros e 3 mais baratos','UFs selecionadas','Todas as 27 UFs','Por região'], key='rank_scope', help='A opção "UFs selecionadas" utiliza os estados definidos no filtro global, no topo do dashboard.')
    rank_fuel=a3.selectbox('Combustível',selected_fuels if selected_fuels else fuels,key='rank_fuel')
    selected_region = None
    if rank_scope == 'Por região':
        selected_region = st.selectbox( 'Região', list(REGION_COLORS.keys()), key='selected_region', help='Exibe todas as UFs da região escolhida, independentemente do filtro global de UFs.')
    grouped = an.ranking_estadual(e, rank_fuel)

    if grouped.empty:
        st.info('Sem dados estaduais.')
    else:
        metric='Média' if rank_mode.startswith('Preço') else 'Variação (%)'
        if rank_scope == 'UFs selecionadas':
            grouped = grouped[grouped['UF'].isin(selected_ufs)]
        elif rank_scope == 'Por região':
            region_ufs = [
                uf for uf, region in UF_REGION.items()
                if region == selected_region
            ]
            grouped = grouped[grouped['UF'].isin(region_ufs)]
            st.caption(
                f'Exibindo todas as UFs da região {selected_region} '
                f'({len(grouped)} UFs com dados disponíveis). '
                'Esta visualização é independente do filtro global de UFs.'
            )
        elif rank_scope.startswith('3 mais'):
            grouped = an.ranking_extremos(grouped, metric)
            if metric == 'Média':
                st.caption('Comparação entre as 3 UFs com maiores e menores preços médios.')
            else:
                st.caption('Comparação entre as 3 UFs com maiores e menores variações percentuais.')

        if grouped.empty:
            st.info('Selecione ao menos uma UF com dados.')
        else:
            grouped = grouped.assign(
                Região=grouped.UF.map(UF_REGION)
            )

            ranking_extremos = rank_scope.startswith('3 mais')

            if ranking_extremos:
                legend_items = config.CORES_RANKING
                legend_title = 'Classificação'
            else:
                legend_items = {
                    region: color
                    for region, color in REGION_COLORS.items()
                    if region in grouped['Região'].values
                }

                legend_title = 'Região'

            fig = gr.grafico_ranking(
                grouped,
                metric,
                ranking_extremos
            )

            st.altair_chart(
                fig,
                use_container_width=True,
                theme="streamlit"
            )

            render_legend(
                legend_items,
                title=legend_title
            )


with st.container(border=True):
    st.subheader('3. Cenário internacional: petróleo Brent')

    c1, c2 = st.columns([2, 1])

    oil_mode = c1.radio(
        'Visualização',
        [config.COL_BRENT, CHANGE],
        horizontal=True,
        key='oil_mode'
    )

    smooth = c2.checkbox(
        'Sobrepor média móvel de 4 semanas',
        value=False
    )

    if o.empty:
        st.info('Sem observações do Brent no período.')
    else:
        oil = an.variacao_brent(o)

        latest = oil.iloc[-1]

        a1, a2 = st.columns(2)

        a1.metric(
            'Última cotação',
            f'US$ {fmt(latest[config.COL_BRENT])}'
        )

        a2.metric(
            'Variação no período',
            f'{fmt(latest[CHANGE])}%'
        )

        y = (
            config.COL_BRENT
            if oil_mode == config.COL_BRENT
            else CHANGE
        )

        fig = gr.grafico_brent(
            oil,
            y,
            smooth,
            show_events,
            start,
            end
        )

        st.altair_chart(
            fig,
            use_container_width=True,
            theme="streamlit"
        )

with st.container(border=True):
    st.subheader('4. Relação estatística: Brent × preço dos combustíveis')

    # O modo Brasil reproduz a análise nacional da imagem original.
    # A seleção de uma UF utiliza os preços estaduais da ANP.
    c_uf, c_fuel, c_all = st.columns([2.2, 2.2, 1.2])
    uf_options = ['Brasil (média nacional)'] + ufs
    selected_uf = c_uf.selectbox('Estado / abrangência', uf_options, key='d4_uf')
    fuel = c_fuel.selectbox('Combustível', fuels, key='d4_fuel')

    if 'd4_all' not in st.session_state:
        st.session_state.d4_all = False
    def activate_all_ufs():
        st.session_state.d4_all = not st.session_state.d4_all
    c_all.button('Todas as 27 UFs' if not st.session_state.d4_all else 'Voltar à seleção',
                on_click=activate_all_ufs, key='d4_all_button')
    all_mode = st.session_state.d4_all

    st.caption('Cada ponto é uma semana com observação válida nas duas bases: a cotação do Brent '
            '(sexta-feira) é associada à semana ANP (domingo a sábado) que a contém. '
            'Sem interpolação nem preenchimento.')

    # Usa a mesma regra de pareamento da versão original.
    # Ao contrário do gráfico anterior, o recorte temporal é aplicado antes da regressão.
    oil_weeks = (
        o[['Semana', 'Data', config.COL_BRENT]]
        .drop_duplicates('Semana')
        .rename(columns={'Data': 'Data Brent'})
    )
    if selected_uf == 'Brasil (média nacional)':
        selected_source = b[b['Combustível'] == fuel][['Semana', PRICE]].copy()
    else:
        selected_source = e[(e['Combustível'] == fuel) & (e['UF'] == selected_uf)][['Semana', PRICE]].copy()
    selected_pairs = an.parear_semanas(
        selected_source,
        oil_weeks,
        validacao='one_to_one'
    )
    regression = an.regressao(selected_pairs[config.COL_BRENT], selected_pairs[PRICE]) if not selected_pairs.empty else None

    # Indicadores exatamente acima do gráfico, como no dashboard original.
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric('Coef. angular (R/l por US$ 1)', fmt(regression['slope'], 4) if regression else '—',
            help='Inclinação da regressão linear simples: variação em R$/litro associada a US$ 1 no Brent.')
    m2.metric('Intercepto (R$/l)', fmt(regression['intercept'], 3) if regression else '—',
            help='Valor estimado do preço do combustível quando Brent = 0; não é previsão realista.')
    m3.metric('R²', fmt(regression['r2'], 3) if regression else '—',
            help='Coeficiente de determinação da regressão linear simples.')
    m4.metric('Correlação de Pearson (r)', fmt(regression['r'], 3) if regression else '—',
            help='Intensidade e direção da associação linear, sem inferência de causalidade.')
    m5.metric('Semanas (n)', str(regression['n']) if regression else str(len(selected_pairs)))

    if all_mode:
        st.info('Exibindo as 27 UFs no mesmo gráfico. Os cinco indicadores acima continuam '
                'referentes à abrangência escolhida no filtro, evitando calcular uma regressão '
                'que trate observações estaduais da mesma semana como independentes.')
        source = e[e['Combustível'] == fuel][['Semana', 'UF', PRICE]].copy()
        pairs = an.parear_semanas(
            source,
            oil_weeks
        )
    else:
        pairs = selected_pairs.copy()
        pairs['UF'] = 'Brasil' if selected_uf.startswith('Brasil') else selected_uf

    if pairs.empty:
        st.warning(
            'Não há semanas com observações pareadas para essa seleção.'
        )
    else:
        fig = gr.grafico_dispersao(
            pairs,
            regression,
            fuel,
            selected_uf,
            all_mode,
            ufs
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            theme="streamlit"
        )
    st.caption(
        'Fonte: ANP e EIA. Associação estatística não demonstra causalidade. '
        'A linha de regressão e os indicadores correspondem à abrangência selecionada.')

with st.expander('▣ Metodologia e fontes'):
    st.markdown('**Fontes:** ANP, preços semanais nacionais e estaduais; EIA, Brent semanal. As datas ANP são semanas iniciadas aos domingos; cada cotação semanal do Brent é pareada com a semana ANP que a contém. Não há interpolação de semanas ausentes. A média regional é simples entre UFs disponíveis; o ranking por preço usa a média semanal no período filtrado. Os indicadores nacionais utilizam a base Brasil, não a média de estados.')
    st.markdown('**Marcos geopolíticos:** as datas e descrições foram fornecidas no escopo do projeto; são anotações contextuais que exigem validação documental antes da publicação. Correlação não prova causalidade.')
    for warning in warnings:
        st.warning(warning)
with st.expander('▥ Regressões e dados pareados'):

    st.caption(
        f'Abrangência: {selected_uf} | '
        f'Período: {formatar_mes_ano(start)} a '
        f'{formatar_mes_ano(end)}'
    )

    if all_mode:
        st.info(
            'As regressões abaixo correspondem à abrangência '
            'selecionada no gráfico 4, mesmo quando todas '
            'as UFs são exibidas no gráfico.'
        )

    # Seleciona a base conforme a abrangência.
    if selected_uf == 'Brasil (média nacional)':
        regression_source = b.copy()
    else:
        regression_source = e[
            e['UF'] == selected_uf
        ].copy()

    # Pareamento semanal entre ANP e Brent.
    paired_data = an.parear_semanas(
        regression_source[
            ['Semana', 'Combustível', PRICE]
        ],
        oil_weeks
    )

    if paired_data.empty:
        st.info(
            'Não há dados pareados disponíveis '
            'para os filtros selecionados.'
        )

    else:
        regression_table = an.tabela_regressoes(
            paired_data,
            selected_fuels
        )

        st.markdown('**Resultados das regressões**')

        st.dataframe(
            regression_table,
            hide_index=True,
            use_container_width=True,
            column_config={
                'Coef. angular (R$/l por US$ 1)':
                    st.column_config.NumberColumn(
                        format='%.4f'
                    ),
                'Intercepto (R$/l)':
                    st.column_config.NumberColumn(
                        format='%.4f'
                    ),
                'R²':
                    st.column_config.NumberColumn(
                        format='%.4f'
                    ),
                'r de Pearson':
                    st.column_config.NumberColumn(
                        format='%.4f'
                    ),
                'p-valor':
                    st.column_config.NumberColumn(
                        format='%.3e'
                    )
            }
        )

        st.caption(
            'O p-valor convencional considera as observações '
            'independentes. A autocorrelação temporal pode '
            'comprometer essa hipótese. Correlação não '
            'implica causalidade.'
        )
        paired_table = an.tabela_dados_pareados(
            paired_data
        )

        available_fuels = [
            comb for comb in fuels
            if comb in paired_table.columns
        ]

        st.markdown('**Dados semanais pareados**')

        st.dataframe(
            paired_table,
            hide_index=True,
            use_container_width=True,
            column_config={
                'Data Brent':
                    st.column_config.DateColumn(
                        format='DD/MM/YYYY'
                    ),
                'Data final':
                    st.column_config.DateColumn(
                        format='DD/MM/YYYY'
                    ),
                config.COL_BRENT:
                    st.column_config.NumberColumn(
                        format='%.2f'
                    ),
                **{
                    combustion:
                        st.column_config.NumberColumn(
                            format='%.2f'
                        )
                    for combustion in available_fuels
                }
            }
        )

        st.download_button(
            'Baixar dados pareados (CSV)',
            paired_table.to_csv(
                index=False,
                sep=';',
                decimal=',',
                date_format='%d/%m/%Y'
            ).encode('utf-8-sig'),
            file_name='dados_pareados.csv',
            mime='text/csv',
            key='download_paired_data'
        )

with st.expander('⇩ Dados filtrados e download'):
    filtered=e[e.UF.isin(selected_ufs)]
    st.dataframe(filtered,hide_index=True,use_container_width=True)
    for label, frame in [('estados', filtered), ('brasil', b), ('brent', o)]:
        st.download_button(
            f'Baixar {label}.csv',
            frame.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig'),
            file_name=f'{label}_filtrado.csv',
            mime='text/csv'
        )
st.caption('Fontes: ANP e EIA | Projeto Integrador SENAC | Dados calculados das bases locais, sem valores simulados')
