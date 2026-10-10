# Radar do Robonildo

Tela de radar de sinais, no estilo de radar de caça. Sem números: compra na metade de cima, venda na de baixo, e cada estratégia do time é um ponto que se aproxima do centro conforme a confiança sobe. No fechamento do candle, quando o robô abre a posição, a mira fecha no alvo e a tela diz "Alvo Capturado!".

## Como usar

1. Rode o `principal.py` (Replay ou Normal). O robô grava `radar/radar_estado.js` a cada segundo.
2. Abra `radar/radar.html` com dois cliques. A etiqueta do canto mostra "AO VIVO" (ou "AO VIVO · REPLAY").
3. Sem o robô rodando, a tela mostra dados simulados e os botões de baixo forçam compra, venda ou mercado lateral.
4. Se o robô para de publicar por mais de 6 segundos, a tela avisa "SEM SINAL DO ROBÔ".

## Som e voz

- **Som:** um ping de sonar a cada volta da varredura, um toque curto quando ela passa por um alvo com confiança média ou alta, e uma sequência de bipes na captura. O navegador só libera o áudio depois do clique no botão.
- **Voz:** fala "Alvo travando" e "Alvo capturado, compra/venda". Na mesma máquina do robô, deixe desligada: o robô já narra e as vozes se sobreporiam.

## Ordens

`RADAR_ENVIA_ORDENS = False` em `configuracao.py`. O radar não envia ordem ao Profit. Quem envia é o robô (`ENVIAR_ORDENS`). O envio pelo radar ainda não existe; `True` é tratado como `False`, com aviso.

## Segurança

O arquivo `radar_estado.js` traz só o desenho: um rumo por estratégia, o lado, a confiança, o consenso e o contador de captura. Não traz nomes de estratégia, condições, limites nem preços. É gerado pelo robô e não vai para o GitHub (`.gitignore`).
