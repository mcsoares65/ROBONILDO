# Radar do Robonildo

Tela de radar de sinais, no estilo de radar de caça. Sem números: compra na metade de cima, venda na de baixo, e cada estratégia do time é um ponto que se aproxima do centro conforme a confiança sobe. No fechamento do candle, quando o robô abre a posição, a mira fecha no alvo e a tela diz "Alvo Capturado!".

## Como usar

1. Rode o `principal.py` (Replay ou Normal). O robô grava `radar/radar_estado.js` a cada segundo.
2. Abra `radar/radar.html` com dois cliques. A etiqueta do canto mostra "AO VIVO" (ou "AO VIVO · REPLAY").
3. Sem o robô rodando, a tela mostra dados simulados e os botões de baixo forçam compra, venda ou mercado lateral.
4. Se o robô para de publicar por mais de 6 segundos, a tela avisa "PERDEMOS O CONTATO COM A BASE".

## Cabeçalho e textos

- No topo ficam o ativo, a data, a hora e o preço atual, exatamente como o robô leu no DDE (em Replay, a hora do replay). O relógio do Windows nunca é usado: sem o robô, ou com um robô antigo que não publica o campo `mercado`, a tela mostra traços (`--/--/----`, `--:--:--`) e o aviso "base sem dados de mercado (atualize a base e reinicie)" abaixo do preço. Cada campo tem largura fixa e fonte de largura única, então a linha não se mexe quando os números mudam.
- A etiqueta do canto mostra **AO VIVO** (verde), **REPLAY** (amarelo, só quando o robô está em modo replay), **PERDEMOS O CONTATO COM A BASE** (vermelho) ou **DADOS SIMULADOS**.
- Som e voz ficam logo abaixo da linha do preço, como dois ícones pequenos (alto-falante e balão de fala), e **abrem ligados**; com risco = desligado. Os navegadores só liberam áudio e fala depois de um toque na página, então aparece o aviso "toque na tela para liberar o áudio" até o primeiro toque.
- Os textos acompanham a confiança da estratégia mais próxima: **VARRENDO** (abaixo de 45%), **CONTATO DETECTADO** (45% a 90%), **ALVO NA MIRA** (90% ou mais, aguardando a confirmação no fechamento do candle; para não ficar piscando perto do limite, só sai da mira abaixo de 85%) e **ALVO CAPTURADO!** (o robô abriu a posição). Esses limites são só da tela e não entram em nenhuma decisão do robô.
- A tela se ajusta ao tamanho da janela, sem barra de rolagem.

## Versões

No canto inferior direito a tela mostra `RADAR Vxxx · BASE Vxxx`: a versão desta página e a da base (o robô) que está transmitindo. Se a base for antiga e não informar a versão, aparece `BASE ?`; sem a base, `BASE -`. Quando as duas diferem, o texto fica amarelo. No contexto do radar, o robô é chamado de "base".

## Som e voz

- **Som:** um ping de sonar a cada volta da varredura, um toque curto quando ela passa por um alvo com confiança média ou alta, e uma sequência de bipes na captura. O navegador só libera o áudio depois do clique no ícone.
- **Voz:** fala "Alvo na mira" e "Alvo capturado, compra/venda". Na mesma máquina do robô, deixe desligada: o robô já narra e as vozes se sobreporiam.

## Ordens

`RADAR_ENVIA_ORDENS = False` em `configuracao.py`. O radar não envia ordem ao Profit. Quem envia é o robô (`ENVIAR_ORDENS`). O envio pelo radar ainda não existe; `True` é tratado como `False`, com aviso.

## Ponte para o radar online (em construção)

`ponte_radar.py`, na raiz do projeto, é um processo **separado** do robô. Ele só lê o `radar_estado.js` e o envia por HTTPS, em mão única, ao servidor do radar (que ainda será criado em `radar/servidor/`). Ele não recebe comando nenhum.

- **Rodar:** `python ponte_radar.py` (em outra janela, com o robô rodando). Se o servidor ficar fora do ar, o robô nem percebe: a ponte tenta de novo com espera crescente e manda só o estado mais recente.
- **Configuração (fora do Git):** variáveis de ambiente ou o arquivo `ponte_radar.privado.json` (já no `.gitignore`), com `radar_url`, `radar_chave_vivo` e `radar_chave_replay`. Cada canal tem a sua chave. Modo `replay` do robô vai para o canal replay, modo `normal` só para o ao vivo. O endereço precisa ser `https://` (`http` só para `127.0.0.1` ou `localhost`, em teste).
- **O que ela envia:** o mesmo conteúdo do `radar_estado.js`, remontado campo a campo depois de validado (nenhum campo extra passa), mais um identificador de sessão e um contador de envio. Arquivo parado não é reenviado, e o servidor mede a idade da última atualização pelo relógio dele.
- **Ainda não existe:** o servidor e a opção de fonte online no `radar.html`. Esta etapa não publica nada na internet.

## Segurança

O arquivo `radar_estado.js` traz só o desenho: um rumo por estratégia, o lado, a confiança, o consenso e o contador de captura, mais o cabeçalho de mercado (ativo, hora e preço, que são dados públicos). Não traz nomes de estratégia, condições, limites nem preços de entrada ou de stop. É gerado pelo robô e não vai para o GitHub (`.gitignore`).
