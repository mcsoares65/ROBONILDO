# ROBONILDO V2

Robô de day trade para WINFUT (mini-índice), operando via DDE com a plataforma
Profit Pro (Nelogica). Desenvolvido em conjunto por um "conselho" de IAs
(Claude, ChatGPT/Codex, Gemini, Grok, DeepSeek) — este repositório é onde essa
competição/colaboração passa a ter histórico real de verdade (commits, PRs,
diffs, tags), em vez de comentários manuais em `versionamento.py`.

## Como o projeto é organizado

- **`motor.py`** — orquestra a operação (candle a candle, abre/fecha posição).
  Não tem NENHUMA fórmula própria de stop/alvo (Regra 1, `compliance.md`) —
  isso é responsabilidade exclusiva da estratégia de saída titular.
- **`configuracao.py`** — parâmetros validados por backtest. Não alterar sem
  novo backtest + validação treino/teste (ver comentário no topo do arquivo).
- **`versionamento.py`** — `VERSAO`, fonte única de verdade (histórico
  detalhado de cada mudança). A partir deste repositório, `git tag`/PRs
  passam a ser o histórico real; `versionamento.py` continua existindo por
  compatibilidade com o que já estava em uso.
- **`compliance.md`** — as regras que toda estratégia (de qualquer autor,
  humano ou IA) deve seguir. É, na prática, o `CONTRIBUTING.md` deste
  projeto — leia antes de propor qualquer cartucho.
- **`classificacao.py`** — roda o backtest/ranking de estratégias contra o
  histórico oficial. É o juiz: nenhuma estratégia é promovida a titular sem
  passar por aqui.
- **`principal.py`** — laço de produção (ao vivo, via DDE). Espelha o mesmo
  contrato usado por `classificacao.py`.
- **`estrategia/entrada/titular/`** — exatamente 1 arquivo: a estratégia de
  entrada em produção.
- **`estrategia/entrada/`** — candidatas de entrada, uma por autor/ideia.
- **`estrategia/saida/titular/`** — exatamente 1 arquivo: a estratégia de
  saída em produção. Hoje é `baseline.py` (ver decisão abaixo).
- **`estrategia/saida/`** — candidatas de saída.

## Status da saída titular (decisão em aberto, 26/09/2026)

`baseline.py` está como titular. `saida_grok_v6.py` foi corrigido nesta
sessão (removida uma fórmula de stop emprestada indevidamente do motor —
ver `changelog.md`, versão V445) e hoje **não define nenhum stop de perda
próprio** — só o profit-lock pós-17:30 do autor original. Falta decidir:
desenhar uma regra de stop própria para ela, ou aceitar formalmente que ela
opera sem stop de perda intermediário.

## Como propor uma estratégia (qualquer IA ou pessoa)

1. Leia `compliance.md` inteiro primeiro — principalmente a Regra 1 (saída
   define seu próprio stop/alvo, motor não interfere) e a Regra 3 (cartucho
   não importa `configuracao.py` nem nenhum módulo do projeto — copie a
   constante que precisar e documente que é cópia).
2. Abra um branch com seu nome/autor: `grok/saida-v7`, `chatgpt/entrada-v22`.
3. Adicione o arquivo em `estrategia/entrada/` ou `estrategia/saida/`
   (nunca direto em `titular/`).
4. Abra um Pull Request. Uma Action roda `classificacao.py` automaticamente
   e posta o resultado no PR — a promoção a titular depende desse número,
   não de alegação de backtest anterior (Regra 4).
5. Mudança em `motor.py`, `compliance.md`, `configuracao.py`,
   `versionamento.py` ou em qualquer arquivo dentro de `titular/` exige
   aprovação humana (ver `CODEOWNERS`) — nenhuma IA promove a própria
   estratégia sozinha.

## Aviso sobre o que ainda não foi conferido nesta migração

Os arquivos abaixo foram trazidos para este repositório a partir do último
upload visto na conversa que organizou esta migração, mas **não foram lidos
ou revisados** nesta sessão — só copiados como estavam. Antes de tratar este
repositório como fonte de verdade para produção, confirme que são
realmente as versões que rodam no seu computador:

`gestor_risco.py`, `leitor_dde.py`, `construtor_candle.py`,
`executor_ordem.py`, `auditor_execucao.py`, `auditor_paridade.py`,
`frases_narracao.py`, `noticias.py`, `teste_email.py`, `_template.py`,
`_nucleo.py`.

Os demais (`motor.py`, `principal.py`, `configuracao.py`, `analise.py`,
`registrador.py`, `email_notificacao.py`, `versionamento.py`,
`compliance.md`, `changelog.md`, `classificacao.py`, e os cartuchos de
saída `baseline.py`/`saida_grok_v6.py`/`saida_claude_v4.py`) foram
lidos, editados e testados (`py_compile` + `classificacao.py` contra o
dataset oficial) nesta mesma sessão — confiança alta.

As candidatas de entrada e saída dos demais autores foram copiadas como
estavam no último upload, sem serem re-testadas aqui.
