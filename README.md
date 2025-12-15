# Robonildo

Automação de monitoramento do ProfitPro que captura o gráfico, pede uma decisão para a IA e narra o que fazer.

## Pré-requisitos
- Python 3.10+
- Windows (biblioteca `pywin32` é usada para focar a janela do Profit)
- Chaves de API:
  - `OPENAI_API_KEY` para as decisões de visão (`DecisorOpenAI`).
  - `ELEVEN_API_KEY` para a síntese de voz (`narracao/voz.py`).

Instale as dependências com:

```bash
python -m venv .venv
source .venv/Scripts/activate  # ou .venv/bin/activate no Linux
pip install -r requirements.txt
```

## Como executar
1. Abra o ProfitPro e deixe a janela visível com o título definido em `config.py` (`NOME_TELA_PROFIT`).
2. Ajuste o offset do gráfico em `main.py` se necessário (`OFFSET_GRAFICO`).
3. Garanta que as variáveis `OPENAI_API_KEY` e `ELEVEN_API_KEY` estejam exportadas no ambiente.
4. Execute:

```bash
python main.py
```

O loop fará a captura da tela, solicitará a decisão para a IA, aplicará as regras de operação e narrará a ação sugerida. Logs CSV serão salvos na pasta `logs/`.

## Estrutura rápida
- `visao/`: foco na janela do ProfitPro e captura da região configurada.
- `ia/`: chamada ao modelo OpenAI Vision e normalização da resposta.
- `regras/`: regras de pregão e horário.
- `operacao/`: estado e simulação de ordens.
- `narracao/`: narração via ElevenLabs e orquestração do texto.
- `leitura/`: ganchos para interpretação visual caso precise.

## Observações
- `ENVIAR_ORDENS` em `config.py` está `False`; mantenha assim enquanto valida o fluxo.
- `MODELO_OPENAI` em `main.py` aponta para `gpt-5-mini`, ajuste conforme disponibilidade na sua conta.
