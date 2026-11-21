# Relatório de auditoria dos dados tratados

**Projeto Integrador:** Instabilidade geopolítica e preços dos combustíveis no Brasil  
**Data da validação:** 18/11/2026 
**Revalidação:** após a refatoração dos módulos do dashboard
**Issue relacionada:** #12 — Implementar a leitura dos dados tratados

## 1. Objetivo

Verificar a integridade das bases tratadas da ANP e da EIA, sua correspondência com os arquivos originais e a consistência do pareamento temporal utilizado pelo dashboard.

O período de análise compreende janeiro a setembro de 2026, considerando as semanas efetivamente disponíveis nas bases ANP e suas respectivas correspondências temporais com as cotações semanais do petróleo Brent.

## 2. Verificações realizadas

- [x] Carregamento dos três arquivos CSV tratados.
- [x] Verificação de datas válidas e preços positivos.
- [x] Verificação de duplicidades nas chaves analisadas.
- [x] Conferência da cobertura temporal entre janeiro e setembro de 2026 nas bases ANP.
- [x] Identificação de 27 UFs, cinco regiões e três combustíveis.
- [x] Conferência da continuidade semanal da base nacional.
- [x] Validação do pareamento temporal ANP × EIA.
- [x] Comparação dos preços médios da ANP com os arquivos originais.
- [x] Comparação das cotações semanais do Brent com o arquivo original.
- [x] Nova execução da auditoria após a correção identificada.

## 3. Resultados consolidados

A auditoria automatizada executou **25 verificações, sem falhas registradas**.

| Base | Registros comparados | Divergências finais |
|---|---:|---:|
| ANP Brasil | 117 | 0 |
| ANP Estados | 3.134 | 0 |
| EIA Brent | 45 | 0 |
| **Total** | **3.296** | **0** |

A comparação foi realizada para os preços médios de revenda da ANP e as cotações semanais do Brent, considerando as chaves de identificação correspondentes.

## 4. Continuidade e alinhamento temporal

A base nacional apresentou 39 semanas consecutivas para cada combustível: Diesel S10, Etanol e Gasolina comum.

Foram identificados 117 pares ANP × EIA, todos com diferença de cinco dias entre o início da semana ANP (domingo) e a referência EIA (sexta-feira).

As semanas são classificadas pela data inicial ANP. Dessa forma, a semana iniciada em 27/09/2026 utiliza a cotação EIA de 02/10/2026.

## 5. Inconsistência identificada e corrigida

Durante a comparação da base EIA tratada com o arquivo original `RBRTEw.csv`, foi identificada uma divergência na cotação de 09/01/2026:

- **Arquivo original:** US$ 62,93/barril.
- **Arquivo tratado antes da correção:** US$ 62,30/barril.
- **Diferença:** US$ 0,63/barril.

O valor tratado foi corrigido para US$ 62,93/barril, preservando o arquivo original.

Após a correção, a comparação EIA apresentou 45 registros pareados, nenhuma divergência de preço e nenhuma data ausente.

A auditoria geral foi executada novamente, mantendo o resultado de 25 verificações sem falhas.

## 6. Revalidação após a refatoração

Após a reorganização e modularização do código-fonte do dashboard, a auditoria automatizada foi executada novamente para verificar a integridade das bases utilizadas pela aplicação.

Os resultados apresentaram:

- 25 verificações automatizadas, sem falhas.
- 117 registros na base nacional da ANP.
- 3.134 registros na base estadual da ANP.
- 45 registros na base EIA Brent.
- 27 unidades federativas e cinco regiões brasileiras.
- 117 observações nacionais pareadas entre ANP e EIA.
- Nenhum aviso emitido pelos carregadores das bases.

Os resultados confirmaram a manutenção dos critérios de integridade estrutural e pareamento temporal após a refatoração.

A revalidação complementa a auditoria original, preservando o histórico das verificações e das correções anteriormente realizadas.

## 7. Evidências

- `scripts/auditar_bases.py`
- `scripts/comparar_raw_processed.py`
- `scripts/comparar_eia.py`
- `docs/validacao/resultado_auditoria.csv`
- `docs/validacao/auditoria_eia.csv`
- `docs/validacao/pareamento_anp_eia.csv`

## 8. Conclusão

As bases tratadas foram aprovadas nas verificações realizadas de integridade estrutural, continuidade temporal nacional, pareamento ANP × EIA e correspondência dos valores analisados com os arquivos originais.

**Limitações:** não foram validados nesta etapa todos os campos das bases, a continuidade semanal individual por UF, o cálculo das médias regionais ou os indicadores estatísticos do dashboard. Essas verificações deverão ser tratadas nas etapas correspondentes.

**Situação:** validação dos dados utilizados na leitura do dashboard concluída no escopo descrito.
