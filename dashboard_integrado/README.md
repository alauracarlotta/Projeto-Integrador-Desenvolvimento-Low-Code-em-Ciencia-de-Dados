# Dashboard Integrado SENAC

Execute `pip install -r requirements.txt` e `streamlit run app.py`.

Coloque os três CSVs tratados na pasta `bases/` ao lado de `app.py`, ou defina `PI_BASES_DIR` com o caminho absoluto da pasta contendo:

- `Base_Semanal_Brasil_2026_Tratada.csv`
- `Base_Semanal_Estados_2026_Tratada.csv`
- `Base_Brent_Weekly_2026_Tratada.csv`

O projeto reutiliza `config.py`, `carregamento.py` e `analises.py` do código enviado, além de um novo `app.py` para o layout final. `graficos.py` foi preservado como referência, mas o novo app usa Altair para as visualizações.

**Nota:** datas e descrições de eventos geopolíticos são anotações do projeto, não fatos históricos verificados. Sem os CSVs, não é possível validar numericamente as figuras. O período Jan–Set/2026 é a janela visual do projeto, e os gráficos exibem apenas semanas efetivamente presentes nas bases.
