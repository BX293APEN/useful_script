from matplotlib import pyplot as plt
import numpy as np
import os

class GraphPlot():
    def __init__(self, saveFile = f"./グラフ.png", x = 20, y = 10, dpi = 100):
        self.fig                    = plt.figure(figsize = (x, y), dpi = dpi)
        plt.rcParams["font.family"] = "HGGothicE"   # 使用するフォント
        plt.rcParams["font.size"]   = 12
        self.file = saveFile
        
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.fig.savefig(self.file, format="png")
        self.fig.show()
        self.fig.clf()
        plt.close()
    
    def fig_config(
        self, 
        figure, 
        title = None, xLabel = None, yLabel = None,
        xMin = None, xMax = None, yMin = None, yMax = None,
        legend = False
    ):
        
        if title is not None:
            figure.set_title(title)
        if xLabel is not None:
            figure.set_xlabel(xLabel)
        if yLabel is not None:
            figure.set_ylabel(yLabel)
        if xMin is not None:
            figure.set_xlim(left = xMin)
        if xMax is not None:
            figure.set_xlim(right = xMax)
        if yMin is not None:
            figure.set_ylim(bottom = yMin)
        if yMax is not None:
            figure.set_ylim(top = yMax)
        if legend:
            figure.legend()

if __name__ == "__main__":
    directory = os.path.dirname(__file__)
    with GraphPlot(f"{directory}/グラフ.png", 20, 10) as f:
        fig     = f.fig
        fig1    = fig.add_subplot(2,2,1)
        f.fig_config(fig1, "タイトル", "X軸", "Y軸", -3, 3, -3, 3)
        x = np.arange(1, 4000)
        fig1.plot(x/100, np.sin(x/100))
        fig1.grid()