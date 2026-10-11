#!/usr/bin/env python3

import re, json, serial, threading, time, platform
from serial.tools import list_ports
from typing import Optional


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def check_serial() -> list[str]:
    """利用可能なシリアルポートをリストで返す"""
    return [info.device for info in list_ports.comports()]


def formatted_prompt(message: str, default):
    """
    型に応じてインタラクティブな入力プロンプトを表示する。

    - str  : 空 Enter でデフォルト文字列を返す
    - bool : y/n 入力。空 Enter でデフォルトを返す
    - int  : 整数入力。不正値は再入力を求める
    """
    if isinstance(default, bool):
        default_str = "y" if default else "n"
        while True:
            raw = input(f"{message} [{default_str}] [y/n]: ").strip().lower()
            if not raw:
                return default
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            print(f"  [{raw}] は y/n ではありません")

    elif isinstance(default, int):
        while True:
            raw = input(f"{message} [{default}]: ").strip()
            if not raw:
                return default
            try:
                return int(raw)
            except ValueError:
                print(f"  [{raw}] は整数ではありません")

    else:  # str
        val = input(f"{message} [{default}]: ").strip()
        return val if val else default


# ---------------------------------------------------------------------------
# SendUARTData
# ---------------------------------------------------------------------------

class SendUARTData:
    """
    シリアルポートの送受信を管理するクラス。

    | Parameters | detail |
    | ---------- | ------ |
    | port       | COM ポート名 (例: "COM4", "/dev/ttyUSB0") |
    | baudrate   | ボーレート |
    | timeout    | 受信タイムアウト [秒] |
    | dtrReset   | True で起動時に DTR パルスリセットを行う |
    | encoding   | 文字列エンコーディング。None or "" でバイト列モード |
    | lineEnd    | 行末文字 (rx_uart_data_ln の読み取り終端) |
    """

    def __init__(
        self,
        port: str      = "COM4",
        baudrate: int  = 115200,
        timeout: float = 0.1,
        dtrReset: bool = False,
        encoding: str  = "UTF-8",
        lineEnd: str   = "\n",
    ):
        self.encoding = encoding.strip() if encoding.strip() else None
        self.lineEnd  = lineEnd

        self.serialPort = serial.Serial(
            port     = port,
            baudrate = baudrate,
            timeout  = timeout,
        )

        if dtrReset:
            self.reset_dtr()

    # ------------------------------------------------------------------
    # コンテキストマネージャ
    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """ポートを安全にクローズする"""
        if self.serialPort and self.serialPort.is_open:
            self.serialPort.close()

    # ------------------------------------------------------------------
    # 内部ヘルパー (エンコード・デコード)
    # ------------------------------------------------------------------

    def encode(self, tx: str) -> bytes:
        if self.encoding is None:
            cleaned = re.sub(r"0x|0X|\s", "", tx)
            if len(cleaned) % 2 != 0:
                raise ValueError(f"奇数桁の16進数文字列です: {tx!r}")
            return bytes.fromhex(cleaned)
        else:
            return tx.encode(self.encoding)

    def decode(self, rx: bytes) -> str:
        if self.encoding is None:
            return " ".join(f"{b:02X}" for b in rx)
        else:
            return rx.decode(self.encoding, errors="replace")

    # ------------------------------------------------------------------
    # 送信
    # ------------------------------------------------------------------

    def tx_uart_data(self, data: str) -> None:
        self.serialPort.write(self.encode(data))

    def tx_uart_cmd(self, data: str) -> None:
        self.serialPort.write(self.encode(f"{data}{self.lineEnd}"))

    # ------------------------------------------------------------------
    # 受信
    # ------------------------------------------------------------------

    def rx_uart_data(self, size: int = 0) -> str:
        """
        シリアルから受信する。
        size : 読み取りバイト数。0 のときは in_waiting 分をすべて読む
        """
        n = size if size > 0 else self.serialPort.in_waiting
        if n == 0:
            return ""
        return self.decode(self.serialPort.read(n))

    def rx_uart_data_ln(self) -> str:
        """lineEnd が現れるまで 1 バイトずつ読み込み、1 行分を返す"""
        line_end_bytes = self.lineEnd.encode()

        buf = bytearray()
        while True:
            b = self.serialPort.read(1)
            if not b:   # タイムアウト
                continue
            buf += b
            if buf.endswith(line_end_bytes):
                break

        return self.decode(bytes(buf))

    # ------------------------------------------------------------------
    # 制御
    # ------------------------------------------------------------------

    def flush(self) -> None:
        """送受信バッファをクリアする"""
        self.serialPort.reset_input_buffer()
        self.serialPort.reset_output_buffer()
        self.serialPort.flush()

    def reset_dtr(self, pulse_sec: float = 0.1) -> None:
        """DTR をパルスさせてターゲットをリセットする"""
        self.serialPort.dtr = True
        time.sleep(pulse_sec)
        self.serialPort.dtr = False



class Pyterm:
    def __init__(self, interval: float = 0.0001, CONFIG_PATH = "config/COM.json"):
        self.newline        = "\n"
        self.interval       = interval
        self.last_rx        = ""
        self._stop_flag     = False
        self._rx_thread: Optional[threading.Thread] = None
        self.CONFIG_PATH    = CONFIG_PATH
        try:
            with open(self.CONFIG_PATH, encoding="UTF-8") as f:
                self.port_config = json.load(f)
        except Exception as e:
            print(e)
            self.port_config = {}


    def _rx_loop(self, uart: SendUARTData) -> None:
        try:
            while not self._stop_flag:
                print(uart.rx_uart_data_ln().replace("\r", "").replace("\n", ""))
                time.sleep(self.interval)
        except Exception as e:
            print(f"[rx_loop] エラー: {e}")

    def start(self, uart: SendUARTData) -> None:
        """受信スレッドを起動する"""
        self._stop_flag = False
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            args=(uart,),
            daemon=True,
        )
        self._rx_thread.start()

    def stop(self) -> None:
        """受信スレッドを停止する"""
        self._stop_flag = True


    def serial_check(self):
        serial_list = check_serial()
        if not serial_list:
            print("利用可能なシリアルポートが見つかりません")
        else:
            print("\n─── 利用可能なポート ───")
            for sp in serial_list:
                label = self.port_config.get(sp, {}).get("device", "未登録デバイス")
                print(f"{sp} : {label}")
        print()

    def setup_config(self):
        """ポート選択から送受信までのメインループ"""
        os_name         = platform.system()
        if os_name == "Windows":
            raw_port    = formatted_prompt("COMポート番号 (0未満で終了)", 8)
            if raw_port < 0:
                print("終了します")
                input()
                return None
            port        = f"COM{raw_port}"
        else:
            port        = formatted_prompt("ポート番号", "/dev/ttyUSB0")
            
        baudrate        = formatted_prompt("baudrate",       115200)
        dtrReset        = formatted_prompt("起動時DTRリセット?", False)
        newline         = formatted_prompt("改行コード : [CRLF/LF/CR]", "LF")
        enc_raw         = formatted_prompt("encoding (Space + Enter でバイト列モード)", "UTF-8")
        encoding        = enc_raw if enc_raw else ""
        if newline.lower() == "crlf":
            self.newline  = "\r\n"
        elif newline.lower() == "cr":
            self.newline  = "\r"
        else:
            self.newline = "\n"
        print(f"\n  接続先 : {port}  baudrate={baudrate}  dtrReset={dtrReset}")
        print(f"  encoding: {encoding or 'bytes mode'}  改行コード={newline.lower()}")
        print("  送信 : テキストを入力して Enter  / Ctrl+C で切断\n")

        return {
            "port" : port,
            "baudrate" : baudrate,
            "dtrReset" : dtrReset,
            "encoding" : encoding,
            "lineEnd" : self.newline
        }

if __name__ == "__main__":
    pyterm = Pyterm()
    while True:
        pyterm.serial_check()
        config = pyterm.setup_config()
        if config is not None:
            try:
                with SendUARTData(
                    port     = config["port"],
                    baudrate = config["baudrate"],
                    timeout  = 0.1,
                    dtrReset = config["dtrReset"],
                    encoding = config["encoding"],
                    lineEnd  = config["lineEnd"]
                ) as uart:
                    time.sleep(0.5)
                    pyterm.start(uart)
                    while True:
                        try:
                            uart.tx_uart_cmd(input())
                        except KeyboardInterrupt:
                            print("\n[切断]")
                            break
                        except Exception as e:
                            print(e)
            except serial.SerialException as e:
                print(f"[エラー] シリアルポートを開けませんでした: {e}")
            finally:
                pyterm.stop()
                time.sleep(0.05)
        else:
            break
