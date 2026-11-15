# Instabilidade Geopolítica e os Preços dos Combustíveis no Brasil

## 📌 Sobre o projeto

Projeto Integrador desenvolvido no curso de **Análise e Desenvolvimento de Sistemas do Centro Universitário Senac**, com foco na aplicação de ferramentas de ciência de dados e desenvolvimento low-code.

O projeto tem como objetivo analisar o comportamento dos preços dos combustíveis no Brasil, entre fevereiro e agosto de 2026, considerando o contexto de instabilidade geopolítica internacional.

A proposta é desenvolver um dashboard interativo que permita acompanhar a evolução dos preços, comparar os valores entre as unidades federativas brasileiras e investigar possíveis associações com as oscilações do preço internacional do petróleo Brent.

## 🛠️ Tecnologias utilizadas

- **Python 3.14:** linguagem de programação.
- **Pandas:** manipulação e análise de dados.
- **Streamlit:** desenvolvimento da aplicação web interativa.
- **Git e GitHub:** versionamento de código e gerenciamento das atividades.

## 📊 Fontes de dados

O projeto utiliza dados públicos provenientes de duas fontes oficiais:

- **ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis):** preços médios semanais de revenda dos combustíveis por unidade federativa brasileira.
- **EIA (U.S. Energy Information Administration):** preços internacionais semanais do petróleo Brent.

O período de análise compreende fevereiro a agosto de 2026, considerando gasolina comum, etanol hidratado e óleo diesel S10.

## 📁 Estrutura do projeto

```text
projeto_integrador/
├── data/
│   ├── raw/             # Dados originais da ANP e EIA
│   └── processed/       # Dados tratados
├── docs/                # Documentação complementar
├── app.py               # Aplicação Streamlit
├── requirements.txt     # Dependências Python
├── .gitignore           # Arquivos ignorados pelo Git
└── README.md            # Documentação principal
```

O ambiente virtual (`venv/`) é criado localmente e não deve ser versionado.

## 🚀 Como executar o projeto

### 1. Clonar o repositório

```bash
git clone https://github.com/alauracarlotta/Projeto-Integrador-Desenvolvimento-Low-Code-em-Ciencia-de-Dados.git
cd Projeto-Integrador-Desenvolvimento-Low-Code-em-Ciencia-de-Dados
```

### 2. Criar o ambiente virtual

É necessário ter uma versão compatível do Python instalada. O ambiente inicial foi configurado utilizando Python 3.14.

```bash
python3 -m venv venv
```

### 3. Ativar o ambiente virtual

**Linux/macOS:**

```bash
source venv/bin/activate
```

**Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Instalar as dependências

```bash
python -m pip install -r requirements.txt
```

### 5. Executar a aplicação

```bash
python -m streamlit run app.py
```

O Streamlit disponibilizará um endereço local para acessar a aplicação no navegador, geralmente `http://localhost:8501`.

## 🧪 Status do desenvolvimento

O dashboard está implementado em `app.py` e lê exclusivamente as bases de `V1_PROJETO/Versao_Oficial/00.Bases/01.Tratadas`:

- `Base_Semanal_Estados_2026_Tratada.csv`
- `Base_Semanal_Brasil_2026_Tratada.csv`
- `Base_Brent_Weekly_2026_Tratada.csv`

Os CSVs ANP usam ponto e vírgula como separador e datas no formato mês/dia/ano. O CSV Brent usa vírgula como separador e combina as colunas `Date` (mês abreviado em português e dia) e `Ano`. O pareamento associa a data EIA ao domingo inicial da semana ANP. O cache da aplicação é invalidado quando esses arquivos são atualizados. Os arquivos auxiliares `cache_sgs_*.csv` não são utilizados pelos gráficos atuais.

- Cabeçalho com indicadores nacionais por combustível.
- Evolução semanal Brasil com linhas para gasolina comum, etanol hidratado e diesel S10.
- Evolução semanal pelas cinco regiões, usando médias simples dos preços estaduais, com referência nacional e opção de variação acumulada.
- Comparação estadual por combustível: por padrão, colunas com os três estados mais baratos e os três mais caros, usando o preço médio no período. Também permite consultar todas as UFs ou apenas as selecionadas.
- Evolução semanal do Brent com cotação, variação acumulada, média móvel opcional de quatro semanas e marcos de contexto.
- Dispersão Brent × combustível por estado, correlação de Pearson e semanas pareadas. O botão Todos os estados reúne as 27 UFs, com cores e destaque interativo por região e identificação da UF no tooltip.
- Filtros de período, combustível e UFs, metodologia e download dos dados filtrados.

As anotações geopolíticas existentes são rótulos de contexto sem validação histórica na aplicação. A associação estatística não implica causalidade.

## 📋 Organização das atividades

O desenvolvimento está organizado no GitHub Projects, utilizando um quadro Kanban e quatro milestones:

1. Base de dados.
2. Protótipo.
3. Dashboard funcional.
4. Documento de conclusões.

As atividades são acompanhadas por meio de issues, responsáveis e prioridades.
