"""
ROBONILDO - leitor_dde.py

Le o preco em tempo real do WIN via DDE do Profit. NAO EXISTE codigo pronto
reaproveitavel do projeto anterior para isso (o ROBONILDO_109 abandonou o DDE
e foi para captura visual - exatamente o caminho que decidimos nao seguir).

ABORDAGEM: em vez de um cliente DDE puro em Python (bibliotecas como PyDDE sao
antigas e mal mantidas), usa uma ponte via Excel: o Profit ja exporta em tempo
real para uma celula do Excel (funcao "Exportar em Tempo Real (RTD/DDE)" que
vimos no menu Arquivo do Profit). O robo controla esse Excel aberto via COM
(win32com) e le o valor da celula a cada leitura - o Excel faz o trabalho de
falar DDE com o Profit, o Python so le o resultado.

PRE-REQUISITO, a fazer manualmente no Profit + Excel antes de rodar:
  1. No Profit: Arquivo > Exportar em Tempo Real (RTD/DDE)
  2. Vincular os campos ATIVO, DATA, HORA e ULT do ativo desejado a uma LINHA
     qualquer da planilha (colunas A, B, C, D respectivamente) e deixar essa
     planilha aberta. NAO precisa ser uma linha fixa - o robo localiza a
     linha certa sozinho, buscando o nome do ativo na coluna A (ver
     localizar_ativo()). Isso elimina a necessidade de colar manualmente o
     ativo certo numa celula fixa toda vez que o Profit reinicia a exportacao.
  3. Preencher CAMINHO_PLANILHA abaixo, se o caminho/nome do arquivo for outro.

ESTE MODULO NAO FOI TESTADO no ambiente real (Windows + Profit + Excel) -
so pode ser validado na maquina onde o Profit roda de verdade.
"""

from datetime import datetime
from typing import Optional

CAMINHO_PLANILHA = r"D:\DAYTRADE\PLANO_TRADE.xlsx"  # AJUSTAR se o nome/local for outro
# V507: a planilha passou a se chamar PLANO_TRADE.xlsx. Enquanto o arquivo ainda tiver o nome
# antigo, o robo acha a planilha aberta por qualquer um destes nomes (o novo tem prioridade).
CAMINHOS_PLANILHA_ANTIGOS = (r"D:\DAYTRADE\PLANO_TRADE_MA_v2.xlsx",)
NOME_ABA_DDE = "DDE"          # aba onde o vínculo DDE do Profit esta configurado
NOME_ABA_GESTAO_RISCO = "GESTAO_RISCO"  # aba do plano de trade ja existente na planilha
CELULA_BANCA_ATUAL = "B3"     # celula onde o robo escreve a banca real, atualizada

# V507 - aba REGISTRO_OPERACOES: o robo escreve uma linha por operacao (abre na entrada,
# completa na saida). A coluna O guarda o id da operacao (horario de entrada ISO) para o robo
# achar a linha certa mesmo depois de reiniciar.
NOME_ABA_REGISTRO = "REGISTRO_OPERACOES"
LINHA_CABECALHO_REGISTRO = 4
PRIMEIRA_LINHA_REGISTRO = 5
LINHAS_BUSCA_REGISTRO = 3000
CABECALHO_REGISTRO = (
    "DATA", "HORA ENTRADA", "LADO", "ENTRADA", "STOP", "ALVO", "HORA SAIDA", "SAIDA",
    "MOTIVO SAIDA", "RESULTADO (pts)", "RESULTADO (R$)", "PICO (R$)", "DEVOLVEU (R$)",
    "BANCA APOS (R$)", "ID OPERACAO (robo)",
)
CABECALHO_REGISTRO_ANTIGO = (   # modelo MA_v2 da planilha, preenchido a mao
    "DATA", "HORARIO ENTRADA", "LADO", "FECHAMENTO", "MA21", "MA50", "DISTANCIA (pts)",
    "STOP", "ALVO (2R)", "SAIDA", "RESULTADO (pts)", "RESULTADO (R$)",
)

# ---------- Localizacao dinamica da linha do ativo (coluna A) ----------
# ANTES: linha fixa (D2/B2/C2) - exigia colar manualmente o ativo certo na
# linha 2 toda vez que o Profit reiniciava a exportacao. AGORA: busca o nome
# do ativo na COLUNA A e usa a linha onde encontrar - qualquer linha que o
# Profit usar, sem precisar copiar/colar nada manualmente.
COLUNA_ATIVO = "A"     # onde o nome do ativo aparece (ex: "WINV26" ou "[R] WINV26")
COLUNA_DATA = "B"
COLUNA_HORA = "C"
COLUNA_PRECO = "D"     # "Ultimo" (preco em tempo real) - NAO "Fechamento" (FEC, fechamento
                       # do dia ANTERIOR no DDE do Profit)
LINHA_MAXIMA_BUSCA = 200   # ate onde procurar na coluna A - ajustar se a planilha for maior
PREFIXO_REPLAY = "[R] "    # como o Profit rotula o ativo em modo Replay na coluna A -
                            # ajustar aqui se o Profit usar outro prefixo/formato

# V460 - COLETA PASSIVA (ver coleta_dde.py). A amostra DDE de 01/10/2026
# fornecida pelo dono mostra A=Asset, L=Quantidade e M=Volume financeiro.
# Apenas Quantidade (total do dia) e registrada em log: NAO e quantidade
# do candle, NAO entra em sinais nem alimenta ConstrutorCandle nesta etapa.
# Confirmar correspondencia A/L na planilha real e comparar deltas com o
# export M15 antes de habilitar qualquer decisao dependente de volume.
COLUNAS_EXTRAS_DDE = {"quantidade": "L"}

CELULA_CONTRATOS_ABERTOS = None   # DESATIVADO: o campo "Cont. Abertos" (CAB) do DDE mostrou
                                   # valores na casa de 1+ milhao em teste real - isso e
                                   # interesse em aberto do MERCADO inteiro, nao a posicao
                                   # pessoal da conta. O DDE do Profit aparentemente nao
                                   # expoe posicao de conta - so dados de mercado/cotacao.
                                   # A checagem cruzada de posicao real fica desativada ate
                                   # encontrarmos outra fonte de dado para isso.

# ---------- Checagens de integridade (prova real contra a tela do Profit) ----------
# Motivadas por discrepancia observada entre a leitura do DDE e o que o Profit
# de fato mostra na tela - sem uma segunda fonte de dado independente, essas
# checagens automaticas + o checkpoint sonoro periodico sao a defesa disponivel.
PRECO_CONGELADO_SEGUNDOS = 45      # preco identico por mais que isso, em horario de
                                    # pregao ativo (fora leiloes/aberturas), e suspeito -
                                    # WIN normalmente tem tick suficiente para nao ficar
                                    # parado tanto tempo com o mercado aberto de verdade
SALTO_MAXIMO_PONTOS = 400          # diferenca entre duas leituras consecutivas maior que
                                    # isso e suspeita de erro de leitura (parsing, glitch do
                                    # DDE) - nao um movimento real de mercado em poucos segundos
DERIVA_RELOGIO_MAXIMA_SEGUNDOS = 10  # diferenca tolerada entre o horario que o DDE
                                       # informa (campo Data/Hora) e o relógio real do
                                       # computador, FORA de replay - acima disso, o
                                       # vínculo DDE pode estar travado/atrasado
AVISO_INTEGRIDADE_REPETIR_SEGUNDOS = 120  # V486: o MESMO tipo de aviso de integridade
                                           # (salto / preco parado / deriva de relogio) so e
                                           # impresso e narrado de novo depois disso. Antes
                                           # saia um por iteracao (~2s): em 05/10/2026 foram
                                           # 825 avisos em 27 min e a voz ficou lendo-os por
                                           # mais de 2 horas (fila do SAPI sem descarte).
FALHA_LEITURA_IMPRIMIR_SEGUNDOS = 30  # V498: no maximo uma linha de "Falha ao ler ..." a cada 30 s
CHECKPOINT_NARRACAO_SEGUNDOS = 600  # a cada 10 minutos, narra o preco atual em voz alta -
                                      # da pra voce conferir contra a tela do Profit sem
                                      # precisar ficar vigiando o tempo todo


class LeitorDDE:
    def __init__(self, caminho_planilha: str = CAMINHO_PLANILHA):
        self.caminho_planilha = caminho_planilha
        self._excel = None
        self._planilha = None
        self._linha_ativo: Optional[int] = None  # descoberta por localizar_ativo(), antes do 1o uso
        # estado para as checagens de integridade
        self._ultimo_preco: Optional[float] = None
        self._ultima_mudanca_preco: Optional[datetime] = None
        self._ultimo_checkpoint: Optional[datetime] = None
        # V498: ultima causa de falha de leitura (o principal usa para narrar) e
        # controle para nao imprimir uma linha de falha a cada 3 segundos
        self.ultimo_erro_leitura: Optional[str] = None
        self._ultima_falha_impressa: Optional[datetime] = None
        self._falhas_suprimidas = 0

    def _avisar_falha_leitura(self, o_que: str, tentativas: int, erro, consequencia: str):
        """V498: uma linha de falha por FALHA_LEITURA_IMPRIMIR_SEGUNDOS (antes saia uma a
        cada ~3 s, enchendo o console sem dizer nada de novo). O principal narra."""
        self.ultimo_erro_leitura = str(erro) if erro is not None else None
        agora = datetime.now()
        if (self._ultima_falha_impressa is not None and
                (agora - self._ultima_falha_impressa).total_seconds() < FALHA_LEITURA_IMPRIMIR_SEGUNDOS):
            self._falhas_suprimidas += 1
            return
        detalhe = f": {erro}" if erro is not None else ""
        extra = (f" (+{self._falhas_suprimidas} falhas iguais omitidas)"
                 if self._falhas_suprimidas else "")
        print(f"[LEITOR_DDE] Falha ao ler {o_que} apos {tentativas} tentativas{detalhe} - "
              f"{consequencia}{extra}")
        self._ultima_falha_impressa = agora
        self._falhas_suprimidas = 0

    def conectar(self):
        try:
            import win32com.client
        except ImportError as e:
            raise RuntimeError(
                "pywin32 nao instalado. Rodar: pip install pywin32"
            ) from e

        # V498: tenta primeiro achar a PLANILHA pelo nome na tabela de objetos em execucao
        # (ROT) do Windows, em qualquer instancia do Excel. Assim o DDE pode ficar numa
        # instancia propria do Excel (aberta so com ele) e mexer em outras planilhas na
        # outra instancia nao tranca a leitura (RPC_E_CALL_REJECTED). Se nao achar, ou se
        # qualquer coisa falhar, segue EXATAMENTE o caminho de antes (GetActiveObject).
        try:
            planilha_rot = None
            for caminho in self._candidatos_planilha():   # V507: nome novo, depois o antigo
                planilha_rot = self._achar_planilha_na_rot(caminho)
                if planilha_rot is not None:
                    self.caminho_planilha = caminho
                    break
            if planilha_rot is not None:
                planilha_rot.Sheets(NOME_ABA_DDE)  # teste de fogo: a aba do DDE responde?
        except Exception as e:
            print(f"[LEITOR_DDE] Busca da planilha por nome indisponivel ({e}); "
                  f"usando o Excel ativo.")
            planilha_rot = None
        if planilha_rot is not None:
            self._planilha = planilha_rot
            self._excel = getattr(planilha_rot, "Application", None)
            print(f"[LEITOR_DDE] Planilha '{self.caminho_planilha}' encontrada pelo nome "
                  f"(instancia propria do Excel, se voce a abriu separada).")
            return

        # GetActiveObject conecta ao Excel JA ABERTO (o mesmo com o vínculo DDE ativo).
        # Dispatch() criaria uma SEGUNDA instancia invisivel, que nao teria o vinculo
        # DDE configurado e entraria em conflito com a instancia original - foi a
        # causa do erro "chamada rejeitada pelo chamado" (RPC_E_CALL_REJECTED).
        try:
            self._excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception as e:
            raise RuntimeError(
                "Nao foi possivel conectar a uma instancia do Excel ja aberta. "
                "Abra o Excel com a planilha (e o vínculo DDE configurado) ANTES "
                "de rodar este script."
            ) from e

        aberta = None
        candidatos = [c.lower() for c in self._candidatos_planilha()]
        for wb in self._excel.Workbooks:
            if wb.FullName.lower() in candidatos:
                aberta = wb
                self.caminho_planilha = wb.FullName
                break
        if aberta is None:
            raise RuntimeError(
                f"O Excel esta aberto, mas nao encontrei a planilha "
                f"'{self.caminho_planilha}' entre as abertas. Verifique o caminho "
                f"em CAMINHO_PLANILHA ou abra o arquivo correto."
            )
        self._planilha = aberta

    def _candidatos_planilha(self):
        vistos, saida = set(), []
        for c in (self.caminho_planilha, *CAMINHOS_PLANILHA_ANTIGOS):
            if c.lower() not in vistos:
                vistos.add(c.lower())
                saida.append(c)
        return saida

    def _achar_planilha_na_rot(self, caminho=None):
        """Procura na Running Object Table a pasta de trabalho com o caminho configurado.
        NAO abre o arquivo se ele nao estiver aberto (so enumera o que ja esta em
        execucao). Devolve o Workbook ou None."""
        import pythoncom
        import win32com.client
        rot = pythoncom.GetRunningObjectTable()
        contexto = pythoncom.CreateBindCtx(0)
        alvo = (caminho or self.caminho_planilha).lower()
        for moniker in rot.EnumRunning():
            try:
                nome = moniker.GetDisplayName(contexto, None)
            except Exception:
                continue
            if str(nome).lower() != alvo:
                continue
            objeto = rot.GetObject(moniker)
            despachante = objeto.QueryInterface(pythoncom.IID_IDispatch)
            return win32com.client.Dispatch(despachante)
        return None

    def localizar_ativo(self, nome_ativo: str) -> int:
        """
        Busca `nome_ativo` na COLUNA_ATIVO (coluna A), linha por linha, ate
        LINHA_MAXIMA_BUSCA - e guarda a linha encontrada para uso por
        ler_preco()/ler_horario_mercado(). Resolve o problema de precisar colar
        manualmente o ativo certo numa linha fixa toda vez que o Profit reinicia
        a exportacao - agora o robo acha a linha sozinho.

        Chamar UMA VEZ, logo apos conectar() e antes do primeiro ler_preco().

        Levanta RuntimeError se nao encontrar - melhor falhar alto e claro aqui
        do que o robo rodar o dia inteiro lendo a celula errada sem avisar.
        """
        if self._planilha is None:
            raise RuntimeError("Chame conectar() antes de localizar_ativo().")

        aba = self._planilha.Sheets(NOME_ABA_DDE)
        alvo = nome_ativo.strip().upper()
        for linha in range(1, LINHA_MAXIMA_BUSCA + 1):
            valor = aba.Range(f"{COLUNA_ATIVO}{linha}").Value
            if valor is None:
                continue
            if str(valor).strip().upper() == alvo:
                self._linha_ativo = linha
                print(f"[LEITOR_DDE] Ativo '{nome_ativo}' encontrado na linha {linha} da coluna {COLUNA_ATIVO}.")
                return linha

        raise RuntimeError(
            f"Ativo '{nome_ativo}' NAO encontrado na coluna {COLUNA_ATIVO} "
            f"(procurado da linha 1 ate {LINHA_MAXIMA_BUSCA}) da aba '{NOME_ABA_DDE}'. "
            f"Confira se o Profit esta exportando esse ativo para a planilha, e se o "
            f"nome bate exatamente (maiusculas/minusculas nao importam, espacos nas "
            f"pontas sao ignorados, mas o resto do texto precisa ser identico)."
        )

    def ler_preco(self, tentativas: int = 3, espera_segundos: float = 0.5) -> Optional[float]:
        """
        Le o preco com nova tentativa em caso de falha - o proprio Profit avisou
        que o DDE tem instabilidade conhecida (atualizacao do Windows), entao uma
        falha pontual de leitura nao deve derrubar o robo inteiro.

        Retorna None (em vez de lancar excecao) se todas as tentativas falharem -
        quem chama deve tratar None como "pular esta leitura, tentar na proxima".
        """
        import time as _time
        if self._planilha is None:
            raise RuntimeError("Chame conectar() antes de ler_preco().")
        if self._linha_ativo is None:
            raise RuntimeError("Chame localizar_ativo() antes de ler_preco().")

        ultimo_erro = None
        for tentativa in range(1, tentativas + 1):
            try:
                celula = f"{COLUNA_PRECO}{self._linha_ativo}"
                valor = self._planilha.Sheets(NOME_ABA_DDE).Range(celula).Value
                if valor is not None:
                    self.ultimo_erro_leitura = None
                    return float(valor)
            except Exception as e:
                ultimo_erro = e
            _time.sleep(espera_segundos)

        self._avisar_falha_leitura("preco", tentativas, ultimo_erro,
                                   "pulando esta leitura (instabilidade conhecida do DDE).")
        return None

    def ler_horario_mercado(self, tentativas: int = 3, espera_segundos: float = 0.5) -> Optional[datetime]:
        """
        Le a Data e a Hora que vem no proprio DDE do Profit - ESSENCIAL para
        replay, onde o horario do mercado simulado e completamente diferente
        do relógio real do computador. Em operacao ao vivo de verdade, os dois
        coincidiriam, mas usar datetime.now() quebraria todas as regras de
        horario (janelas bloqueadas, corte de seguranca) durante um replay.

        Com nova tentativa, igual ler_preco(), pela mesma instabilidade conhecida
        do DDE.
        """
        if self._planilha is None:
            return None
        if self._linha_ativo is None:
            return None

        import time as _time
        ultimo_erro = None
        for tentativa in range(1, tentativas + 1):
            try:
                aba = self._planilha.Sheets(NOME_ABA_DDE)
                data_str = aba.Range(f"{COLUNA_DATA}{self._linha_ativo}").Value
                hora_str = aba.Range(f"{COLUNA_HORA}{self._linha_ativo}").Value
                if data_str is None or hora_str is None:
                    return None
                if isinstance(data_str, datetime):
                    data_str = data_str.strftime("%d/%m/%Y")
                if isinstance(hora_str, datetime):
                    hora_str = hora_str.strftime("%H:%M:%S")
                return datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M:%S")
            except Exception as e:
                ultimo_erro = e
                _time.sleep(espera_segundos)

        self._avisar_falha_leitura("horario", tentativas, ultimo_erro, "pulando esta leitura.")
        return None

    def verificar_integridade(self, preco_atual: float, horario_mercado: datetime,
                               modo_replay: bool = False) -> list:
        """
        "Prova real" contra a tela do Profit - detecta os sintomas mais comuns de
        um vínculo DDE com problema, sem precisar de uma segunda fonte de dado:

          1. Preco CONGELADO por tempo demais (DDE travou, Profit continua andando)
          2. SALTO implausivel entre duas leituras (erro de parsing/glitch pontual)
          3. DERIVA DE RELOGIO entre o horario do DDE e o relógio real (so fora
             de replay - em replay os dois relogios sao esperados divergir)

        Devolve uma lista de avisos (strings) - vazia se nada suspeito. Quem
        chama decide o que fazer com os avisos (narrar, logar, pausar).
        Atualiza o estado interno (ultimo preco/hora) a cada chamada.
        """
        avisos = []
        agora_real = datetime.now()

        if self._ultimo_preco is not None:
            se_mudou = preco_atual != self._ultimo_preco
            if se_mudou:
                salto = abs(preco_atual - self._ultimo_preco)
                if salto > SALTO_MAXIMO_PONTOS:
                    avisos.append(
                        f"Salto suspeito de {salto:.0f} pontos entre leituras "
                        f"({self._ultimo_preco:.0f} para {preco_atual:.0f}) - "
                        f"confira a tela do Profit."
                    )
                self._ultima_mudanca_preco = agora_real
            elif self._ultima_mudanca_preco is not None:
                parado_ha = (agora_real - self._ultima_mudanca_preco).total_seconds()
                if parado_ha > PRECO_CONGELADO_SEGUNDOS:
                    avisos.append(
                        f"Preço parado em {preco_atual:.0f} há {parado_ha:.0f} segundos - "
                        f"possível travamento do vínculo DDE, confira a tela do Profit."
                    )
        else:
            self._ultima_mudanca_preco = agora_real

        self._ultimo_preco = preco_atual

        if not modo_replay and horario_mercado is not None:
            deriva = abs((agora_real - horario_mercado).total_seconds())
            if deriva > DERIVA_RELOGIO_MAXIMA_SEGUNDOS:
                avisos.append(
                    f"Horário do DDE ({horario_mercado.strftime('%H:%M:%S')}) está "
                    f"{deriva:.0f} segundos distante do relógio real - vínculo pode "
                    f"estar atrasado."
                )

        return avisos

    def checkpoint_devido(self) -> bool:
        """
        True quando ja se passou CHECKPOINT_NARRACAO_SEGUNDOS desde o ultimo
        checkpoint sonoro - quem chama narra o preco atual e marca o checkpoint
        como feito via marcar_checkpoint_feito().
        """
        if self._ultimo_checkpoint is None:
            return True
        return (datetime.now() - self._ultimo_checkpoint).total_seconds() >= CHECKPOINT_NARRACAO_SEGUNDOS

    def marcar_checkpoint_feito(self):
        self._ultimo_checkpoint = datetime.now()

    def ler_extras(self) -> dict:
        """V460: le os campos extras configurados em COLUNAS_EXTRAS_DDE, uma
        leitura por coluna, sem nova tentativa. Best-effort: devolve {} se nada
        configurado e None no campo que falhar. Nunca lanca excecao."""
        saida = {}
        if not COLUNAS_EXTRAS_DDE or self._planilha is None or self._linha_ativo is None:
            return saida
        for nome, coluna in COLUNAS_EXTRAS_DDE.items():
            try:
                v = self._planilha.Sheets(NOME_ABA_DDE).Range(f"{coluna}{self._linha_ativo}").Value
                saida[nome] = None if v is None else float(v)
            except Exception:
                saida[nome] = None
        return saida

    def ler_contratos_abertos(self) -> Optional[int]:
        """Le o campo CAB (Contratos Abertos) para checagem cruzada de posicao real,
        conforme identificado na lista de campos DDE do Profit.

        Retorna None se a coluna CAB ainda nao estiver configurada na planilha -
        nesse caso, a checagem cruzada em principal.py fica desativada e um aviso
        deveria ser considerado, ja que essa protecao existe justamente para pegar
        divergencia entre o estado interno do robo e a posicao real na corretora."""
        if self._planilha is None or CELULA_CONTRATOS_ABERTOS is None:
            return None
        valor = self._planilha.Sheets(NOME_ABA_DDE).Range(CELULA_CONTRATOS_ABERTOS).Value
        if valor is None:
            return None
        return int(valor)

    def escrever_banca_atual(self, valor: float):
        """Atualiza a celula da banca atual na aba GESTAO_RISCO da planilha,
        assim o plano de trade reflete o capital real, nao um valor fixo estatico."""
        if self._planilha is None:
            return
        try:
            self._planilha.Sheets(NOME_ABA_GESTAO_RISCO).Range(CELULA_BANCA_ATUAL).Value = valor
        except Exception as e:
            print(f"[LEITOR_DDE] Falha ao atualizar banca atual na planilha: {e}")

    # ---------- V507: aba REGISTRO_OPERACOES ----------
    @staticmethod
    def _celula_texto(v):
        return "" if v is None else str(v).strip()

    def preparar_registro_operacoes(self) -> bool:
        """Confere a aba REGISTRO_OPERACOES e a deixa pronta para o robo. Idempotente:
        - cabecalho ja e o novo -> nada a fazer;
        - cabecalho e o modelo antigo (MA_v2, preenchido a mao) -> troca titulo e cabecalho e
          limpa a linha de exemplo que veio no modelo (so se for a conhecida);
        - qualquer outra coisa -> NAO mexe e desliga o registro (nao sobrescrever dado do dono).
        Devolve True se o robo pode gravar. Nunca lanca excecao."""
        self._registro_ok = False
        if self._planilha is None:
            return False
        try:
            ws = self._planilha.Sheets(NOME_ABA_REGISTRO)
            n = len(CABECALHO_REGISTRO)
            lc = LINHA_CABECALHO_REGISTRO
            atual = tuple(self._celula_texto(ws.Range(f"{chr(65 + i)}{lc}").Value) for i in range(n))
            if atual == CABECALHO_REGISTRO:
                self._registro_ok = True
                return True
            antigo = atual[:len(CABECALHO_REGISTRO_ANTIGO)] == CABECALHO_REGISTRO_ANTIGO and not any(atual[len(CABECALHO_REGISTRO_ANTIGO):])
            if not antigo:
                print(f"[REGISTRO] A aba '{NOME_ABA_REGISTRO}' tem um cabecalho que o robo nao conhece; "
                      f"nao vou escrever nela. Apague a linha {lc} ou restaure o cabecalho do modelo.")
                return False
            ws.Range("A1").Value = "REGISTRO DE OPERAÇÕES — ROBONILDO"
            ws.Range("A2").Value = ("Preenchido pelo robô: uma linha por operação (abre na entrada, completa na saída). "
                                    "Resultado em R$ já líquido de custos. Não edite a coluna O.")
            for i, nome in enumerate(CABECALHO_REGISTRO):
                ws.Range(f"{chr(65 + i)}{lc}").Value = nome
            # linha de exemplo do modelo antigo (17/08/2026) e a observacao logo abaixo
            if (self._celula_texto(ws.Range("A5").Value).startswith("17/08/2026")
                    and self._celula_texto(ws.Range("A6").Value).startswith("(linha de exemplo")):
                ws.Range("A5:O6").ClearContents()
            self._registro_ok = True
            print(f"[REGISTRO] Aba '{NOME_ABA_REGISTRO}' preparada para o robo.")
            return True
        except Exception as e:
            print(f"[REGISTRO] Nao foi possivel preparar a aba '{NOME_ABA_REGISTRO}': {e}")
            return False

    def _com_tentativas(self, funcao, tentativas=3, espera=0.5):
        import time
        ultimo = None
        for _ in range(tentativas):
            try:
                return funcao()
            except Exception as e:   # Excel ocupado recalculando o DDE: RPC_E_CALL_REJECTED
                ultimo = e
                time.sleep(espera)
        raise ultimo

    def _linha_da_operacao(self, ws, id_operacao):
        """Linha onde esta o id (coluna O) ou None; devolve tambem a primeira linha livre."""
        ini = PRIMEIRA_LINHA_REGISTRO
        fim = ini + LINHAS_BUSCA_REGISTRO - 1
        col_o = ws.Range(f"O{ini}:O{fim}").Value
        col_a = ws.Range(f"A{ini}:A{fim}").Value
        achada, livre = None, None
        for k in range(len(col_o)):
            o = col_o[k][0] if isinstance(col_o[k], (tuple, list)) else col_o[k]
            a = col_a[k][0] if isinstance(col_a[k], (tuple, list)) else col_a[k]
            if o is not None and self._celula_texto(o) == id_operacao:
                achada = ini + k
            if livre is None and o is None and a is None:
                livre = ini + k
        return achada, livre

    @staticmethod
    def _fracao_dia(dt):
        return (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400.0

    def registrar_abertura_planilha(self, posicao):
        """Grava a linha da operacao ao abrir (data, hora, lado, entrada, stop, alvo)."""
        if self._planilha is None or not getattr(self, "_registro_ok", False):
            return
        try:
            self._com_tentativas(lambda: self._gravar_abertura(posicao))
        except Exception as e:
            print(f"[REGISTRO] Falha ao registrar a abertura na planilha: {e}")

    def _gravar_abertura(self, posicao):
        ws = self._planilha.Sheets(NOME_ABA_REGISTRO)
        id_op = posicao.horario_entrada
        achada, livre = self._linha_da_operacao(ws, id_op)
        if achada is not None:
            return   # ja existe (robo reiniciado com a posicao aberta): nao duplica
        if livre is None:
            raise RuntimeError("aba REGISTRO_OPERACOES cheia")
        t = datetime.fromisoformat(id_op)
        ws.Range(f"A{livre}").Value = t.replace(hour=0, minute=0, second=0, microsecond=0)
        ws.Range(f"A{livre}").NumberFormat = "dd/mm/yyyy"
        ws.Range(f"B{livre}").Value = self._fracao_dia(t)
        ws.Range(f"B{livre}").NumberFormat = "hh:mm:ss"
        ws.Range(f"C{livre}").Value = posicao.lado
        ws.Range(f"D{livre}").Value = posicao.entrada
        ws.Range(f"E{livre}").Value = "" if posicao.stop is None else posicao.stop
        ws.Range(f"F{livre}").Value = "" if posicao.alvo is None else posicao.alvo
        ws.Range(f"O{livre}").NumberFormat = "@"
        ws.Range(f"O{livre}").Value = id_op

    def registrar_fechamento_planilha(self, posicao, horario_saida, saida, motivo,
                                      resultado_pts, resultado_reais, pico_reais=None, devolveu_reais=None,
                                      banca=None):
        """Completa a linha da operacao na saida. Se a linha de abertura nao existir (falhou ou
        o robo foi iniciado depois), cria a linha ja completa."""
        if self._planilha is None or not getattr(self, "_registro_ok", False):
            return
        try:
            self._com_tentativas(lambda: self._gravar_fechamento(
                posicao, horario_saida, saida, motivo, resultado_pts, resultado_reais, pico_reais,
                devolveu_reais, banca))
        except Exception as e:
            print(f"[REGISTRO] Falha ao registrar o fechamento na planilha: {e}")

    def _gravar_fechamento(self, posicao, horario_saida, saida, motivo, resultado_pts,
                           resultado_reais, pico_reais, devolveu_reais, banca):
        ws = self._planilha.Sheets(NOME_ABA_REGISTRO)
        id_op = posicao.horario_entrada
        achada, _ = self._linha_da_operacao(ws, id_op)
        if achada is None:
            self._gravar_abertura(posicao)
            achada, _ = self._linha_da_operacao(ws, id_op)
            if achada is None:
                raise RuntimeError("linha da operacao nao encontrada")
        r = achada
        ws.Range(f"G{r}").Value = self._fracao_dia(horario_saida)
        ws.Range(f"G{r}").NumberFormat = "hh:mm:ss"
        ws.Range(f"H{r}").Value = saida
        ws.Range(f"I{r}").Value = motivo
        ws.Range(f"J{r}").Value = round(resultado_pts, 1)
        ws.Range(f"K{r}").Value = round(resultado_reais, 2)
        if pico_reais is not None:
            ws.Range(f"L{r}").Value = round(pico_reais, 2)
        if devolveu_reais is not None:
            ws.Range(f"M{r}").Value = round(devolveu_reais, 2)
        if banca is not None:
            ws.Range(f"N{r}").Value = round(banca, 2)
        # stop/alvo podem ter sido reconfigurados pelo cartucho de saida depois da abertura
        ws.Range(f"E{r}").Value = "" if posicao.stop is None else posicao.stop
        ws.Range(f"F{r}").Value = "" if posicao.alvo is None else posicao.alvo

    def desconectar(self):
        # NAO fecha o Excel (self._excel.Quit()) - a instancia e a que o usuario
        # abriu manualmente com o vínculo DDE configurado, fechar destruiria isso.
        # So limpa as referencias do lado do Python.
        self._excel = None
        self._planilha = None


def ler_preco_atual(leitor: LeitorDDE) -> float:
    """Funcao de conveniencia para uso em principal.py."""
    return leitor.ler_preco()
