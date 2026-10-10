"""ponte_radar.py - V554. Transmissor do radar: leva o estado do robo (radar/radar_estado.js) ate o servidor.

Roda como PROCESSO SEPARADO, no mesmo computador do robo (`python ponte_radar.py`). Nao e o robo, nao e
estrategia e nao recebe comando algum: so le o arquivo de estado e envia, em mao unica, para o servidor.

Salvaguardas (ata AM/AN do conselho):
  - le o arquivo como TEXTO e interpreta como JSON; nunca executa o JavaScript do arquivo;
  - valida tamanho, tipos e numeros finitos, e remonta o estado campo a campo (so passa o que esta na lista
    de campos permitidos: nada de nomes de estrategia, condicoes, limites, preco de entrada ou stop);
  - so envia atualizacao genuina (arquivo congelado nao e reenviado; o servidor mede a idade pelo relogio dele);
  - sem fila: depois de uma falha envia apenas o estado mais recente; tentativas com espera progressiva;
  - identificador de sessao proprio a cada partida da ponte e contador de envio crescente, para o servidor
    ignorar pedido antigo e entender reinicios;
  - canal pelo modo do robo: modo "replay" vai para o canal replay, modo "normal" vai SO para o canal ao vivo
    (nunca vira publicacao publica); cada canal tem a sua chave de publicacao;
  - as chaves ficam em variavel de ambiente ou em ponte_radar.privado.json (fora do Git), nunca vao ao
    navegador nem aos logs.

Configuracao (variaveis de ambiente ou ponte_radar.privado.json com as mesmas chaves em minusculas):
  RADAR_URL            endereco do servidor, https:// (http so para 127.0.0.1/localhost, em teste)
  RADAR_CHAVE_VIVO     chave de publicacao do canal ao vivo
  RADAR_CHAVE_REPLAY   chave de publicacao do canal replay
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Callable, Optional

RAIZ = Path(__file__).resolve().parent
CAMINHO_ESTADO_PADRAO = RAIZ / "radar" / "radar_estado.js"
CAMINHO_CONFIG_PRIVADA = RAIZ / "ponte_radar.privado.json"

TAMANHO_MAXIMO_BYTES = 20_000
PREFIXO = "window.RADAR_ESTADO ="
INTERVALO_MINIMO_ENVIO_S = 2.0      # escolha inicial de engenharia, a medir
TIMEOUT_ENVIO_S = 5.0
ESPERA_MAXIMA_FALHA_S = 30.0
CANAL_POR_MODO = {"normal": "vivo", "replay": "replay"}

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
_TEXTO_CURTO = re.compile(r"^[A-Za-z0-9._ -]{1,16}$")


class ErroEstado(ValueError):
    """Arquivo de estado ausente de forma esperada, fora do formato ou com valores invalidos."""


# ---------------------------------------------------------------- leitura e validacao
def _inteiro(valor, nome, minimo, maximo):
    if isinstance(valor, bool) or not isinstance(valor, int) or not (minimo <= valor <= maximo):
        raise ErroEstado(f"campo {nome} invalido")
    return valor


def _decimal(valor, nome, minimo=None, maximo=None):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ErroEstado(f"campo {nome} invalido")
    valor = float(valor)
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        raise ErroEstado(f"campo {nome} fora da faixa")
    return valor


def _lado(valor, nome):
    if isinstance(valor, bool) or valor not in (-1, 0, 1):
        raise ErroEstado(f"campo {nome} invalido")
    return int(valor)


def validar_estado(bruto) -> dict:
    """Remonta o estado so com os campos permitidos. Qualquer outro campo e descartado."""
    if not isinstance(bruto, dict):
        raise ErroEstado("estado nao e um objeto")
    modo = bruto.get("modo")
    if modo not in CANAL_POR_MODO:
        raise ErroEstado("campo modo invalido")
    versao = bruto.get("versao")
    if versao is not None and (not isinstance(versao, str) or not _TEXTO_CURTO.match(versao)):
        raise ErroEstado("campo versao invalido")
    if not isinstance(bruto.get("radar_envia_ordens"), bool):
        raise ErroEstado("campo radar_envia_ordens invalido")
    lista = bruto.get("estrategias")
    if not isinstance(lista, list) or len(lista) > 32:
        raise ErroEstado("campo estrategias invalido")
    estrategias = []
    for item in lista:
        if not isinstance(item, dict):
            raise ErroEstado("item de estrategias invalido")
        estrategias.append({
            "id": _inteiro(item.get("id"), "id", 0, 999),
            "dir": _lado(item.get("dir"), "dir"),
            "conf": _decimal(item.get("conf"), "conf", 0.0, 1.0),
        })
    posicao = bruto.get("posicao")
    captura = bruto.get("captura")
    if not isinstance(captura, dict):
        raise ErroEstado("campo captura invalido")
    mercado = bruto.get("mercado")
    mercado_ok = None
    if mercado is not None:
        if not isinstance(mercado, dict):
            raise ErroEstado("campo mercado invalido")
        ativo = mercado.get("ativo")
        horario = mercado.get("horario")
        preco = mercado.get("preco")
        if not isinstance(ativo, str) or len(ativo) > 16 or not re.match(r"^[A-Za-z0-9._ -]*$", ativo):
            raise ErroEstado("campo mercado.ativo invalido")
        if horario is not None and (not isinstance(horario, str) or not _ISO.match(horario)):
            raise ErroEstado("campo mercado.horario invalido")
        mercado_ok = {
            "ativo": ativo,
            "horario": horario,
            "preco": None if preco is None else _decimal(preco, "mercado.preco"),
            "timeframe_min": _inteiro(mercado.get("timeframe_min"), "mercado.timeframe_min", 1, 1440),
        }
    return {
        "n": _inteiro(bruto.get("n"), "n", 0, 2**53),
        "versao": versao,
        "modo": modo,
        "radar_envia_ordens": bruto["radar_envia_ordens"],
        "estrategias": estrategias,
        "consenso": _decimal(bruto.get("consenso"), "consenso", 0.0, 1.0),
        "posicao": None if posicao is None else _lado(posicao, "posicao"),
        "captura": {
            "seq": _inteiro(captura.get("seq"), "captura.seq", 0, 2**53),
            "dir": _lado(captura.get("dir"), "captura.dir"),
        },
        "mercado": mercado_ok,
    }


def _recusa_constante(nome):
    raise ErroEstado("numero nao finito no arquivo")


def interpretar_texto(texto: str) -> dict:
    """`window.RADAR_ESTADO = {...};` -> estado validado. Nunca executa o texto."""
    texto = texto.strip()
    if not texto.startswith(PREFIXO) or not texto.endswith(";"):
        raise ErroEstado("formato do arquivo nao reconhecido")
    corpo = texto[len(PREFIXO):-1].strip()
    try:
        bruto = json.loads(corpo, parse_constant=_recusa_constante)
    except ErroEstado:
        raise
    except ValueError:
        raise ErroEstado("conteudo nao e JSON valido")
    return validar_estado(bruto)


def ler_estado(caminho) -> dict:
    """Le o arquivo (FileNotFoundError se ainda nao existe) e devolve o estado validado."""
    caminho = Path(caminho)
    tamanho = caminho.stat().st_size
    if tamanho > TAMANHO_MAXIMO_BYTES:
        raise ErroEstado("arquivo maior que o permitido")
    try:
        texto = caminho.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise ErroEstado("arquivo nao esta em UTF-8")
    return interpretar_texto(texto)


# ---------------------------------------------------------------- configuracao e envio
def destino_valido(url: str) -> bool:
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if p.scheme == "https" and p.hostname:
        return True
    return p.scheme == "http" and p.hostname in ("127.0.0.1", "localhost")


def carregar_configuracao(env=None, caminho_privado: Optional[Path] = None) -> dict:
    env = os.environ if env is None else env
    privado = {}
    caminho_privado = CAMINHO_CONFIG_PRIVADA if caminho_privado is None else Path(caminho_privado)
    if caminho_privado.exists():
        try:
            privado = json.loads(caminho_privado.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            privado = {}
    if not isinstance(privado, dict):
        privado = {}

    def pega(nome):
        valor = env.get(nome.upper()) or privado.get(nome.lower())
        return valor.strip() if isinstance(valor, str) and valor.strip() else None

    return {
        "url": pega("RADAR_URL"),
        "chaves": {"vivo": pega("RADAR_CHAVE_VIVO"), "replay": pega("RADAR_CHAVE_REPLAY")},
    }


def enviar_http(url: str, chave: str, corpo: bytes, timeout: float) -> int:
    """POST autenticado. Devolve o status HTTP; levanta excecao em falha de rede ou status de erro."""
    req = urllib.request.Request(
        url, data=corpo, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + chave,
                 "User-Agent": "robonildo-ponte-radar"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


class Ponte:
    """Um passo = ler o arquivo e, se houver atualizacao genuina, enviar. Sem threads, sem fila."""

    def __init__(self, caminho, url: str, chaves: dict,
                 enviar: Callable = enviar_http, relogio: Callable = time.monotonic,
                 intervalo_min_s: float = INTERVALO_MINIMO_ENVIO_S, timeout_s: float = TIMEOUT_ENVIO_S,
                 log: Callable = print):
        if not destino_valido(url):
            raise ValueError("RADAR_URL precisa ser https:// (http so para 127.0.0.1 ou localhost)")
        self.caminho = Path(caminho)
        self.url = url.rstrip("/")
        self._chaves = dict(chaves)
        self._enviar = enviar
        self._relogio = relogio
        self.intervalo_min_s = intervalo_min_s
        self.timeout_s = timeout_s
        self._log = log
        self.sessao = uuid.uuid4().hex
        self.geracao = 0
        self._seq = 0
        self._ultimo_visto_n: Optional[int] = None
        self._enviado = None                 # (n, modo) do ultimo envio com sucesso
        self._captura_enviada: Optional[int] = None
        self._ultimo_envio_ok: Optional[float] = None
        self._falhas = 0
        self._proxima_tentativa = 0.0
        self._conectado: Optional[bool] = None
        self._aviso_atual = None

    def _avisar(self, chave: str, texto: str):
        if self._aviso_atual != chave:
            self._aviso_atual = chave
            self._log(f"[PONTE] {texto}")

    def passo(self) -> bool:
        """True se enviou uma atualizacao com sucesso neste passo."""
        agora = self._relogio()
        if agora < self._proxima_tentativa:
            return False
        try:
            estado = ler_estado(self.caminho)
        except FileNotFoundError:
            self._avisar("arquivo", "aguardando o arquivo de estado do robo")
            return False
        except (ErroEstado, OSError) as erro:
            self._avisar("invalido:" + str(erro), f"estado ignorado ({erro})")
            return False
        if self._aviso_atual is not None and self._aviso_atual != "ok":
            self._aviso_atual = "ok"

        if self._ultimo_visto_n is not None and estado["n"] < self._ultimo_visto_n:
            self.geracao += 1                 # o robo reiniciou: contador n voltou
        self._ultimo_visto_n = estado["n"]

        if (estado["n"], estado["modo"]) == self._enviado:
            return False                      # arquivo congelado: nao e atualizacao nova
        capturou = estado["captura"]["seq"] != self._captura_enviada and self._captura_enviada is not None
        if (self._ultimo_envio_ok is not None and not capturou
                and agora - self._ultimo_envio_ok < self.intervalo_min_s):
            return False

        canal = CANAL_POR_MODO[estado["modo"]]
        chave = self._chaves.get(canal)
        if not chave:
            self._avisar("sem-chave:" + canal, f"sem chave de publicacao para o canal {canal}: nada enviado")
            return False

        self._seq += 1
        corpo = json.dumps({"sessao": self.sessao, "geracao": self.geracao, "seq": self._seq,
                            "estado": estado}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        try:
            status = self._enviar(f"{self.url}/publicar/{canal}", chave, corpo, self.timeout_s)
            if not (200 <= int(status) < 300):
                raise RuntimeError(f"HTTP {status}")
        except urllib.error.HTTPError as erro:
            self._falha(f"servidor recusou (HTTP {erro.code})", agora)
            return False
        except Exception as erro:             # rede, timeout, DNS...: so o nome do erro, nunca cabecalhos
            self._falha(f"sem conexao com o servidor ({type(erro).__name__})", agora)
            return False

        if self._conectado is not True:
            self._log("[PONTE] conectado ao servidor" if self._conectado is None else "[PONTE] conexao recuperada")
        self._conectado = True
        self._falhas = 0
        self._enviado = (estado["n"], estado["modo"])
        self._captura_enviada = estado["captura"]["seq"]
        self._ultimo_envio_ok = agora
        return True

    def _falha(self, texto: str, agora: float):
        self._falhas += 1
        espera = min(ESPERA_MAXIMA_FALHA_S, 2.0 ** self._falhas)
        self._proxima_tentativa = agora + espera
        if self._conectado is not False:
            self._log(f"[PONTE] {texto}; tentando de novo (espera progressiva)")
        self._conectado = False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Transmissor do radar do ROBONILDO (processo separado do robo).")
    ap.add_argument("--arquivo", default=str(CAMINHO_ESTADO_PADRAO), help="radar_estado.js do robo")
    ap.add_argument("--verificar-a-cada", type=float, default=0.5, help="segundos entre leituras do arquivo")
    args = ap.parse_args(argv)
    cfg = carregar_configuracao()
    if not cfg["url"]:
        print("[PONTE] defina RADAR_URL (variavel de ambiente ou ponte_radar.privado.json).")
        return 2
    if not any(cfg["chaves"].values()):
        print("[PONTE] defina RADAR_CHAVE_VIVO e/ou RADAR_CHAVE_REPLAY.")
        return 2
    try:
        ponte = Ponte(args.arquivo, cfg["url"], cfg["chaves"])
    except ValueError as erro:
        print(f"[PONTE] {erro}")
        return 2
    print(f"[PONTE] sessao {ponte.sessao[:8]} | lendo {args.arquivo} | destino {ponte.url}")
    try:
        while True:
            ponte.passo()
            time.sleep(args.verificar_a_cada)
    except KeyboardInterrupt:
        print("[PONTE] encerrada.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
