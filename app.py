import streamlit as st
import pandas as pd

# Lê o arquivo .csv
dados = pd.read_csv('data/processed/vendas.csv', sep=';', encoding='utf-8-sig')

# Remove espaços dos nomes das colunas
dados.columns = dados.columns.str.strip()

# Título
st.title('Dashboard de Vendas')

# Filtro 
categoria = st.selectbox('Selecione a Categoria:', dados['Categoria'].unique())

# Filtra os Dados
dados_filtrados = dados[dados['Categoria'] == categoria]

# KPI 
st.metric(label='Total de Vendas', value=f'R$ {dados_filtrados["Valor"].sum():,.2f}')

# Duas colunas
col1, col2 = st.columns(2)

with col1:
	# Gráfico de Barras
	st.subheader('Vendas por Produto')
	grafico_barras = dados_filtrados.groupby('Produto')['Valor'].sum()
	st.bar_chart(grafico_barras)

with col2:
	if 'Data' in dados_filtrados.columns:
		# Gráfico de Linha
		st.subheader('Evolução das Vendas')
		grafico_linha = dados_filtrados.groupby('Data')['Valor'].sum()
		st.line_chart(grafico_linha)
	
	else:
		st.subheader('Quantidade Vendida por Produto')
		grafico_qtd = dados_filtrados.groupby('Produto').size()
		st.bar_chart(grafico_qtd)

#Tabela
st.subheader('Tabela de Dados Filtrados')
st.dataframe(dados_filtrados)
