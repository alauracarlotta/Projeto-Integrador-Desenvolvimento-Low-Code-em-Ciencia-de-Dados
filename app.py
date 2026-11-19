"""Dashboard integrado SENAC | executar: streamlit run app.py"""
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
import numpy as np
import altair as alt
import plotly.graph_objects as go
import graficos as gr
import streamlit as st
import config
import carregamento as cg
import analises as an

st.set_page_config(page_title='Instabilidade geopolítica | SENAC', page_icon='⛽', layout='wide')
st.markdown('''<style>
.stApp{background:#110e16;color:#f6f1f8}.block-container{max-width:1540px;padding-top:1.1rem}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#665073!important;border-radius:13px;background:#18131e}
[data-testid="stMetric"]{background:#241b2b;border:1px solid #574560;border-radius:10px;padding:12px}
[data-testid="stMetricValue"]{color:#f9f4ff;font-size:1.75rem}
[data-testid="stExpander"]{background:#21182a;border-color:#654875}
.stButton button{background:#34203f;color:#f8efff;border:1px solid #9b60b4;width:100%}
[data-baseweb="tag"]{background-color:#a73753!important}
section[data-testid="stSidebar"]{display:none}
h1{font-size:2.0rem!important}h3{font-size:1.25rem!important}
</style>''', unsafe_allow_html=True)

ROOT=Path(__file__).resolve().parent
UF_SIGLAS={'Acre':'AC','Alagoas':'AL','Amapá':'AP','Amazonas':'AM','Bahia':'BA','Ceará':'CE','Distrito Federal':'DF','Espírito Santo':'ES','Goiás':'GO','Maranhão':'MA','Mato Grosso':'MT','Mato Grosso do Sul':'MS','Minas Gerais':'MG','Pará':'PA','Paraíba':'PB','Paraná':'PR','Pernambuco':'PE','Piauí':'PI','Rio de Janeiro':'RJ','Rio Grande do Norte':'RN','Rio Grande do Sul':'RS','Rondônia':'RO','Roraima':'RR','Santa Catarina':'SC','São Paulo':'SP','Sergipe':'SE','Tocantins':'TO'}
DEFAULT=['AM','GO','PE','RS','SP']
REGIONS={'Norte':['AC','AP','AM','PA','RO','RR','TO'],'Nordeste':['AL','BA','CE','MA','PB','PE','PI','RN','SE'],'Centro-Oeste':['DF','GO','MT','MS'],'Sudeste':['ES','MG','RJ','SP'],'Sul':['PR','RS','SC']}
UF_REGION={u:r for r,ufs in REGIONS.items() for u in ufs}
REGION_COLORS={'Norte':'#27935C','Nordeste':'#E7B82D','Centro-Oeste':'#E58A38','Sudeste':'#D95B5B','Sul':'#4385C6'}
FUEL_COLORS={'Gasolina comum':'#FF993D','Etanol':'#29D87C','Diesel S10':'#48A6FF'}
EVENTS=[('2026-02-28','Início do conflito (EUA × Irã)','#B65AF0'),('2026-04-13','Início do bloqueio naval','#FF9700'),('2026-08-30','Persistência do bloqueio naval','#2586FF')]
PRICE='Preço médio'; CHANGE='Variação acumulada (%)'

def fmt(v,n=2):
    return an.fmt(float(v),n) if pd.notna(v) else '—'

def chart_base(chart,height=320):
    return (chart.properties(height=height).configure(background='#18131e')
        .configure_view(stroke=None)
        .configure_axis(labelColor='#E5DDEC',titleColor='#E5DDEC',gridColor='#392D41',domainColor='#705D79')
        .configure_legend(labelColor='#E5DDEC',titleColor='#E5DDEC'))

def marks(chart,begin,end,enabled):
    if not enabled:return chart
    for date,title,color in EVENTS:
        dt=pd.Timestamp(date)
        if begin<=dt<=end:
            line=alt.Chart(pd.DataFrame({'date':[dt],'event':[title]})).mark_rule(color=color,strokeDash=[5,4],strokeWidth=2).encode(x='date:T',tooltip='event:N')
            chart=chart+line
    return chart

def line_chart(df,y,colorfield,domain,colors,begin,end,events, ytitle, height=315):
    base=alt.Chart(df).mark_line(point=alt.OverlayMarkDef(size=28),strokeWidth=2).encode(
        x=alt.X('Semana:T',title='Semanas',axis=alt.Axis(format='%b/%Y',tickCount='month')),
        y=alt.Y(f'{y}:Q',title=ytitle,scale=alt.Scale(zero=False)),
        color=alt.Color(f'{colorfield}:N',scale=alt.Scale(domain=domain,range=colors),legend=alt.Legend(orient='right',title=None)),
        tooltip=[alt.Tooltip('Semana:T',format='%d/%m/%Y'),alt.Tooltip(f'{colorfield}:N'),alt.Tooltip(f'{y}:Q',format='.3f')])
    return chart_base(marks(base,begin,end,events),height)

@st.cache_data(show_spinner='Lendo e validando bases ANP/EIA…')
def load(folder):
    brasil,wb=cg.carregar_brasil(folder)
    estados,we=cg.carregar_estados(folder)
    brent,wt=cg.carregar_brent(folder)
    estados['UF']=estados['Estado'].map(UF_SIGLAS)
    return brasil,estados,brent,wb+we+wt

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

# A semana ANP é identificada pela data inicial (domingo); o Brent é associado ao domingo de sua semana.
for frame in (brasil,estados):frame['Semana']=frame['Data inicial']
brent['Semana']=brent['Data']-pd.to_timedelta((brent['Data'].dt.dayofweek+1)%7,unit='D')
ufs=sorted(estados['UF'].dropna().unique().tolist())
fuels=list(config.ORDEM_COMBUSTIVEIS)
if 'ufs' not in st.session_state:st.session_state.ufs=[u for u in DEFAULT if u in ufs]
if 'fuels' not in st.session_state:st.session_state.fuels=fuels.copy()

def select_all():st.session_state.ufs=ufs.copy()
def reset():st.session_state.ufs=[u for u in DEFAULT if u in ufs]

st.title('⛽ Instabilidade geopolítica e os preços dos combustíveis no Brasil')
st.caption('Preços semanais de revenda por UF e petróleo Brent  •  Projeto Integrador SENAC  •  Jan/2026 a Set/2026')
indicators=st.container(border=True)
with st.container(border=True):
    st.subheader('⚑ Filtros')
    c1,c2,c3,c4=st.columns([3,2.2,3,1.8])
    selected_fuels=c1.multiselect('Combustível',fuels,key='fuels')
    # Limites Jan–Set são a janela do projeto; dados não existentes nunca são interpolados.
    months=[pd.Period(f'2026-{m:02d}') for m in range(1,10)]
    selected_period=c2.select_slider('Período',options=months,value=(months[0],months[-1]),format_func=lambda x:x.strftime('%m/%Y'))
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

start,end=selected_period[0].start_time,selected_period[1].end_time
b=brasil[brasil.Semana.between(start,end)&brasil['Combustível'].isin(selected_fuels)].copy()
e=estados[estados.Semana.between(start,end)&estados['Combustível'].isin(selected_fuels)].copy()
o=brent[brent.Semana.between(start,end)].copy()
with indicators:
    st.subheader('▥ Indicadores-chave (Brasil)')
    st.caption('Preço médio da última semana disponível e variação desde a primeira semana disponível no período filtrado.')
    cols=st.columns(3)
    for col,fuel in zip(cols,fuels):
        d=b[b['Combustível']==fuel].sort_values('Semana')
        if d.empty:col.metric(fuel,'Sem dados');continue
        first,last=d.iloc[0],d.iloc[-1]
        delta=(last[PRICE]/first[PRICE]-1)*100 if first[PRICE] else np.nan
        col.metric(fuel,f'R$ {fmt(last[PRICE])}',f'{fmt(delta)}% desde {first.Semana:%d/%m}',delta_color='inverse')

with st.container(border=True):
    st.markdown('**Questões da análise**')
    cols=st.columns(4)
    for col,title,question in zip(cols,['1. Cenário nacional','2. Diferenças regionais','3. Cenário internacional','4. Relação estatística'],['Como os preços evoluíram?','O comportamento é uniforme?','Como o Brent se comportou?','Há associação com o Brent?']):
        col.markdown(f'**{title}**  \n{question}')

with st.container(border=True):
    st.subheader('1. Cenário nacional: evolução semanal dos preços')
    if b.empty:st.info('Não há dados nacionais no período e combustíveis selecionados.')
    else:
        d=b.sort_values('Semana').copy()
        fig=line_chart(d,PRICE,'Combustível',fuels,[FUEL_COLORS[f] for f in fuels],start,end,show_events,'R$/litro')
        st.altair_chart(fig,use_container_width=True,theme=None)

st.subheader('2. Diferenças regionais')
left,right=st.columns(2)
with left,st.container(border=True):
    st.markdown('#### 2.1 Evolução do preço médio por região')
    reg_fuel=st.selectbox('Combustível (regiões)',selected_fuels if selected_fuels else fuels,key='region_fuel')
    region=e[e['Combustível']==reg_fuel].groupby(['Semana','Região'],as_index=False)[PRICE].mean()
    if region.empty:st.info('Sem dados regionais.')
    else:
        fig=line_chart(region,PRICE,'Região',list(REGION_COLORS),list(REGION_COLORS.values()),start,end,show_events,'Preço médio (R$/litro)',300)
        st.altair_chart(fig,use_container_width=True,theme=None)
        st.caption('Média simples dos preços médios estaduais disponíveis em cada região. Não ponderada pelo número de postos.')
with right,st.container(border=True):
    st.markdown('#### 2.2 Comparação estadual')
    a1,a2,a3=st.columns(3)
    rank_mode=a1.selectbox('Indicador',['Preço médio (R$/litro)','Variação no período (%)'],key='rank_mode')
    rank_scope=a2.selectbox('Visualização',['3 mais caros e 3 mais baratos','UFs selecionadas','Todas as 27 UFs'],key='rank_scope')
    rank_fuel=a3.selectbox('Combustível',selected_fuels if selected_fuels else fuels,key='rank_fuel')
    state=e[e['Combustível']==rank_fuel].sort_values('Semana')
    if state.empty:st.info('Sem dados estaduais.')
    else:
        grouped=state.groupby('UF',as_index=False).agg(**{'Média':(PRICE,'mean'),'Inicial':(PRICE,'first'),'Final':(PRICE,'last'),'Semanas':('Semana','nunique')})
        grouped['Variação (%)']=(grouped['Final']/grouped['Inicial']-1)*100
        metric='Média' if rank_mode.startswith('Preço') else 'Variação (%)'
        if rank_scope=='UFs selecionadas':grouped=grouped[grouped.UF.isin(selected_ufs)]
        if rank_scope.startswith('3 mais'):
            ordered=grouped.sort_values([metric,'UF'])
            grouped=pd.concat([ordered.head(3),ordered.tail(3)]).drop_duplicates('UF')
            st.caption('Extremos entre todas as UFs: mais caros/baratos por preço ou maiores altas/menores variações em %.')
        if grouped.empty:st.info('Selecione ao menos uma UF com dados.')
        else:
            grouped=grouped.assign(Região=grouped.UF.map(UF_REGION))
            plot=alt.Chart(grouped).mark_bar(cornerRadiusEnd=3).encode(
                x=alt.X(f'{metric}:Q',title='R$/litro' if metric=='Média' else 'Variação (%)',scale=alt.Scale(zero=metric=='Média')),
                y=alt.Y('UF:N',sort=alt.SortField(field=metric,order='descending'),title=None),
                color=alt.Color('Região:N',scale=alt.Scale(domain=list(REGION_COLORS),range=list(REGION_COLORS.values())),legend=alt.Legend(orient='bottom')),
                tooltip=['UF:N','Região:N',alt.Tooltip(f'{metric}:Q',format='.2f')])
            st.altair_chart(chart_base(plot,max(260,len(grouped)*20)),use_container_width=True,theme=None)

with st.container(border=True):
    st.subheader('3. Cenário internacional: petróleo Brent')
    c1,c2=st.columns([2,1])
    oil_mode=c1.radio('Visualização',['Brent (US$/barril)',CHANGE],horizontal=True,key='oil_mode')
    smooth=c2.checkbox('Sobrepor média móvel de 4 semanas',value=False)
    if o.empty:st.info('Sem observações do Brent no período.')
    else:
        oil=o.sort_values('Semana').copy()
        oil[CHANGE]=(oil[config.COL_BRENT]/oil[config.COL_BRENT].iloc[0]-1)*100
        latest=oil.iloc[-1]
        a1,a2=st.columns(2)
        a1.metric('Última cotação',f'US$ {fmt(latest[config.COL_BRENT])}')
        a2.metric('Variação no período',f'{fmt(latest[CHANGE])}%')
        y=config.COL_BRENT if oil_mode.startswith('Brent') else CHANGE
        base=alt.Chart(oil).mark_line(point=True,color='#57C9FF',strokeWidth=2.5).encode(
            x=alt.X('Semana:T',title='Semanas',axis=alt.Axis(format='%b/%Y',tickCount='month')),
            y=alt.Y(f'{y}:Q',title='US$/barril' if y==config.COL_BRENT else '%',scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip('Semana:T',format='%d/%m/%Y'),alt.Tooltip(f'{y}:Q',format='.2f')])
        if smooth:
            rolling=oil.set_index('Semana')[y].rolling('28D',min_periods=4).mean().reset_index(name='Média móvel')
            base=base+alt.Chart(rolling).mark_line(color='#FFC267',strokeDash=[6,4]).encode(x='Semana:T',y='Média móvel:Q')
        st.altair_chart(chart_base(marks(base,start,end,show_events),340),use_container_width=True,theme=None)

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
    oil_weeks = o[['Semana', config.COL_BRENT]].drop_duplicates('Semana')
    if selected_uf == 'Brasil (média nacional)':
        selected_source = b[b['Combustível'] == fuel][['Semana', PRICE]].copy()
    else:
        selected_source = e[(e['Combustível'] == fuel) & (e['UF'] == selected_uf)][['Semana', PRICE]].copy()
    selected_pairs = (selected_source.merge(oil_weeks, on='Semana', how='inner', validate='one_to_one')
                      .dropna(subset=[PRICE, config.COL_BRENT]).sort_values('Semana'))
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
        pairs = source.merge(oil_weeks, on='Semana', how='inner', validate='many_to_one')
    else:
        pairs = selected_pairs.copy()
        pairs['UF'] = 'Brasil' if selected_uf.startswith('Brasil') else selected_uf

    if pairs.empty:
        st.warning('Não há semanas com observações pareadas para essa seleção.')
    else:
        # Cores e nomes das quatro fases são preservados do gráfico original.
        # Em "Todas as UFs", os símbolos distinguem as UFs, sem perder a legenda por fase.
        pairs = pairs.rename(columns={'Semana': 'Data inicial'})
        pairs['Data Brent'] = pairs['Data inicial'] + pd.Timedelta(days=5)
        pairs['Data final'] = pairs['Data inicial'] + pd.Timedelta(days=6)
        phases, phase_names = an.fases_conflito(pairs['Data Brent'])
        pairs['Fase'] = phases
        phase_colors = ['#7F8C8D', '#6A1B9A', '#BF360C', '#263238']
        fig = go.Figure()
        symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'triangle-down',
                   'triangle-left', 'triangle-right', 'star', 'hexagon', 'pentagon']
        symbol_map = {state: symbols[i % len(symbols)] for i, state in enumerate(ufs)}
        for phase, color in zip(phase_names, phase_colors):
            group = pairs[pairs['Fase'] == phase]
            if group.empty:
                continue
            fig.add_trace(go.Scatter(
                x=group[config.COL_BRENT], y=group[PRICE], mode='markers', name=phase,
                marker=dict(size=9 if not all_mode else 7, color=color, opacity=.85,
                            symbol=[symbol_map.get(u, 'circle') for u in group['UF']],
                            line=dict(width=.5, color='white')),
                customdata=group[['UF', 'Data final']].assign(
                    **{'Data final': group['Data final'].dt.strftime('%d/%m/%Y')}).to_numpy(),
                hovertemplate='UF: %{customdata[0]}<br>Semana até %{customdata[1]}'
                              '<br>Brent: US$ %{x:.2f}<br>' + fuel + ': R$ %{y:.2f}/l<extra></extra>'
            ))
        if regression is not None:
            xx = np.array([regression['x_min'], regression['x_max']])
            fig.add_trace(go.Scatter(
                x=xx, y=regression['intercept'] + regression['slope'] * xx,
                mode='lines', name='Regressão linear',
                line=dict(color=config.CORES_COMBUSTIVEIS[fuel], width=3), hoverinfo='skip'))
            annotation = (f'<b>{an.equacao(regression)}</b><br>'
                          f'R² = {an.fmt(regression["r2"], 3)} · r = {an.fmt(regression["r"], 3)}<br>'
                          f'n = {regression["n"]} semanas')
            fig.add_annotation(x=.02, y=.98, xref='paper', yref='paper', text=annotation,
                               showarrow=False, align='left', xanchor='left', yanchor='top',
                               bgcolor='rgba(255,255,255,.88)', bordercolor='rgba(0,0,0,.3)',
                               borderwidth=1, font=dict(size=12, color='#222'))
        label = 'nacional' if selected_uf.startswith('Brasil') else f'({selected_uf})'
        fig.update_layout(
            height=500, template='plotly_dark', paper_bgcolor='#18131e', plot_bgcolor='#18131e',
            font=dict(family='Inter, Segoe UI, Arial, sans-serif', size=13),
            separators=',.', margin=dict(t=30, l=10, r=10, b=10), hovermode='closest',
            xaxis_title='Preço do petróleo Brent (US$ por barril)',
            yaxis_title=f'{fuel} – preço médio {label} (R$/litro)',
            legend=dict(orientation='h', y=-.22, x=0, title_text=''))
        fig.update_xaxes(tickprefix='US$ ', gridcolor='rgba(128,128,128,.2)')
        fig.update_yaxes(tickprefix='R$ ', tickformat='.2f', gridcolor='rgba(128,128,128,.2)')
        st.plotly_chart(fig, use_container_width=True)
    st.caption('Fonte: ANP e EIA. Associação estatística não demonstra causalidade. '
               'A linha de regressão e os indicadores correspondem à abrangência selecionada.')

with st.expander('▣ Metodologia e fontes'):
    st.markdown('**Fontes:** ANP, preços semanais nacionais e estaduais; EIA, Brent semanal. As datas ANP são semanas iniciadas aos domingos; cada cotação semanal do Brent é pareada com a semana ANP que a contém. Não há interpolação de semanas ausentes. A média regional é simples entre UFs disponíveis; o ranking por preço usa a média semanal no período filtrado. Os indicadores nacionais utilizam a base Brasil, não a média de estados.')
    st.markdown('**Marcos geopolíticos:** as datas e descrições foram fornecidas no escopo do projeto; são anotações contextuais que exigem validação documental antes da publicação. Correlação não prova causalidade.')
    for warning in warnings:st.warning(warning)
with st.expander('⇩ Dados filtrados e download'):
    filtered=e[e.UF.isin(selected_ufs)]
    st.dataframe(filtered,hide_index=True,use_container_width=True)
    for label,frame in [('estados',filtered),('brasil',b),('brent',o)]:
        st.download_button(f'Baixar {label}.csv',frame.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),file_name=f'{label}_filtrado.csv',mime='text/csv')
st.caption('Fontes: ANP e EIA | Projeto Integrador SENAC | Dados calculados das bases locais, sem valores simulados')
