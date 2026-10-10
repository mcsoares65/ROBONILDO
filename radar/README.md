# Radar do Robonildo

Tela de radar de sinais, no estilo de radar de caça. Sem números: compra na metade de cima, venda na de baixo, e cada estratégia do time é um ponto que se aproxima do centro conforme a confiança sobe. No fechamento do candle, quando o robô abre a posição, a mira fecha no alvo e a tela diz "Alvo Capturado!".

## Como usar

1. Rode o `principal.py` (Replay ou Normal). O robô grava `radar/radar_estado.js` a cada segundo.
2. Abra `radar/radar.html` com dois cliques. A etiqueta do canto mostra "AO VIVO" (ou "AO VIVO · REPLAY").
3. Sem o robô rodando, a tela mostra dados simulados e os botões de baixo forçam compra, venda ou mercado lateral.
4. Se o robô para de publicar por mais de 6 segundos, a tela avisa "SEM SINAL DO ROBÔ".

## Cabeçalho e textos

- No topo ficam o ativo, a data, a hora e o preço atual, exatamente como o robô leu no DDE (em Replay, a hora do replay). O relógio do Windows nunca é usado: sem o robô, ou com um robô antigo que não publica o campo `mercado`, a tela mostra traços (`--/--/----`, `--:--:--`) e o aviso "robô sem dados de mercado (atualize o robô e reinicie)" abaixo do preço. Cada campo tem largura fixa e fonte de largura única, então a linha não se mexe quando os números mudam.
- A etiqueta do canto mostra **AO VIVO** (verde), **REPLAY** (amarelo, só quando o robô está em modo replay), **SEM SINAL DO ROBÔ** (vermelho) ou **DADOS SIMULADOS**.
- Som e voz ficam logo abaixo da linha do preço, como dois ícones pequenos (alto-falante e balão de fala), e **abrem ligados**; com risco = desligado. Os navegadores só liberam áudio e fala depois de um toque na página, então aparece o aviso "toque na tela para liberar o áudio" até o primeiro toque.
- Os textos acompanham a confiança da estratégia mais próxima: **VARRENDO** (abaixo de 45%), **CONTATO DETECTADO** (45% a 70%), **ALVO NA MIRA** (70% ou mais, aguardando a confirmação no fechamento do candle) e **ALVO CAPTURADO!** (o robô abriu a posição). Esses limites são só da tela e não entram em nenhuma decisão do robô.
- A tela se ajusta ao tamanho da janela, sem barra de rolagem.

## Som e voz

- **Som:** um ping de sonar a cada volta da varredura, um toque curto quando ela passa por um alvo com confiança média ou alta, e uma sequência de bipes na captura. O navegador só libera o áudio depois do clique no ícone.
- **Voz:** fala "Alvo na mira" e "Alvo capturado, compra/venda". Na mesma máquina do robô, deixe desligada: o robô já narra e as vozes se sobreporiam.

## Ordens

`RADAR_ENVIA_ORDENS = False` em `configuracao.py`. O radar não envia ordem ao Profit. Quem envia é o robô (`ENVIAR_ORDENS`). O envio pelo radar ainda não existe; `True` é tratado como `False`, com aviso.

## Segurança

O arquivo `radar_estado.js` traz só o desenho: um rumo por estratégia, o lado, a confiança, o consenso e o contador de captura, mais o cabeçalho de mercado (ativo, hora e preço, que são dados públicos). Não traz nomes de estratégia, condições, limites nem preços de entrada ou de stop. É gerado pelo robô e não vai para o GitHub (`.gitignore`).
