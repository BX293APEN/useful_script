"""
# GraphPlot.py

matplotlib のメソッド名（`add_subplot` / `plot` / `pie` / `bar` / `barh` など）は
グラフの種類ごとにバラバラで覚えにくい。

このモジュールは `matplotlib` のメソッド名自体は内部でそのまま使いながら、
利用者側は次の 3 つの操作だけでグラフを組み立てられるようにするラッパー。

| 操作 | 役割 |
| --- | --- |
| `fig.add_subplot(...)` | matplotlib 標準のまま。`Axes` を1つ作る |
| `GraphPlot.add_element(...)` | その `Axes` にデータ（系列・スライス・棒）を1つずつ追加する |
| `GraphPlot.fig_config(...)` | タイトル・軸ラベル・凡例などを設定し、最終的な描画を確定する |

対応しているグラフの種類（`kind`）

| kind | グラフ |
| --- | --- |
| `"line"` | 折れ線グラフ |
| `"pie"` | 円グラフ（内側/外側ラベル混在・中央くり抜き対応） |
| `"barh"` | 横軸棒グラフ |
| `"barv"` | 縦軸棒グラフ |
"""

import os
from typing import Any

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes


class GraphPlot:
    """
    `with` 文で使う matplotlib のラッパークラス。

    | 引数 | 型 | 説明 |
    | --- | --- | --- |
    | `saveFile` | `str | None` | 保存先パス。`None` の場合は保存しない |
    | `x` | `float` | Figure の横幅（インチ） |
    | `y` | `float` | Figure の縦幅（インチ） |
    | `dpi` | `int` | 解像度 |
    | `show` | `bool` | `plt.show()` を呼ぶかどうか |
    | `font` | `str` | 使用したい日本語フォント名 |
    """


    def __init__(
        self,
        saveFile: str | None    = "./グラフ.png",
        x: float                = 20,
        y: float                = 10,
        dpi: int                = 100,
        title : str | None      = None,
        titleSize               = 16,
        show: bool              = True,
        font: str               = "HGGothicE",
    ):
        self.fig                = plt.figure(figsize=(x, y), dpi=dpi)
        plt.rcParams["font.family"] = font  # 使用するフォント
        plt.rcParams["font.size"]   = 12

        if title is not None:
            self.fig.suptitle(title, fontsize = titleSize)

        self.file                   = saveFile
        self.doShow                 = show

        # Axes単位でデータを蓄積するための内部状態。
        # key: id(Axes), value: {"kind": str, "pie": {...}, "bar": {...}}
        self._states: dict[int, dict[str, Any]] = {}

        # 円グラフの外側ラベルを結ぶ引き出し線のスタイル定義（クラス内に閉じる）。
        # キーは `fig_config(..., outerLineStyle=...)` に渡す値と対応する。
        #
        # | キー | 見た目 | connectionstyle |
        # | --- | --- | --- |
        # | `"angle"` | カクカク（直角に折れ曲がる） | `angle,angleA=0,angleB={angle}` |
        # | `"straight"` | 最短距離の直線 | `arc3,rad=0` |
        # | `"arc"` | 緩やかな弧 | `arc3,rad=0.3` |
        self._OUTER_LINE_STYLES: dict[str, str] = {
            "angle": "angle,angleA=0,angleB={angle}",
            "straight": "arc3,rad=0",
            "arc": "arc3,rad=0.3",
        }

    def __enter__(self) -> "GraphPlot":
        return self

    def __exit__(self, *args) -> None:
        if self.file is not None:
            self.fig.savefig(self.file, format="png")
        if self.doShow:
            try:
                self.fig.show()
            except Exception:
                pass  # GUIバックエンドが無い環境では無視する
        self.fig.clf()
        plt.close(self.fig)

    # ------------------------------------------------------------------
    # 内部ヘルパー: フォント解決 / 引き出し線スタイル解決
    # ------------------------------------------------------------------
    def _resolve_connection_style(self, style_name: str, angle: float) -> str:
        """
        円グラフの外側ラベル用引き出し線の `connectionstyle` 文字列を解決する。

        | 引数 | 型 | 説明 |
        | --- | --- | --- |
        | `style_name` | `str` | `_OUTER_LINE_STYLES` のキー（`"angle"` / `"straight"` / `"arc"`） |
        | `angle` | `float` | スライス中心の角度（度）。`"angle"` スタイルの折れ曲がり位置計算に使う |

        戻り値

        | 型 | 説明 |
        | --- | --- |
        | `str` | `matplotlib.patches.ConnectionStyle` に渡せる文字列 |
        """
        if style_name not in self._OUTER_LINE_STYLES:
            valid = ", ".join(self._OUTER_LINE_STYLES)
            raise ValueError(f"未対応の outerLineStyle です: {style_name}（指定可能な値: {valid}）")
        return self._OUTER_LINE_STYLES[style_name].format(angle=angle)

    # ------------------------------------------------------------------
    # 公開API: add_element
    # ------------------------------------------------------------------
    def add_element(
        self,
        figure: Axes,
        title: str,
        value: Any,
        color: str | None = None,
        kind: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        `Axes` にデータを1つ追加する。折れ線グラフはこの時点で即座に描画され、
        円グラフ・棒グラフはデータを蓄積するだけで、実際の描画は `fig_config` の
        呼び出し時にまとめて行われる。

        | 引数 | 型 | 説明 |
        | --- | --- | --- |
        | `figure` | `Axes` | `fig.add_subplot(...)` で作成した対象 |
        | `title` | `str` | 系列名 / スライス名 / 棒グラフの凡例ラベル |
        | `value` | `Any` | 値。折れ線は配列、円・棒は数値（円グラフの中央円は文字列可） |
        | `color` | `str | None` | 色。`None` なら自動で割り当てる |
        | `kind` | `str | None` | `"line"` / `"pie"` / `"barh"` / `"barv"`。同一 `Axes` への最初の呼び出しでのみ必須 |
        | `**kwargs` | `dict` | グラフの種類によって変わる追加オプション（下表） |

        `kind="line"` のとき

        | key | 型 | 説明 |
        | --- | --- | --- |
        | `x` | `array-like` | X軸の値。省略時は `1, 2, 3, ...` の連番 |
        | `marker` | `str` | マーカー形状（デフォルト `"o"`） |
        | `linestyle` | `str` | 線種（デフォルト `"-"`） |

        `kind="pie"` のとき

        | key | 型 | 説明 |
        | --- | --- | --- |
        | `circle` | `bool` | `True` の場合、通常のスライスではなく中央くり抜き円のラベル（`f"{title}\\n{value}"`）として登録する |
        | `outer_pos` | `tuple[float, float]` | このスライスの外側ラベルを表示する座標(data座標系)を個別指定する |
        | `labelTitle` | `str` | 指定すると、このスライスのグラフ上の表示（内側/外側ラベル）のみを`title`や自動計算した値を使わず、この文字列で上書きする。凡例には影響せず、常に`title`（元のラベル名）が使われる |

        `kind="barh"` / `"barv"` のとき

        | key | 型 | 説明 |
        | --- | --- | --- |
        | `categories` | `list[str]` | カテゴリ（軸の目盛りラベル）。系列を追加するたびに渡してよい（最後に渡した値を使用） |

        戻り値

        | 型 | 説明 |
        | --- | --- |
        | `None` | 内部状態の更新、または即時描画のみ行う |
        """
        ax_key = id(figure)
        if ax_key not in self._states:
            if kind is None:
                raise ValueError(
                    "同一Axesへの最初の add_element 呼び出しでは kind "
                    "('line' / 'pie' / 'barh' / 'barv') を指定してください"
                )
            self._states[ax_key] = {
                "kind": kind,
                "pie": {
                    "labels": [], "values": [], "colors": [],
                    "outer_positions": {}, "label_titles": {}, "center_label": None,
                },
                "bar": {"categories": None, "series": []},
            }
        state = self._states[ax_key]
        kind = state["kind"]

        if kind == "line":
            # --- 折れ線グラフ: 呼び出された時点で即座に1本の線を描画する ---
            xs = kwargs.get("x")
            if xs is None:
                xs = np.arange(1, len(value) + 1)
            figure.plot(
                xs,
                value,
                label=title,
                color=color,
                marker=kwargs.get("marker", "o"),
                linestyle=kwargs.get("linestyle", "-"),
            )

        elif kind == "pie":
            if kwargs.get("circle"):
                # --- 中心の円を作成: f"{title}\n{value}" をくり抜き円の中央に表示する ---
                state["pie"]["center_label"] = f"{title}\n{value}"
            else:
                # --- 通常の要素追加: スライスとして蓄積し、実描画は fig_config で行う ---
                state["pie"]["labels"].append(title)
                state["pie"]["values"].append(value)
                state["pie"]["colors"].append(color)
                if "outer_pos" in kwargs:
                    state["pie"]["outer_positions"][title] = kwargs["outer_pos"]
                if "labelTitle" in kwargs:
                    state["pie"]["label_titles"][title] = kwargs["labelTitle"]

        elif kind in ("barh", "barv"):
            if "categories" in kwargs:
                state["bar"]["categories"] = kwargs["categories"]
            state["bar"]["series"].append({"title": title, "values": value, "color": color})

        else:
            raise ValueError(f"未対応の kind です: {kind}")

    # ------------------------------------------------------------------
    # 公開API: fig_config
    # ------------------------------------------------------------------
    def fig_config(
        self,
        figure: Axes,
        title: str | None = "タイトル",
        legend: bool = True,
        legendTitle: str = "凡例",
        legendPlace: str = "center left",
        legendFontSize: int = 20,
        **kwargs: Any,
    ) -> None:
        """
        `Axes` のタイトル・軸・凡例などを設定する。円グラフ・棒グラフは
        ここで初めて実際の描画（`ax.pie` / `ax.bar` / `ax.barh`）が行われる。

        | 引数 | 型 | 説明 |
        | --- | --- | --- |
        | `figure` | `Axes` | `add_element` で1回以上データを追加した対象 |
        | `title` | `str | None` | グラフタイトル |
        | `legend` | `bool` | 凡例を表示するか |
        | `legendTitle` | `str` | 凡例のタイトル |
        | `legendPlace` | `str` | 凡例の位置（`loc`） |
        | `legendFontSize` | `int` | 凡例のフォントサイズ |
        | `**kwargs` | `dict` | グラフの種類によって変わる追加オプション（下表） |

        `kind="line"` のとき

        | key | 型 | 説明 |
        | --- | --- | --- |
        | `xLabel` | `str` | X軸ラベル |
        | `yLabel` | `str` | Y軸ラベル |
        | `xMin` / `xMax` | `float` | X軸の表示範囲 |
        | `yMin` / `yMax` | `float` | Y軸の表示範囲 |
        | `grid` | `bool` | グリッド線を表示するか（デフォルト `True`） |

        `kind="pie"` のとき

        | key | 型 | 説明 |
        | --- | --- | --- |
        | `threshold` | `float` | この割合(%)未満のスライスを外側ラベルにする（デフォルト `10`） |
        | `isPercent` | `bool` | `True`の場合、`add_element`で渡した`value`を「既にパーセント(0〜100)」として扱う。`False`（デフォルト）の場合は実値として扱い、合計に対する割合を自動計算する |
        | `outerLineStyle` | `str` | 外側ラベルの引き出し線の形。指定できる値は下表 |
        | `startAngle` | `float` | 最初のスライス（`add_element`で最初に追加した要素）の開始角度（度）。`0`が3時方向、`90`（デフォルト）が12時方向で、`counterclock`の向きに回転していく基準角度になる |
        | `clockwise` | `bool` | `True`なら時計回りにスライスを配置する。`False`（デフォルト）なら反時計回り |
        | `labelFontSize` | `float` | スライスの内側/外側ラベルの文字サイズ（デフォルト `9`） |
        | `centerFontSize` | `float` | 中央くり抜き円のラベルの文字サイズ（デフォルト `11`） |

        `outerLineStyle` の指定値

        | 値 | 見た目 | 説明 |
        | --- | --- | --- |
        | `"angle"`（デフォルト） | カクカク | 円の中心から水平に出た後、ラベルへ直角に折れ曲がる線（`connectionstyle="angle"`） |
        | `"straight"` | 直線 | スライスからラベルまで最短距離で結ぶ直線（`connectionstyle="arc3,rad=0"`） |
        | `"arc"` | 弧 | 緩やかにカーブして結ぶ線（`connectionstyle="arc3,rad=0.3"`） |

        `kind="barh"` / `"barv"` のとき

        | key | 型 | 説明 |
        | --- | --- | --- |
        | `xLabel` | `str` | X軸ラベル（`barv` では未使用） |
        | `yLabel` | `str` | Y軸ラベル（`barh` では未使用） |
        | `groupWidth` | `float` | 同一カテゴリ内の棒グループ全体の幅（デフォルト `0.7`） |

        戻り値

        | 型 | 説明 |
        | --- | --- |
        | `None` | `figure` に対して直接描画・設定を行う |
        """
        ax_key = id(figure)
        state = self._states.get(ax_key)
        if state is None:
            raise ValueError("先に add_element でデータを追加してから fig_config を呼び出してください")
        kind = state["kind"]

        if kind == "line":
            if kwargs.get("xLabel") is not None:
                figure.set_xlabel(kwargs["xLabel"])
            if kwargs.get("yLabel") is not None:
                figure.set_ylabel(kwargs["yLabel"])
            if kwargs.get("xMin") is not None or kwargs.get("xMax") is not None:
                figure.set_xlim(left=kwargs.get("xMin"), right=kwargs.get("xMax"))
            if kwargs.get("yMin") is not None or kwargs.get("yMax") is not None:
                figure.set_ylim(bottom=kwargs.get("yMin"), top=kwargs.get("yMax"))
            if kwargs.get("grid", True):
                figure.grid(True, linestyle="--", alpha=0.5)
            legend_handles, legend_labels = figure.get_legend_handles_labels()

        elif kind == "pie":
            legend_handles, legend_labels = self._render_pie(
                figure,
                state["pie"],
                threshold=kwargs.get("threshold", 10),
                is_percent=kwargs.get("isPercent", False),
                outer_line_style=kwargs.get("outerLineStyle", "angle"),
                start_angle=kwargs.get("startAngle", 90),
                clockwise=kwargs.get("clockwise", False),
                label_font_size=kwargs.get("labelFontSize", 9),
                center_font_size=kwargs.get("centerFontSize", 11),
            )

        elif kind in ("barh", "barv"):
            legend_handles, legend_labels = self._render_bar(figure, state["bar"], kind, kwargs)

        else:
            raise ValueError(f"未対応の kind です: {kind}")

        if title is not None:
            figure.set_title(title)

        if legend:
            figure.legend(
                legend_handles,
                legend_labels,
                title=legendTitle,
                loc=legendPlace,
                bbox_to_anchor=kwargs.get("legendAnchor", (1.1, 0.5)),
                fontsize=legendFontSize,
            )

    # ------------------------------------------------------------------
    # 内部ヘルパー: 円グラフの実描画
    # ------------------------------------------------------------------
    def _render_pie(
        self,
        ax: Axes,
        pie_state: dict[str, Any],
        threshold: float = 10,
        is_percent: bool = False,
        outer_line_style: str = "angle",
        start_angle: float = 90,
        clockwise: bool = False,
        label_font_size: float = 9,
        center_font_size: float = 11,
    ) -> tuple[list, list[str]]:
        """
        円グラフを実際に描画する（内側/外側ラベル混在 + 中央くり抜き対応）。

        | 引数 | 型 | 説明 |
        | --- | --- | --- |
        | `ax` | `Axes` | 描画対象 |
        | `pie_state` | `dict` | `add_element` で蓄積したスライス情報 |
        | `threshold` | `float` | この割合(%)未満のスライスを外側ラベルにする |
        | `is_percent` | `bool` | `True`なら`value`を既にパーセントとして扱い、合計からの再計算をしない |
        | `outer_line_style` | `str` | 外側ラベルの引き出し線スタイル。`_OUTER_LINE_STYLES` のキーを参照 |
        | `start_angle` | `float` | 最初のスライスの開始角度（度）。`0`が3時方向、`90`が12時方向 |
        | `clockwise` | `bool` | `True`なら時計回り、`False`なら反時計回りにスライスを配置する |
        | `label_font_size` | `float` | スライスの内側/外側ラベルの文字サイズ |
        | `center_font_size` | `float` | 中央くり抜き円のラベルの文字サイズ |

        凡例のラベルには常に元のラベル名（`add_element` の `title`）を使う。
        `labelTitle` はグラフ上の表示（内側/外側ラベル）のみを上書きし、凡例には影響しない。

        戻り値

        | 型 | 説明 |
        | --- | --- |
        | `tuple[list, list[str]]` | 凡例用の `(ハンドル一覧, ラベル一覧)` |
        """
        labels = pie_state["labels"]
        values = pie_state["values"]
        colors = pie_state["colors"]
        outer_positions = pie_state["outer_positions"]
        label_titles = pie_state["label_titles"]
        center_label = pie_state["center_label"]

        total = sum(values)
        cmap = plt.get_cmap("tab10").colors
        # 色が未指定(None)のスライスにはカラーマップから自動で色を割り当てる
        resolved_colors = [c if c is not None else cmap[i % len(cmap)] for i, c in enumerate(colors)]

        wedges, _texts = ax.pie(
            values,
            colors=resolved_colors,
            startangle=start_angle,
            counterclock=not clockwise,
            wedgeprops={"edgecolor": "white", "linewidth": 1},
        )

        legend_labels: list[str] = []
        for wedge, value, label in zip(wedges, values, labels):
            angle = (wedge.theta2 + wedge.theta1) / 2.0
            x = np.cos(np.deg2rad(angle))
            y = np.sin(np.deg2rad(angle))

            # 内側/外側の判定には常に割合(%)を使う（isPercentでない場合は合計から計算）
            pct = value if is_percent else value / total * 100

            if label in label_titles:
                # --- labelTitle 指定あり: グラフ上の表示（内側/外側ラベル）のみをこの文字列で上書き。
                #     凡例は元のラベル名（label）のまま変更しない ---
                slice_text = label_titles[label]
            else:
                # --- デフォルト: スライスラベルは "label\n○○%" ---
                slice_text = f"{label}\n{pct:.0f}%"

            # --- 凡例には常に元のラベル名（title/label）を使う ---
            legend_labels.append(label)

            if pct >= threshold and label not in outer_positions:
                # --- 内側ラベル ---
                ax.text(
                    x * 0.75, y * 0.75, slice_text,
                    ha="center", va="center", fontsize=label_font_size, color="white", weight="bold",
                )
            else:
                # --- 外側ラベル: outer_positions に個別指定があればそれを使い、
                #     無ければ角度からの自動計算にフォールバックする ---
                xytext = outer_positions.get(label, (x * 1.5, y * 1.5))
                text_x, _text_y = xytext
                horizontal_align = "left" if text_x >= 0 else "right"
                connection_style = self._resolve_connection_style(outer_line_style, angle)
                ax.annotate(
                    slice_text,
                    xy=(x, y), xytext=xytext, ha=horizontal_align, va="center", fontsize=label_font_size,
                    arrowprops={"arrowstyle": "-", "connectionstyle": connection_style},
                )

        if center_label is not None:
            # --- 中央くり抜き円 + ラベル（title\nvalue のまま変更しない） ---
            ax.add_patch(plt.Circle((0, 0), radius=0.45, facecolor="white", edgecolor="none", zorder=3))
            ax.text(0, 0, center_label, ha="center", va="center", fontsize=center_font_size, weight="bold", zorder=4)

        ax.set_xlim(-1.9, 1.9)
        ax.set_ylim(-1.6, 1.6)
        ax.axis("equal")
        return list(wedges), legend_labels

    # ------------------------------------------------------------------
    # 内部ヘルパー: 棒グラフ（横/縦）の実描画
    # ------------------------------------------------------------------
    def _render_bar(
        self, ax: Axes, bar_state: dict[str, Any], kind: str, kwargs: dict[str, Any]
    ) -> tuple[list, list[str]]:
        """
        棒グラフ（横軸 `barh` / 縦軸 `barv`）を実際に描画する。

        | 引数 | 型 | 説明 |
        | --- | --- | --- |
        | `ax` | `Axes` | 描画対象 |
        | `bar_state` | `dict` | `add_element` で蓄積した系列情報 |
        | `kind` | `str` | `"barh"` または `"barv"` |
        | `kwargs` | `dict` | `fig_config` に渡された追加オプション |

        戻り値

        | 型 | 説明 |
        | --- | --- |
        | `tuple[list, list[str]]` | 凡例用の `(ハンドル一覧, ラベル一覧)` |
        """
        categories = bar_state["categories"] or []
        series_list = bar_state["series"]
        n = len(series_list)
        positions = np.arange(len(categories))
        group_width = kwargs.get("groupWidth", 0.7)
        bar_width = group_width / max(n, 1)

        cmap = plt.get_cmap("tab10").colors
        handles = []
        for i, series in enumerate(series_list):
            color = series["color"] if series["color"] is not None else cmap[i % len(cmap)]
            offset = (i - (n - 1) / 2) * bar_width
            if kind == "barh":
                bars = ax.barh(positions + offset, series["values"], height=bar_width, label=series["title"], color=color)
            else:
                bars = ax.bar(positions + offset, series["values"], width=bar_width, label=series["title"], color=color)
            handles.append(bars)

        if kind == "barh":
            ax.set_yticks(positions)
            ax.set_yticklabels(categories)
            if kwargs.get("xLabel") is not None:
                ax.set_xlabel(kwargs["xLabel"])
            ax.grid(True, axis="x", linestyle="--", alpha=0.5)
        else:
            ax.set_xticks(positions)
            ax.set_xticklabels(categories)
            if kwargs.get("yLabel") is not None:
                ax.set_ylabel(kwargs["yLabel"])
            ax.grid(True, axis="y", linestyle="--", alpha=0.5)

        labels = [series["title"] for series in series_list]
        return handles, labels


if __name__ == "__main__":
    directory = os.path.dirname(__file__) or "."

    with GraphPlot(f"{directory}/グラフ.png", 20, 10, title = "グラフ") as f:
        fig = f.fig

        # === 1. 折れ線グラフ ===============================================
        ax_line = fig.add_subplot(2, 2, 1)
        months = np.arange(1, 13)
        f.add_element(ax_line, "東京", [12, 15, 18, 22, 28, 33, 38, 36, 30, 24, 18, 14], kind="line", x=months)
        f.add_element(ax_line, "札幌", [8, 10, 13, 17, 21, 26, 30, 29, 24, 19, 13, 9], x=months)
        f.fig_config(ax_line, title="折れ線グラフ（月別平均気温）", xLabel="月", yLabel="気温 (℃)")

        # === 2. 円グラフ（内外ラベル混在 + 中央くり抜き） =====================
        ax_pie = fig.add_subplot(2, 2, 2)
        # 値は既に「割合(%)」として渡す例 -> isPercent=True で自動再計算をスキップ
        f.add_element(ax_pie, "Apple", 45, kind="pie")
        f.add_element(ax_pie, "Banana", 25, labelTitle=f"ばなな")
        f.add_element(ax_pie, "Cherry", 15, labelTitle="人気No.3")  # グラフ上の表示のみ上書き（凡例は"Cherry"のまま）
        f.add_element(ax_pie, "Durian", 8, outer_pos=(-1.3, 0.7))
        f.add_element(ax_pie, "Elderberry", 7, outer_pos=(-1.35, 1.2))
        f.add_element(ax_pie, "合計", "100%", circle=True)  # 中央くり抜き円のラベル（title\nvalueのまま）
        f.fig_config(
            ax_pie,
            title               = None, # "円グラフ（内ラベル・外ラベル混在）",
            legendTitle         = "果物",
            isPercent           = True,       # value を「既にパーセント」として扱う
            outerLineStyle      = "straight",  # 外側ラベルの線を最短距離の直線にする
            clockwise           = True,
            labelFontSize       = 15,
            centerFontSize      = 25,
        )

        # === 3. 横軸棒グラフ =================================================
        ax_barh = fig.add_subplot(2, 2, 3)
        f.add_element(ax_barh, "2024年", [120, 95, 140, 80], kind="barh", categories=["製品A", "製品B", "製品C", "製品D"])
        f.add_element(ax_barh, "2025年", [135, 100, 150, 90])
        f.fig_config(ax_barh, title="横軸棒グラフ（製品別売上）", xLabel="売上（百万円）")

        # === 4. 縦軸棒グラフ =================================================
        ax_barv = fig.add_subplot(2, 2, 4)
        f.add_element(ax_barv, "売上", [220, 260, 240, 300], kind="barv", categories=["Q1", "Q2", "Q3", "Q4"])
        f.add_element(ax_barv, "コスト", [150, 170, 165, 190])
        f.fig_config(ax_barv, title="縦軸棒グラフ（四半期売上とコスト）", yLabel="金額（百万円）")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
