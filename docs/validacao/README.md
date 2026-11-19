# Validação das bases de dados

Este diretório reúne a documentação e os relatórios de validação das bases utilizadas no dashboard do Projeto Integrador.

## Organização

- `data/raw/`: arquivos originais da ANP e da EIA.
- `data/processed/`: arquivos tratados utilizados pelo dashboard.
- `scripts/`: scripts de auditoria e comparação.
- `docs/validacao/`: documentação e relatórios gerados.

## Como reproduzir a validação

Na raiz do projeto, com o ambiente virtual ativado, execute:

```bash
python scripts/auditar_bases.py
python scripts/comparar_raw_processed.py
python scripts/comparar_eia.py
```

Os scripts verificam a integridade das bases tratadas e comparam os preços médios da ANP e as cotações do Brent com os respectivos arquivos originais.

## Relatórios gerados

- `resultado_auditoria.csv`: resultados das verificações automatizadas.
- `auditoria_eia.csv`: datas do Brent e correspondência com as semanas ANP.
- `pareamento_anp_eia.csv`: observações nacionais pareadas entre ANP e EIA.

## Critérios de validação

- Carregamento dos três arquivos tratados.
- Datas válidas e preços positivos.
- Ausência de duplicações nas chaves analisadas.
- Cobertura temporal das bases ANP.
- Continuidade das semanas nacionais.
- Correspondência temporal entre ANP e EIA.
- Comparação dos valores tratados com os arquivos originais.

## Tratamento de inconsistências

Quando uma divergência for identificada, ela deverá ser investigada e documentada antes de qualquer correção.

Os arquivos originais em `data/raw/` devem ser preservados. Correções justificadas podem ser realizadas em `data/processed/`, seguidas de nova execução dos testes.

## Limitações

A auditoria valida a integridade estrutural, o pareamento temporal e a correspondência dos valores comparados com os arquivos brutos utilizados no projeto.

Ela não substitui a validação das médias regionais, correlações, regressões ou demais indicadores estatísticos do dashboard.
