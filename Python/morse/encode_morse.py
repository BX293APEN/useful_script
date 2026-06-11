import re, jaconv, time, json

class MorseCodeTranslator:
    def __init__(self, morseDataDir:str, tempo = 0.03, gpio = None):
        self.hiragana = re.compile(r'[\u3041-\u3096]') #ひらがなの登録
        self.katakana = re.compile(r'[\u30A0-\u30FA]') #カタカナの登録
        self.tempo =  tempo
        self.gpio = gpio
        with open(f"{morseDataDir}/morse.json", "r", encoding = "UTF-8") as morseDataFile:
            morseDataJSON = json.loads(morseDataFile.read())
        self.morseData = dict(**morseDataJSON["base"], **morseDataJSON["ja"], **morseDataJSON["en"])

    def tu(self):
        if self.gpio is not None:
            self.gpio.value = True
            time.sleep(self.tempo * 3)
            self.gpio.value = False
            time.sleep(self.tempo)

    def to(self):
        if self.gpio is not None:
            self.gpio.value = True
            time.sleep(self.tempo)
            self.gpio.value = False
            time.sleep(self.tempo)
        
    def sep(self):
        if self.gpio is not None:
            self.gpio.value = False
            time.sleep(self.tempo * 2)
            

    def exchange(self, morsestr):
        val = ""
        for code in morsestr:
            if code == "　":
                code = "space"
            elif code == " ":
                code = "space"
            elif code == "゛":
                code = "濁点"
            elif code == "゜":
                code = "半濁点"
                
            elif (self.hiragana.search(code) is not None):
                hkataka = jaconv.hira2hkata(code)
                hkm = jaconv.h2z(hkataka[0])
                try:
                    hka = jaconv.h2z(hkataka[1])
                    val += f"{self.morseData[jaconv.kata2hira(hkm)]} "
                    if hka == '\uFF9E':
                        code = "濁点"
                    elif hka == '\uFF9F':
                        code = "半濁点"
                
                except IndexError:
                    hka = ""

            elif (self.katakana.search(code) is not None):
                hkataka = jaconv.z2h(code)
                hkm = jaconv.h2z(hkataka[0])
                try:
                    hka = jaconv.h2z(hkataka[1])
                    val += f"{self.morseData[jaconv.kata2hira(hkm)]} "
                    if hka == '\uFF9E':
                        code = "濁点"
                    elif hka == '\uFF9F':
                        code = "半濁点"
                
                except IndexError:
                    hka = ""
                    code = jaconv.kata2hira(hkm)
            else:
                code = code.lower()
            val += f"{self.morseData[code]} "
        return val
    
    def morse_gpio(self, morsestr):
        val = self.exchange(morsestr)
        for c in val:
            if c == "-":
                self.tu()
            elif c == ".":
                self.to()
            else:
                self.sep()
        return val

if __name__ == "__main__":
    morse = MorseCodeTranslator("./")
    print(morse.exchange("sos"))