# Metodologia e validação da análise complementar de eletromobilidade

**Projeto:** Instabilidade Geopolítica e os Preços dos Combustíveis no Brasil  
**Período analisado:** janeiro a setembro de 2026  
**Data da validação:** 22/11/2026  
**Abrangência:** Brasil

## 1. Objetivo

Investigar, de maneira exploratória e complementar, a existência de associação linear entre as variações mensais do preço do petróleo Brent e os emplacamentos de automóveis elétricos no Brasil.

A análise não substitui os objetivos principais do Projeto Integrador.

## 2. Fontes de dados

| Fonte | Informação | Periodicidade |
|---|---|---|
| Fenabrave | Emplacamentos de automóveis elétricos | Mensal |
| EIA | Europe Brent Spot Price FOB | Semanal |

Os relatórios originais da Fenabrave encontram-se preservados em `data/raw/fenabrave/`.

## 3. Extração e tratamento dos dados

A extração foi automatizada utilizando Python e a biblioteca PyPDF, por meio do script `scripts/extrair_fenabrave.py`.

Foram adotados os seguintes critérios:

- Seleção da tabela Mercado de Eletrificados Autos.
- Extração da linha B) Elétricos.
- Utilização da coluna (A), correspondente ao mês de referência.
- Exclusão de automóveis híbridos e veículos comerciais leves.
- Preservação dos valores originalmente publicados em cada edição.
- Identificação do arquivo de origem e da página utilizada.

A base consolidada foi armazenada em:

`data/processed/Base_Mensal_Eletricos_2026.csv`

## 4. Validação dos dados extraídos

Os nove registros extraídos automaticamente foram comparados manualmente com os respectivos relatórios originais.

| Mês | Fonte original | Base tratada | Divergência |
|---|---:|---:|---:|
| Janeiro | 8.198 | 8.198 | 0 |
| Fevereiro | 8.654 | 8.654 | 0 |
| Março | 13.991 | 13.991 | 0 |
| Abril | 17.468 | 17.468 | 0 |
| Maio | 20.878 | 20.878 | 0 |
| Junho | 21.018 | 21.018 | 0 |
| Julho | 25.698 | 25.698 | 0 |
| Agosto | 27.061 | 27.061 | 0 |
| Setembro | 22.056 | 22.056 | 0 |

### Resultado da validação

| Indicador | Resultado |
|---|---:|
| Relatórios analisados | 9 |
| Registros comparados | 9 |
| Correspondências | 9 |
| Divergências | 0 |
| Correspondência dos valores conferidos | 100% |

Durante a conferência, foram identificadas pequenas revisões nos valores publicados em edições posteriores da Fenabrave.

Optou-se por preservar os valores originalmente publicados em cada relatório mensal, garantindo consistência no critério de extração e rastreabilidade dos registros.

## 5. Integração com o petróleo Brent

Os registros semanais do Brent foram agregados por média aritmética mensal, considerando o mês da data original de cada observação.

Posteriormente, as bases foram integradas pela referência mensal.

Foram calculadas as variações percentuais em relação ao mês imediatamente anterior:

**Variação mensal (%) = [(valor atual / valor anterior) - 1] × 100**

Janeiro foi utilizado como referência inicial, resultando em oito observações pareadas entre fevereiro e setembro de 2026.

## 6. Análise estatística

Foi aplicada regressão linear simples, considerando:

- **Variável independente (X):** variação percentual mensal do preço do Brent.
- **Variável dependente (Y):** variação percentual mensal dos emplacamentos de automóveis elétricos.

### Resultados obtidos

| Indicador | Resultado |
|---|---:|
| Coeficiente de Pearson (r) | 0,4246 |
| Coeficiente de determinação (R²) | 0,1803 |
| Coeficiente angular | 0,5037 |
| Intercepto | 10,8629 |
| p-valor | 0,2944 |
| Observações pareadas | 8 |

A amostra apresentou associação linear positiva, porém sem significância estatística ao nível de 5%.

Os resultados possuem caráter exploratório e não permitem estabelecer relações causais.

## 7. Implementação no dashboard

A funcionalidade foi implementada no módulo independente `eletromobilidade.py`, preservando a estrutura dos demais módulos da aplicação.

A visualização contempla:

- Gráfico de dispersão das variações mensais.
- Reta de regressão linear.
- Identificação dos meses.
- Tooltips interativos.
- Indicadores estatísticos.
- Identificação das fontes e do período analisado.
- Ressalvas metodológicas.

A análise é disponibilizada em uma seção expansível, fechada por padrão, com abrangência nacional e período fixo.

Os filtros globais do dashboard não interferem nessa funcionalidade.

## 8. Testes realizados

| Teste | Resultado |
|---|---|
| Extração automatizada dos relatórios | Aprovado |
| Correspondência com os valores originais | Aprovado |
| Integração mensal das bases | Aprovado |
| Cálculo das métricas estatísticas | Aprovado |
| Renderização do gráfico | Aprovado |
| Integração ao dashboard | Aprovado |
| Tema claro | Aprovado |
| Tema escuro | Aprovado |
| Responsividade mobile em 440 px | Aprovado com ressalva |
| Tooltips no desktop | Aprovado |
| Independência dos filtros globais | Aprovado |
| Seção expansível fechada por padrão | Aprovado |
| Regressão das funcionalidades existentes | Aprovado |

Na simulação mobile, foi identificada uma pequena sobreposição entre alguns rótulos mensais, sem comprometimento estrutural da visualização.

O funcionamento dos tooltips por toque e a apresentação em larguras inferiores a 440 px não foram especificamente validados.

## 9. Reprodução da análise

Na raiz do projeto, com o ambiente virtual ativado e as dependências principais instaladas, execute:

```bash
python -m pip install -r requirements-dev.txt
```

Para reproduzir a extração:

```bash
python -m scripts.extrair_fenabrave
```

Para executar a integração, consultar as métricas e visualizar o gráfico isoladamente:

```bash
python -m eletromobilidade
```

Para executar o dashboard completo:

```bash
python -m streamlit run app.py
```

## 10. Limitações metodológicas

- Quantidade reduzida de observações pareadas.
- Ausência de controle sobre outras variáveis econômicas e comerciais.
- Possível influência de sazonalidade e dependência temporal.
- Possíveis defasagens entre decisões de compra e emplacamentos.
- Ausência de modelagem dos efeitos específicos dos acontecimentos geopolíticos.
- Não incorporação de revisões posteriores dos relatórios mensais.
- Resultados restritos ao período analisado.

## 11. Encerramento da validação

A etapa de implementação e validação local confirmou a correspondência dos dados extraídos com os valores originais conferidos, a integração mensal das bases e o funcionamento da visualização complementar.

A interpretação aprofundada dos resultados será incorporada às etapas de análise e elaboração das conclusões do Projeto Integrador.

A validação em produção será realizada após a publicação da funcionalidade.
