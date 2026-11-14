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

O ambiente inicial foi configurado e testado com uma aplicação demonstrativa de vendas, utilizando dados de exemplo para verificar o funcionamento do Streamlit e do Pandas.

**A aplicação demonstrativa ainda não representa o dashboard definitivo do Projeto Integrador.**

As próximas etapas incluem o tratamento e a integração das bases de dados, a definição das visualizações, a elaboração do protótipo e a implementação do dashboard com os dados oficiais.

## 📋 Organização das atividades

O desenvolvimento está organizado no GitHub Projects, utilizando um quadro Kanban e quatro milestones:

1. Base de dados.
2. Protótipo.
3. Dashboard funcional.
4. Documento de conclusões.

As atividades são acompanhadas por meio de issues, responsáveis e prioridades.
