#!/usr/bin/env python3
"""
SVG to PNG converter with CSS variable resolution and custom font support.
Usage: python3 svg_to_png.py <input.svg> [output.png] [--scale N]
"""

import argparse, re, sys
from pathlib import Path

# pip install cairosvg
import cairosvg


class SVG2PNG:
    # 使用するフォント名（システムにインストール済みであること）
    FONT_FAMILY = "HGPGothicE"

    # 置き換え対象のフォントファミリー文字列（SVG内に複数パターンある場合は追加）
    FONT_REPLACE_TARGETS: list[str] = [
        "'Noto Sans JP', 'Yu Gothic', 'Meiryo', sans-serif",
    ]

    # ============================================================
    # 処理関数
    # ============================================================

    def extract_css_variables(self, svg: str) -> dict[str, str]:
        """SVGの <style> タグ内の :root ブロックからCSS変数を抽出して辞書で返す。"""
        variables: dict[str, str] = {}

        # <style> ブロックを取得
        style_match = re.search(r"<style[^>]*>(.*?)</style>", svg, re.DOTALL)
        if not style_match:
            print("[INFO] <style>タグが見つかりませんでした。", file=sys.stderr)
            return variables

        style_content = style_match.group(1)

        # :root { ... } ブロックを取得
        root_match = re.search(r":root\s*\{([^}]*)\}", style_content, re.DOTALL)
        if not root_match:
            print("[INFO] :rootブロックが見つかりませんでした。", file=sys.stderr)
            return variables

        root_content = root_match.group(1)

        # --variable-name: value; を抽出
        for match in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", root_content):
            var_name = match.group(1).strip()
            value    = match.group(2).strip()
            variables[var_name] = value

        print(f"[INFO] CSS変数を{len(variables)}件抽出しました: {list(variables.keys())}")
        return variables


    def resolve_css_variables(
        self,
        svg: str, 
        variables: dict[str, str]
    ) -> str:
        """SVG内の var(--xxx) をすべて実際の値に置換する。"""
        for var_name, value in variables.items():
            svg = svg.replace(f"var({var_name})", value)

        # 置換できなかった var() が残っていれば警告
        remaining = re.findall(r"var\(--[\w-]+\)", svg)
        if remaining:
            unique = sorted(set(remaining))
            print(f"[WARNING] 未解決のCSS変数が残っています: {unique}", file=sys.stderr)

        return svg


    def replace_font_family(
        self,
        svg: str, 
        targets: list[str], 
        replacement: str
    ) -> str:
        """SVG内の font-family 属性を指定フォントに置換する。"""
        for target in targets:
            svg = svg.replace(target, replacement)
        return svg


    def convert(
        self,
        svg_path: str, 
        output_path: str, 
        scale: float = 2.0
    ) -> None:
        src = Path(svg_path)
        if not src.exists():
            print(f"[ERROR] ファイルが見つかりません: {svg_path}", file=sys.stderr)
            sys.exit(1)

        svg = src.read_text(encoding="utf-8")

        # <style>タグからCSS変数を自動抽出して解決
        css_vars = self.extract_css_variables(svg)
        svg = self.resolve_css_variables(svg, css_vars)

        # フォントを置換
        svg = self.replace_font_family(svg, self.FONT_REPLACE_TARGETS, self.FONT_FAMILY)

        # PNG に変換
        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            write_to=output_path,
            scale=scale,
        )
        print(f"[OK] 変換完了: {output_path}")


    # ============================================================
    # エントリポイント
    # ============================================================

    def __init__(self) -> None:
        parser = argparse.ArgumentParser(
            description="SVGをPNGに変換します（CSS変数・フォント置換つき）"
        )
        parser.add_argument("input", help="入力SVGファイルのパス")
        parser.add_argument(
            "output",
            nargs="?",
            help="出力PNGファイルのパス（省略時は入力と同名の.png）",
        )
        parser.add_argument(
            "--scale",
            type=float,
            default=2.0,
            help="出力解像度の倍率（デフォルト: 2.0）",
        )
        args = parser.parse_args()

        output = args.output or str(Path(args.input).with_suffix(".png"))
        self.convert(args.input, output, args.scale)


if __name__ == "__main__":
    SVG2PNG()
