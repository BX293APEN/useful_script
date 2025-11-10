class DOSWindowASCIIART:
    def __init__(
        self,
        color   = "red",
        bgcolor = "black",
        msg     = ["Hello", "World"]
    ):
        self.colorList = {
            "black"         : "\033[30m",
            "red"           : "\033[31m",
            "green"         : "\033[32m",
            "yellow"        : "\033[33m",
            "blue"          : "\033[34m",
            "purple"        : "\033[35m",
            "light_blue"    : "\033[36m",
            "white"         : "\033[37m",
            "light_red"     : "\033[91m",   # 明るい赤
            "light_green"   : "\033[92m",   # 明るい緑
            "light_yellow"  : "\033[93m",   # 明るい黄
            "light_blue"    : "\033[94m",   # 明るい青
            "light_purple"  : "\033[95m",   # 明るい紫
            "light_white"   : "\033[97m"    # 明るい白
        }

        self.bgColorList = {
            "black"         : "\033[40m",
            "red"           : "\033[41m",
            "green"         : "\033[42m",
            "yellow"        : "\033[43m",
            "blue"          : "\033[44m",
            "purple"        : "\033[45m",
            "light_blue"    : "\033[46m",
            "white"         : "\033[47m"
        }

        self.resetColor = "\033[0m"
        self.color = self.colorList.get(color, self.resetColor)
        self.bgColor = self.bgColorList.get(bgcolor, self.resetColor)
        self.msg = msg
    
    def display(self):
        for line in self.msg:
            print(f"{self.bgColor}{self.color}{line}{self.resetColor}")

    def set_message(self, msg):
        self.msg = msg

    def set_color(self, color):
        self.color = self.colorList.get(color, self.resetColor)

    def set_bgcolor(self, bgcolor):
        self.bgColor = self.bgColorList.get(bgcolor, self.resetColor)



if __name__ == "__main__":

    logo = [
        "║ ███╗  ████      ████   ║",
        "║ ██╔███╝██╔██  ██╝██║   ║",
        "║ ██║ ╚╝ ██║ ╚██╔██████╗ ║",
        "║ ██║███╗██║  ╚═╝ ╚██╔═╝ ║",
        "║ ███╝ ╚████     ██████╗ ║",
        "║ ╚═╝   ╚══╝     ╚═════╝ ║"
    ]

    dos = DOSWindowASCIIART(
        msg=logo,
        color   = "red",
        bgcolor = "black",
    )
    dos.display()
