#!/usr/bin/env python3

import argparse
import sys
import cv2
import numpy as np
from pathlib import Path


class ARGConfig:
    HELP_TEXT = """
png_to_svg.py  ―  白背景PNG → SVG アウトライン変換スクリプト

出力SVGにはCSS変数が埋め込まれます。色を変えたいときは
SVGファイルの <style> セクションの変数値を書き換えるだけです。

    :root {
      --fill-1: black;    /* 輪郭1の塗り色  */
      --stroke-1: none;   /* 輪郭1の線の色  */
      --fill-2: none;     /* 輪郭2の塗り色  */
      --stroke-2: black;  /* 輪郭2の線の色  */
      /* ... */
    }

使い方:
    python png_to_svg.py input.png output.svg [オプション]

オプション:
    --threshold  INT   二値化の閾値 (0-255, デフォルト: 240)
                       ※ 高いほど「白に近い色も白と見なす」
    --smooth     INT   輪郭の平滑化強度 (デフォルト: 2, 0=なし)
    --stroke     STR   全輪郭の線の色のデフォルト (デフォルト: "black")
    --fill       STR   全輪郭の塗り色のデフォルト (デフォルト: "none")
    --width      INT   SVGの幅(px)。省略時は元画像の幅
    --min-area   INT   無視する輪郭の最小面積(px²) (デフォルト: 50)

例:
    # 輪郭だけ（塗りなし）→ CSS変数で後から自由に色付け
    python png_to_svg.py logo.png logo.svg

    # デフォルトの塗りを黒にして出力
    python png_to_svg.py logo.png logo.svg --fill black --stroke none

    # 細かいノイズを除去して変換
    python png_to_svg.py logo.png logo.svg --min-area 200 --smooth 3
"""
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="白背景PNGをCSS変数付きSVGに変換します",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self.HELP_TEXT,
        )
        parser.add_argument(
            "input",
            nargs="?",
            default=None,
            help="入力PNGファイル"
        )
        parser.add_argument(
            "output",
            nargs="?",
            default=None,
            help="出力SVGファイル (省略時は入力ファイル名の拡張子を .svg に変更)"
        )
        parser.add_argument(
            "--threshold",  
            type=int, default=240,
            help="二値化閾値 0-255 (デフォルト: 240)"
        )
        parser.add_argument(
            "--smooth",
            type=int, default=2,
            help="平滑化強度 (デフォルト: 2)"
        )
        parser.add_argument(
            "--stroke",
            default="black",
            help="線の色のデフォルト (デフォルト: black)"
        )
        parser.add_argument(
            "--fill",
            default="none",
            help="塗り色のデフォルト (デフォルト: none)"
        )
        parser.add_argument(
            "--width",
            type=int, default=None,
            help="SVGの出力幅px (省略時は元画像サイズ)"
        )
        parser.add_argument(
            "--min-area",
            type=int, default=50,
            help="無視する最小面積px² (デフォルト: 50)"
        )

        args                = parser.parse_args()
        self.inputPath      = args.input
        self.outputPath     = args.output
        self.threshold      = args.threshold
        self.smooth         = args.smooth
        self.defaultStroke  = args.stroke
        self.defaultFill    = args.fill
        self.svgWidth       = args.width
        self.minArea        = args.min_area


class PNG2SVG:
    """PNGをSVGアウトラインに変換するクラス。"""

    def __init__(self, inputPath, threshold, smooth, defaultStroke, defaultFill, svgWidth, minArea):
        self.inputPath      = inputPath
        self.threshold      = threshold
        self.smooth         = smooth
        self.defaultStroke  = defaultStroke
        self.defaultFill    = defaultFill
        self.svgWidth       = svgWidth
        self.minArea        = minArea
        self.svg_content    = None   # convert() 後に格納される
        self.out_w          = None
        self.out_h          = None
        self.path_count     = None

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _load_image(self) -> np.ndarray:
        """画像を読み込み、アルファ合成して3chのBGR配列を返す。"""
        img = cv2.imread(self.inputPath, cv2.IMREAD_UNCHANGED)
        if img is None:
            sys.exit(f"[エラー] 画像を読み込めませんでした: {self.inputPath}")

        if img.shape[2] == 4:
            alpha    = img[:, :, 3]
            rgb      = img[:, :, :3]
            white_bg = np.ones_like(rgb) * 255
            mask     = alpha[:, :, np.newaxis] / 255.0
            img      = (rgb * mask + white_bg * (1 - mask)).astype(np.uint8)
        else:
            img = img[:, :, :3]

        return img

    def _binarize(self, img: np.ndarray) -> np.ndarray:
        """グレースケール変換 → 二値化 → ノイズ除去を行い、二値画像を返す。"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(
            gray, self.threshold, 255, cv2.THRESH_BINARY_INV
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return binary

    def _contour_to_svg_path(self, contour, smooth: int) -> str:
        """OpenCV輪郭点列 → SVG path d属性文字列（Catmull-Romスプライン近似）"""
        pts = contour.reshape(-1, 2)
        n   = len(pts)
        if n < 3:
            return ""

        if smooth > 0:
            k      = smooth * 2 + 1
            kernel = np.ones(k) / k
            px     = np.pad(pts[:, 0].astype(float), k // 2, mode='wrap')
            py     = np.pad(pts[:, 1].astype(float), k // 2, mode='wrap')
            xs     = np.convolve(px, kernel, mode='valid')
            ys     = np.convolve(py, kernel, mode='valid')
            pts    = np.stack([xs, ys], axis=1)

        step = max(1, n // 300)
        pts  = pts[::step]
        n    = len(pts)

        d_parts = [f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"]
        for i in range(n):
            p0 = pts[(i - 1) % n]
            p1 = pts[i]
            p2 = pts[(i + 1) % n]
            p3 = pts[(i + 2) % n]
            cp1x = p1[0] + (p2[0] - p0[0]) / 6
            cp1y = p1[1] + (p2[1] - p0[1]) / 6
            cp2x = p2[0] - (p3[0] - p1[0]) / 6
            cp2y = p2[1] - (p3[1] - p1[1]) / 6
            d_parts.append(
                f"C {cp1x:.2f},{cp1y:.2f} {cp2x:.2f},{cp2y:.2f} {p2[0]:.2f},{p2[1]:.2f}"
            )
        d_parts.append("Z")
        return " ".join(d_parts)

    def _collect_paths(self, binary: np.ndarray, scale: float) -> list[tuple]:
        """輪郭を検出してSVGパスエントリのリストを返す。"""
        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE
        )
        if not contours:
            sys.exit("[警告] 輪郭が検出されませんでした。--threshold を下げてみてください。")

        print(f"[情報] 検出した輪郭数: {len(contours)}")

        path_entries = []
        skipped      = 0
        for cnt, hier in zip(contours, hierarchy[0]):
            area = cv2.contourArea(cnt)
            if area < self.minArea:
                skipped += 1
                continue
            path_d = self._contour_to_svg_path(cnt, self.smooth)
            if not path_d:
                continue
            is_hole = hier[3] != -1
            path_entries.append((area, path_d, is_hole))

        path_entries.sort(key=lambda x: x[0], reverse=True)
        print(f"[情報] 変換したパス数: {len(path_entries)}  スキップ(小さすぎ): {skipped}")
        return path_entries

    def _build_css(self, path_entries: list[tuple]) -> str:
        """CSS変数ブロック文字列を生成して返す。"""
        lines = ["  :root {"]
        for idx, (area, _, is_hole) in enumerate(path_entries, start=1):
            label = "穴(内側)" if is_hole else f"面積:{int(area)}px²"
            f_val = "none" if is_hole else self.defaultFill
            s_val = self.defaultStroke
            lines.append(f"    --fill-{idx}:   {f_val};   /* 輪郭{idx} 塗り色  ({label}) */")
            lines.append(f"    --stroke-{idx}: {s_val};   /* 輪郭{idx} 線の色  ({label}) */")
        lines.append("  }")
        return "\n".join(lines)

    def _build_svg(self, path_entries: list[tuple], out_w: int, out_h: int, scale: float) -> str:
        """SVG全体の文字列を生成して返す。"""
        css_block      = self._build_css(path_entries)
        transform_attr = f' transform="scale({scale:.6f})"' if scale != 1.0 else ""
        stroke_width   = f"{1 / scale:.2f}"

        svg_paths = []
        for idx, (_, path_d, _) in enumerate(path_entries, start=1):
            svg_paths.append(
                f'  <path id="path-{idx}" d="{path_d}"\n'
                f'        fill="var(--fill-{idx})"\n'
                f'        stroke="var(--stroke-{idx})"\n'
                f'        stroke-width="{stroke_width}"\n'
                f'        fill-rule="evenodd"{transform_attr}/>'
            )

        return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{out_w}" height="{out_h}"
     viewBox="0 0 {out_w} {out_h}">

  <!--
    色を変えるには下の <style> 内の変数値を書き換えてください。
    使える色の書き方例:
      black  /  white  /  none  /  red
      #ff0000  /  rgb(255,0,0)  /  rgba(255,0,0,0.5)
  -->
  <style>
{css_block}
  </style>

  <!-- 白背景 -->
  <rect width="100%" height="100%" fill="white"/>

{chr(10).join(svg_paths)}
</svg>
"""

    # ------------------------------------------------------------------
    # 公開メソッド
    # ------------------------------------------------------------------

    def convert(self) -> str:
        """変換を実行し、SVG文字列を返す（ファイルには書き込まない）。"""
        img    = self._load_image()
        h, w   = img.shape[:2]
        binary = self._binarize(img)

        scale        = (self.svgWidth / w) if self.svgWidth and self.svgWidth != w else 1.0
        self.out_w   = int(w * scale)
        self.out_h   = int(h * scale)

        path_entries    = self._collect_paths(binary, scale)
        self.path_count = len(path_entries)
        self.svg_content = self._build_svg(path_entries, self.out_w, self.out_h, scale)
        return self.svg_content

    def output(self, outputPath: str = None) -> None:
        """convert() で生成したSVGをファイルに書き出す。"""
        if self.svg_content is None:
            raise RuntimeError("output() の前に convert() を呼び出してください。")

        dest = outputPath if outputPath else Path(self.inputPath).with_suffix(".svg")
        Path(dest).write_text(self.svg_content, encoding="utf-8")
        print(f"[完了] SVGを保存しました: {dest}  ({self.out_w} x {self.out_h} px)")
        print()
        print("  色を変えるには出力SVGの <style> 内の変数を編集してください:")
        for idx in range(1, min(4, self.path_count + 1)):
            print(f"    --fill-{idx}   : 輪郭{idx}の塗り色")
            print(f"    --stroke-{idx} : 輪郭{idx}の線の色")
        if self.path_count > 3:
            print(f"    ... 他 {self.path_count - 3} 個")


if __name__ == "__main__":
    config    = ARGConfig()
    if not Path(config.inputPath).exists():
        svgPath = input("変換するSVGパス : ")
    else:
        svgPath = config.inputPath
    converter = PNG2SVG(
        svgPath, 
        config.threshold, 
        config.smooth, 
        config.defaultStroke, 
        config.defaultFill, 
        config.svgWidth, 
        config.minArea
    )
    converter.convert()
    converter.output(config.outputPath)
