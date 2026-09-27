"""
ROBONILDO - executor_ordem.py

Envia ordens de verdade para o Profit, usando os atalhos de teclado documentados
no projeto anterior (ALT+C compra, ALT+V venda, ALT+Z encerra posicao).

SEGURANCA:
  - So executa se cfg.ENVIAR_ORDENS for True (travado em False por padrao).
  - Antes de qualquer tecla, confirma que a janela do Profit esta em foco -
    nunca envia tecla "no escuro" para a janela errada.
  - Pensado para uso em conta SIMULADA (replay/demo) nesta fase. Usar com
    capital real exige reavaliar esse modulo, nao so trocar ENVIAR_ORDENS.
"""

import time
from typing import Optional

import configuracao as cfg


class FocoProfit:
    """Encontra e confirma foco na janela do Profit, evitando enviar tecla para
    a janela errada (editor de texto, terminal, etc.)."""

    JANELAS_IGNORADAS = ["notepad", "code.exe", "cmd.exe", "powershell", "terminal"]

    def __init__(self, nome_janela: str = None):
        self.nome_janela = nome_janela or cfg.NOME_TELA_PROFIT

    @staticmethod
    def _processo_elevado(pid: int):
        """
        True/False se conseguir determinar, None se nao (ex: sem permissao
        para abrir o processo). Usado so para diagnostico - nunca bloqueia o
        envio, so ajuda a explicar POR QUE um envio pode estar falhando
        silenciosamente: o Windows (UIPI - User Interface Privilege Isolation)
        bloqueia SEM AVISO o envio de teclas sinteticas de um processo comum
        para um processo elevado (Administrador). Se o Profit estiver rodando
        como Administrador e o Python nao estiver, keybd_event() "funciona"
        (sem excecao) mas a tecla nunca chega no Profit - exatamente o
        sintoma relatado (log diz "Enviado ALT+C", Profit nao recebe nada).
        """
        try:
            import win32api
            import win32con
            import win32security
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
            token = win32security.OpenProcessToken(handle, win32con.TOKEN_QUERY)
            elevacao = win32security.GetTokenInformation(token, win32security.TokenElevation)
            return bool(elevacao)
        except Exception:
            return None

    def diagnosticar(self):
        """Imprime informacao detalhada da janela encontrada (titulo exato,
        PID, elevacao) e do proprio processo Python - para investigar envios
        que 'funcionam' no log mas nao chegam no Profit de verdade."""
        try:
            import win32gui
            import win32process
            import win32api
        except ImportError:
            print("[EXECUTOR_ORDEM] [DIAGNOSTICO] pywin32 nao disponivel.")
            return

        hwnd = self.encontrar_janela()
        pid_nosso = win32api.GetCurrentProcessId()
        elevado_nosso = self._processo_elevado(pid_nosso)
        print(f"[EXECUTOR_ORDEM] [DIAGNOSTICO] Processo Python: PID={pid_nosso} "
              f"elevado(Administrador)={elevado_nosso}")

        if hwnd is None:
            print(f"[EXECUTOR_ORDEM] [DIAGNOSTICO] Nenhuma janela contendo "
                  f"'{self.nome_janela}' foi encontrada.")
            return

        titulo_exato = win32gui.GetWindowText(hwnd)
        pid_profit = win32process.GetWindowThreadProcessId(hwnd)[1]
        elevado_profit = self._processo_elevado(pid_profit)
        print(f"[EXECUTOR_ORDEM] [DIAGNOSTICO] Janela encontrada: titulo exato="
              f"{titulo_exato!r} | hwnd={hwnd} | PID={pid_profit} | "
              f"elevado(Administrador)={elevado_profit}")

        if elevado_nosso is False and elevado_profit is True:
            print("[EXECUTOR_ORDEM] [DIAGNOSTICO] *** SUSPEITO ENCONTRADO ***: "
                  "o Profit esta rodando como Administrador e o Python NAO esta. "
                  "O Windows (UIPI) bloqueia silenciosamente o envio de teclas "
                  "nessa situacao - keybd_event() nao gera erro, mas a tecla "
                  "nunca chega no Profit. Solucao: rodar o Python TAMBEM como "
                  "Administrador (ou o Profit sem elevacao).")
        elif elevado_nosso is None or elevado_profit is None:
            print("[EXECUTOR_ORDEM] [DIAGNOSTICO] Nao foi possivel determinar "
                  "a elevacao de um dos dois processos (permissao negada ao "
                  "consultar) - verifique manualmente clicando com o botao "
                  "direito em cada processo no Gerenciador de Tarefas, aba "
                  "'Detalhes', coluna 'Elevado'.")

    def encontrar_janela(self):
        try:
            import win32gui
        except ImportError as e:
            raise RuntimeError("pywin32 nao instalado. Rodar: pip install pywin32") from e

        janela_encontrada = []

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            titulo = win32gui.GetWindowText(hwnd)
            if not titulo:
                return
            titulo_lower = titulo.lower()
            if any(ignorada in titulo_lower for ignorada in self.JANELAS_IGNORADAS):
                return
            if self.nome_janela.lower() in titulo_lower:
                janela_encontrada.append(hwnd)

        win32gui.EnumWindows(callback, None)
        return janela_encontrada[0] if janela_encontrada else None

    def focar(self) -> bool:
        try:
            import win32gui
            import win32process
            import win32api
            import win32con
        except ImportError as e:
            raise RuntimeError("pywin32 nao instalado. Rodar: pip install pywin32") from e

        hwnd = self.encontrar_janela()
        if hwnd is None:
            print(f"[EXECUTOR_ORDEM] Janela do Profit ('{self.nome_janela}') nao encontrada.")
            return False

        # O Windows bloqueia deliberadamente que um processo em segundo plano
        # roube o foco enquanto o usuario esta digitando ativamente em outra
        # janela (protecao contra sequestro de foco). SetForegroundWindow()
        # sozinho pode falhar silenciosamente nessa situacao.
        #
        # Solucao: "anexar" temporariamente a fila de entrada do nosso processo
        # a do processo que esta em primeiro plano agora - isso contorna a
        # restricao de forma legitima (tecnica padrao de automacao no Windows).
        hwnd_atual = win32gui.GetForegroundWindow()
        # GetForegroundWindow pode devolver 0 durante uma troca de janela. Nesse
        # caso GetWindowThreadProcessId(0) tambem devolve thread 0 e o Windows
        # responde erro 87 (parametro incorreto) ao AttachThreadInput.
        thread_atual = (win32process.GetWindowThreadProcessId(hwnd_atual)[0]
                        if hwnd_atual else 0)
        thread_nosso = win32api.GetCurrentThreadId()
        thread_profit = win32process.GetWindowThreadProcessId(hwnd)[0]

        anexado_atual = False
        anexado_profit = False
        try:
            # AttachThreadInput e apenas uma ajuda para vencer a protecao de
            # foco do Windows. Uma falha aqui nao pode derrubar o robo: ainda
            # tentamos restaurar/focar a janela e confirmamos o foco antes de
            # enviar qualquer tecla.
            try:
                if thread_atual and thread_atual != thread_nosso:
                    win32process.AttachThreadInput(thread_nosso, thread_atual, True)
                    anexado_atual = True
                if thread_profit and thread_profit != thread_nosso:
                    win32process.AttachThreadInput(thread_nosso, thread_profit, True)
                    anexado_profit = True
            except Exception as e:
                print(f"[EXECUTOR_ORDEM] AttachThreadInput indisponivel ({e}); "
                      "tentando foco direto com seguranca.")

            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            except Exception as e:
                print(f"[EXECUTOR_ORDEM] Nao foi possivel ativar a janela do Profit: {e}")
                return False
            time.sleep(0.2)  # da tempo do Windows processar a troca de foco

            janela_ativa = win32gui.GetForegroundWindow()
            if janela_ativa != hwnd:
                print("[EXECUTOR_ORDEM] Falha ao confirmar foco na janela do Profit "
                      "mesmo apos forcar (AttachThreadInput).")
                return False
            return True
        finally:
            # sempre desanexa, mesmo se algo falhar acima - nao deixar a fila
            # de entrada permanentemente ligada entre processos
            if anexado_atual:
                try:
                    win32process.AttachThreadInput(thread_nosso, thread_atual, False)
                except Exception as e:
                    print(f"[EXECUTOR_ORDEM] Aviso ao desanexar foco atual: {e}")
            if anexado_profit:
                try:
                    win32process.AttachThreadInput(thread_nosso, thread_profit, False)
                except Exception as e:
                    print(f"[EXECUTOR_ORDEM] Aviso ao desanexar foco do Profit: {e}")


class ExecutorOrdem:
    def __init__(self):
        self.foco = FocoProfit()

    def _enviar_tecla(self, combinacao: str) -> bool:
        if not cfg.ENVIAR_ORDENS:
            print(f"[EXECUTOR_ORDEM] ENVIAR_ORDENS=False - NAO enviando '{combinacao}' "
                  f"(modo somente alerta/registro).")
            return False

        try:
            foco_confirmado = self.foco.focar()
        except Exception as e:
            # A automacao do Windows nunca pode encerrar o processo principal.
            print(f"[EXECUTOR_ORDEM] Falha inesperada ao preparar foco: {e}")
            foco_confirmado = False

        if not foco_confirmado:
            print(f"[EXECUTOR_ORDEM] Ordem '{combinacao}' CANCELADA - "
                  f"nao foi possivel confirmar foco na janela do Profit.")
            return False

        try:
            import win32api
            import win32con
            import win32gui
        except ImportError as e:
            raise RuntimeError("pywin32 nao instalado. Rodar: pip install pywin32") from e

        # verificacao final, bem no instante de enviar - reduz ao maximo a
        # janela de tempo entre "confirmamos foco" e "apertamos a tecla",
        # onde o usuario digitando em outro lugar poderia roubar o foco de volta
        hwnd_profit = self.foco.encontrar_janela()
        if hwnd_profit is None or win32gui.GetForegroundWindow() != hwnd_profit:
            print(f"[EXECUTOR_ORDEM] Ordem '{combinacao}' CANCELADA - o foco mudou "
                  f"no ultimo instante antes do envio (provavelmente o usuario "
                  f"estava digitando em outra janela).")
            return False

        # DIAGNOSTICO: investigando relato de "log diz enviado, Profit nao
        # recebe" - imprime titulo exato da janela, PID e elevacao dos dois
        # processos a cada envio, ate a causa ser confirmada. Remover/silenciar
        # depois que o problema for resolvido (fica bem verboso).
        self.foco.diagnosticar()

        # win32con NAO tem constantes VK_C/VK_V/VK_Z - teclas de letra usam o
        # proprio codigo ASCII da letra maiuscula (nao existe VK_A..VK_Z no Windows)
        mapa_teclas = {"C": ord("C"), "V": ord("V"), "Z": ord("Z")}
        tecla = mapa_teclas[combinacao]

        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)       # ALT down
        win32api.keybd_event(tecla, 0, 0, 0)                   # tecla down
        time.sleep(0.05)
        win32api.keybd_event(tecla, 0, win32con.KEYEVENTF_KEYUP, 0)      # tecla up
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)  # ALT up

        print(f"[EXECUTOR_ORDEM] Enviado ALT+{combinacao} para o Profit.")
        return True

    def comprar(self) -> bool:
        return self._enviar_tecla("C")

    def vender(self) -> bool:
        return self._enviar_tecla("V")

    def encerrar_posicao(self) -> bool:
        return self._enviar_tecla("Z")
