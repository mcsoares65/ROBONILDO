"""
noticias.py — Robonildo V2

Script único de notícias financeiras pra narração e exibição no
terminal. Busca manchetes via RSS (fontes brasileiras + Investing.com),
filtra por relevância ao ativo (WIN/Ibovespa) e lista direto no prompt,
coloridas por categoria.

IMPORTANTE: uso estritamente informativo. Este módulo NUNCA deve
alimentar a lógica de entrada/saída em estrategia/. O edge estatístico
validado (PF Teste Longo/Curto) foi medido só com preço e indicadores
técnicos — misturar notícia na decisão de trade reabriria a porta pra
complexidade não validada (o mesmo problema que matou o v107).

Uso:
    python noticias.py

Ctrl+C pra parar.

Requer: pip install feedparser colorama deep-translator
(deep-translator é opcional: sem ele, as manchetes em inglês
continuam aparecendo, só que sem tradução)
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
from colorama import init, Fore, Style

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    _TRADUTOR_DISPONIVEL = True
except ImportError:
    _TRADUTOR_DISPONIVEL = False

init(autoreset=True)

# ---------------------------------------------------------------------
# Fontes RSS
# ---------------------------------------------------------------------
FONTES_RSS = {
    "InfoMoney": "https://www.infomoney.com.br/feed/",
    "Money Times": "https://www.moneytimes.com.br/feed/",
    "Valor Investe": "https://valorinveste.globo.com/rss/valor-investe/",
    # Feeds públicos e gratuitos da Investing.com (não precisam de
    # cadastro/aprovação — são os RSS oficiais listados em
    # investing.com/webmaster-tools/rss). Cobrem Fed, geopolítica e
    # mercado dos EUA, que os feeds só-Brasil não trazem.
    "Investing.com Economia": "https://www.investing.com/rss/news_14.rss",
    "Investing.com Ações": "https://www.investing.com/rss/news_25.rss",
}

# Termos que tornam uma manchete relevante pro WIN/Ibovespa
# (português dos feeds BR + equivalentes em inglês da Investing.com)
PALAVRAS_CHAVE = [
    "ibovespa", "bovespa", "selic", "copom", "banco central", " bc ",
    "dólar", "cambio", "câmbio", "fed", "federal reserve", "juros",
    "inflação", "inflacao", "ipca", "pib", "b3",
    "mini índice", "mini indice", "índice futuro", "indice futuro",
    "inflation", "interest rate", "rate hike", "rate cut",
    "recession", "treasury", "tariff", "gdp",
]

INTERVALO_BUSCA_SEGUNDOS = 60       # busca nova a cada 1 min
JANELA_RELEVANCIA_MINUTOS = 15      # so considera "quente" o que saiu ha ate 15 min -
                                     # evita a "rajada de atraso" ao ligar o robo,
                                     # narrando tudo que saiu nas ultimas horas de uma vez
LIMITE_MANCHETES_POR_FONTE = 15     # quantas entradas do feed olhar por vez

RETENCAO_LIDAS_HORAS = 48           # por quanto tempo uma manchete "ja lida" continua
                                     # bloqueada, mesmo apos reiniciar o script - evita
                                     # que reiniciar o robo faca tudo parecer novo de novo
CAMINHO_MANCHETES_LIDAS = Path(__file__).parent / "logs" / "noticias_lidas.json"

# Fontes cujas manchetes saem em inglês — só essas passam pelo tradutor
FONTES_EM_INGLES = {"Investing.com Economia", "Investing.com Ações"}


_aviso_erro_traducao_mostrado = False
_ultima_traducao = 0.0
_INTERVALO_MIN_TRADUCAO = 1.0  # segundos entre chamadas


def traduzir_se_necessario(fonte: str, titulo: str) -> str:
    """Traduz pra português só as manchetes de fontes em inglês.
    Tenta o Google primeiro; se ele falhar (rate limit, bloqueio de
    IP, fora do ar), cai pro MyMemory — outro serviço gratuito, com
    limite independente do Google. Se os dois falharem, ou o
    deep-translator não estiver instalado, devolve o título original
    sem quebrar o resto do script."""
    global _aviso_erro_traducao_mostrado, _ultima_traducao
    if fonte not in FONTES_EM_INGLES or not _TRADUTOR_DISPONIVEL:
        return titulo

    espera = _INTERVALO_MIN_TRADUCAO - (time.monotonic() - _ultima_traducao)
    if espera > 0:
        time.sleep(espera)
    _ultima_traducao = time.monotonic()

    try:
        traduzido = GoogleTranslator(source="en", target="pt").translate(titulo)
        if traduzido:
            return traduzido
    except Exception:
        pass  # cai pro MyMemory abaixo

    try:
        traduzido = MyMemoryTranslator(source="en-GB", target="pt-BR").translate(titulo)
        if traduzido:
            return traduzido
    except Exception as erro:
        if not _aviso_erro_traducao_mostrado:
            print(f"{Fore.LIGHTBLACK_EX}[aviso] tradução falhou nos dois "
                  f"serviços ({type(erro).__name__}: {erro}) — mostrando "
                  f"original quando isso acontecer{Style.RESET_ALL}")
            _aviso_erro_traducao_mostrado = True

    return titulo

# Categorias pra colorir a exibição no terminal
CATEGORIAS = [
    ("JUROS/COPOM", ["selic", "copom", "banco central", " bc ",
                      "rate hike", "rate cut", "interest rate"], Fore.YELLOW),
    ("CÂMBIO/FED", ["dólar", "dolar", "câmbio", "cambio", "fed",
                     "federal reserve", "treasury"], Fore.CYAN),
    ("ÍNDICES/B3", ["ibovespa", "bovespa", "b3", "mini índice", "mini indice",
                     "índice futuro", "indice futuro"], Fore.GREEN),
    ("INFLAÇÃO/PIB", ["inflação", "inflacao", "ipca", "pib",
                       "inflation", "gdp", "recession"], Fore.RED),
]


def categorizar(titulo: str):
    t = titulo.lower()
    for nome, termos, cor in CATEGORIAS:
        if any(termo in t for termo in termos):
            return nome, cor
    return "MERCADO", Fore.WHITE


def imprimir(fonte: str, titulo: str):
    """
    Linha 1 (vermelha) - so contexto (categoria + fonte), NAO e falada.
    A manchete em si (linha 2, ciano) e responsabilidade de quem recebe o
    callback_narracao - normalmente o narrar() de principal.py, que ja
    imprime nessa cor e fala em voz alta.
    """
    categoria, _cor_categoria_nao_usada = categorizar(titulo)
    hora = datetime.now().strftime("%H:%M:%S")
    prefixo = f"{Fore.LIGHTBLACK_EX}[{hora}]{Style.RESET_ALL}"
    print(
        f"{prefixo} {Fore.RED}Notícia: {categoria:<13} {fonte}:{Style.RESET_ALL}"
    )


def _exibir_cyan_local(titulo: str):
    """Callback padrao usada so quando o script roda standalone (sem o
    narrar() de principal.py disponivel) - so exibe, nao fala de verdade."""
    hora = datetime.now().strftime("%H:%M:%S")
    prefixo = f"{Fore.LIGHTBLACK_EX}[{hora}]{Style.RESET_ALL}"
    print(f"{prefixo} {Fore.CYAN}Narrador: {titulo}{Style.RESET_ALL}")


# ---------------------------------------------------------------------
# Busca e filtragem
# ---------------------------------------------------------------------
class NoticiasMercado:
    """
    Busca notícias em background e chama callback_narracao(frase) para
    cada manchete nova e relevante encontrada. Falha silenciosamente
    em qualquer erro de rede/parsing — nunca deve derrubar o robô.
    """

    def __init__(self, callback_narracao=None):
        self.callback_narracao = callback_narracao
        self._manchetes_ja_narradas = {}  # chave (link/id) -> hora em que foi vista
                                           # (dict, nao set, para poder podar entradas
                                           # velhas e persistir com data)
        self.ultimas_manchetes = []  # histórico em memória: (fonte, titulo, hora)
        self._parar = threading.Event()
        self._pausado = threading.Event()
        self._thread = None
        self._carregar_lidas_do_disco()

    def _carregar_lidas_do_disco(self):
        """Recupera as manchetes ja vistas em execucoes anteriores, para que
        reiniciar o script NAO faca tudo parecer novo de novo. Poda entradas
        mais velhas que RETENCAO_LIDAS_HORAS na hora de carregar."""
        if not CAMINHO_MANCHETES_LIDAS.exists():
            print(f"{Fore.LIGHTBLACK_EX}[NOTICIAS] Nenhum historico de manchetes "
                  f"lidas encontrado ainda ({CAMINHO_MANCHETES_LIDAS}) - "
                  f"comecando do zero (normal na primeira execucao).{Style.RESET_ALL}")
            return
        try:
            with open(CAMINHO_MANCHETES_LIDAS, "r", encoding="utf-8") as f:
                dados = json.load(f)
            corte = datetime.now() - timedelta(hours=RETENCAO_LIDAS_HORAS)
            for chave, hora_iso in dados.items():
                try:
                    hora = datetime.fromisoformat(hora_iso)
                except ValueError:
                    continue
                if hora >= corte:
                    self._manchetes_ja_narradas[chave] = hora
            print(f"{Fore.LIGHTBLACK_EX}[NOTICIAS] {len(self._manchetes_ja_narradas)} "
                  f"manchete(s) ja lida(s) recuperada(s) de execucoes anteriores "
                  f"({CAMINHO_MANCHETES_LIDAS}).{Style.RESET_ALL}")
        except Exception as e:
            print(f"[NOTICIAS] AVISO: falha ao carregar manchetes ja lidas de "
                  f"{CAMINHO_MANCHETES_LIDAS}: {type(e).__name__}: {e} - "
                  f"comecando do zero.")

    def _salvar_lidas_no_disco(self):
        try:
            CAMINHO_MANCHETES_LIDAS.parent.mkdir(parents=True, exist_ok=True)
            dados = {chave: hora.isoformat() for chave, hora in self._manchetes_ja_narradas.items()}
            with open(CAMINHO_MANCHETES_LIDAS, "w", encoding="utf-8") as f:
                json.dump(dados, f)
        except Exception as e:
            print(f"[NOTICIAS] AVISO: falha ao salvar manchetes lidas em "
                  f"{CAMINHO_MANCHETES_LIDAS}: {type(e).__name__}: {e}")

    def _relevante(self, titulo: str) -> bool:
        titulo_lower = f" {titulo.lower()} "
        return any(p in titulo_lower for p in PALAVRAS_CHAVE)

    def _dentro_da_janela(self, entrada) -> bool:
        publicado = entrada.get("published_parsed")
        if not publicado:
            return True  # sem data confiável: não descarta, só não valida idade
        dt_pub = datetime(*publicado[:6])
        return datetime.now() - dt_pub <= timedelta(minutes=JANELA_RELEVANCIA_MINUTOS)

    def _apresentar(self, fonte: str, titulo: str):
        """Traduz (se necessario), exibe a linha de contexto (vermelha) e
        entrega o titulo para narracao."""
        titulo_exibicao = traduzir_se_necessario(fonte, titulo)
        self.ultimas_manchetes.append((fonte, titulo_exibicao, datetime.now()))

        imprimir(fonte, titulo_exibicao)  # linha vermelha, so contexto

        callback = self.callback_narracao or _exibir_cyan_local
        try:
            callback(titulo_exibicao)  # so o titulo - quem imprime/fala a linha
                                        # ciano e o callback (ex: narrar() de
                                        # principal.py)
        except Exception:
            pass

    def _buscar_uma_vez(self):
        """Verifica os feeds e apresenta na hora QUALQUER manchete nova,
        relevante e dentro da janela de frescor - sem represar. Noticias ja
        apresentadas antes (mesmo link/id) nunca voltam a aparecer."""
        for fonte, url in FONTES_RSS.items():
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue

            for entrada in feed.entries[:LIMITE_MANCHETES_POR_FONTE]:
                titulo = (entrada.get("title") or "").strip()
                if not titulo:
                    continue
                # chave de deduplicacao: link/id da materia, NAO o titulo -
                # sites como InfoMoney tem materias "ao vivo" que atualizam o
                # PROPRIO titulo varias vezes ao longo do dia (ex: "Bolsa
                # sobe..." vira "Bolsa fecha em alta..."), continuando na
                # mesma URL - usar o titulo como chave fazia essas variacoes
                # parecerem noticias novas, repetindo a mesma materia
                chave = entrada.get("id") or entrada.get("link") or titulo
                if chave in self._manchetes_ja_narradas:
                    continue
                if not self._relevante(titulo):
                    continue
                if not self._dentro_da_janela(entrada):
                    continue

                self._manchetes_ja_narradas[chave] = datetime.now()
                self._salvar_lidas_no_disco()  # persiste na hora, sobrevive a reinicio
                self._apresentar(fonte, titulo)

    def _loop(self):
        while not self._parar.is_set():
            if not self._pausado.is_set():
                self._buscar_uma_vez()
            self._parar.wait(INTERVALO_BUSCA_SEGUNDOS)

    def pausar(self):
        """Suspende buscas, exibição e narração sem encerrar a thread."""
        self._pausado.set()

    def retomar(self):
        """Reativa o monitoramento no pregão seguinte."""
        self._pausado.clear()

    def iniciar(self):
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self._parar.set()
        if self._thread:
            self._thread.join(timeout=2)


# ---------------------------------------------------------------------
# Execução standalone — lista as notícias direto no terminal
# ---------------------------------------------------------------------
def main():
    print(f"{Fore.LIGHTBLACK_EX}Painel de notícias no terminal — verifica a cada "
          f"1 min, mostra tudo que for novo — Ctrl+C pra parar{Style.RESET_ALL}")
    if _TRADUTOR_DISPONIVEL:
        print(f"{Fore.LIGHTBLACK_EX}Tradutor automático: ativo{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.LIGHTBLACK_EX}Tradutor automático: desativado — "
              f"rode 'pip install deep-translator' e reinicie{Style.RESET_ALL}\n")

    # standalone: usa o callback padrao (so exibe em ciano, nao fala de
    # verdade) - a linha vermelha de contexto ja e impressa internamente
    # por _apresentar(), nao precisa fazer de novo aqui
    modulo = NoticiasMercado(callback_narracao=None)
    modulo.iniciar()  # já faz a primeira busca assim que a thread sobe

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        modulo.parar()
        print(f"\n{Fore.LIGHTBLACK_EX}Painel encerrado.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
