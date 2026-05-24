#!/usr/bin/env python3

# pip install cairosvg
import cairosvg
import re, sys, os

class SVG2PNG:
    FONT_REPLACE_TARGETS: list[str] = [
        "'HGPGothicE', 'Noto Sans JP', 'Yu Gothic', 'Meiryo', sans-serif",
    ]

    # 使用するフォント名（システムにインストール済みであること）
    FONT_FAMILY = "HGPGothicE"

    def set_font(self, font = "HGPGothicE"):
        self.FONT_FAMILY = font
    
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

    # ============================================================
    # エントリポイント
    # ============================================================

    def __init__(
        self,
        svgPath: str, 
        outputPath: str, 
        scale: float = 2.0
    ):
        if not os.path.exists(svgPath):
            print(f"[ERROR] ファイルが見つかりません: {svgPath}", file=sys.stderr)
            sys.exit(1)

        
        with open(svgPath, "r", encoding="utf-8") as f:
            svg = f.read()

        # <style>タグからCSS変数を自動抽出して解決
        css_vars    = self.extract_css_variables(svg)
        svg         = self.resolve_css_variables(svg, css_vars)

        # フォントを置換
        svg         = self.replace_font_family(svg, self.FONT_REPLACE_TARGETS, self.FONT_FAMILY)

        # PNG に変換
        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            write_to=outputPath,
            scale=scale,
        )
        print(f"[OK] 変換完了: {outputPath}")

if __name__ == "__main__":
    svgPath    = input("SVGファイルパス : ")
    defaultOut = os.path.splitext(svgPath)[0] + ".png"
    outPath    = input(f"出力ファイルパス (デフォルト : {defaultOut}) : ").strip() or defaultOut
    scaleInput = input("倍率 (デフォルト : 2.0) : ").strip()
    try:
        scale = float(scaleInput) if scaleInput else 2.0
    except ValueError:
        print("[WARNING] 倍率の値が不正なため、デフォルト値 2.0 を使用します。", file=sys.stderr)
        scale = 2.0
    SVG2PNG(svgPath, outPath, scale)