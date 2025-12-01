import numpy as np

# pip install sounddevice
import sounddevice as sd

from time import sleep

class SoundWaveMaker:
    def __init__(
        self,
        rateFreq = 44100
    ):
        self.rateFreq           = rateFreq
        self.referenceSound     = {
            "ド" : 261.626,
            "ド#" : 277.183, 
            "レ" : 293.665, 
            "レ#" : 311.127, 
            "ミ" : 329.628, 
            "ファ" : 349.228, 
            "ファ#" : 369.994, 
            "ソ" : 391.995, 
            "ソ#" : 415.305, 
            "ラ" : 440.000, 
            "ラ#" : 466.164, 
            "シ" : 493.883, 
            "C" : 261.626,
            "C#" : 277.183, 
            "D" : 293.665, 
            "D#" : 311.127, 
            "E" : 329.628, 
            "F" : 349.228, 
            "F#" : 369.994, 
            "G" : 391.995, 
            "G#" : 415.305, 
            "A" : 440.000, 
            "A#" : 466.164, 
            "B" : 493.883, 
        }
    
    def get_freq(self, code):
        if code in self.referenceSound:
            return self.referenceSound[code]
        else:
            return 0

    def output(
        self, 
        sound       = [],
        duration    = 1.0,     # 再生時間（秒）
        wait        = False
    ):
        t = np.linspace(0, duration, int(self.rateFreq * duration))
        audio = sum([np.sin(2 * np.pi * s * t) for s in sound])/len(sound)
        sd.play(audio, self.rateFreq)
        if wait:
            sd.wait()  # 再生が終わるまで待つ

if __name__ == "__main__":
    swm = SoundWaveMaker()
    swm.output(
        [
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ") * (2 ** (-1))
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ド"),
            swm.get_freq("ド"),
            swm.get_freq("ド"),
            swm.get_freq("ド") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ") * (2 ** (-1))
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ミ"),
            swm.get_freq("ミ"),
            swm.get_freq("ミ"),
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ソ"),
            swm.get_freq("ソ"),
            swm.get_freq("ソ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ミ"),
            swm.get_freq("ミ"),
            swm.get_freq("ミ"),
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ") * (2 ** (-1))
            
        ],
        duration    = 2.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ミ"),
            swm.get_freq("ド"),
            swm.get_freq("ソ"),
            swm.get_freq("ド") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ド"),
            swm.get_freq("ソ"),
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ド"),
            swm.get_freq("ラ"),
            swm.get_freq("ファ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ミ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 0.5,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ミ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ファ#") * (2 ** (-1))
            
        ],
        duration    = 0.5,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("レ") * 2,
            swm.get_freq("ラ"),
            swm.get_freq("レ") * 2,
            swm.get_freq("ソ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("シ"),
            swm.get_freq("ソ"),
            swm.get_freq("レ") * 2,
            swm.get_freq("レ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ファ#"),
            swm.get_freq("ド") * 2,
            swm.get_freq("レ#") * (2 ** (-1))
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ミ"),
            swm.get_freq("シ"),
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ミ"),
            swm.get_freq("ド"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ド") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ド"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ファ"),
            swm.get_freq("ファ"),
            swm.get_freq("ド") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ド"),
            swm.get_freq("ラ"),
            swm.get_freq("ファ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("レ") * 2,
            swm.get_freq("ファ"),
            swm.get_freq("ラ"),
            swm.get_freq("レ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ド") * 2,
            swm.get_freq("ラ"),
            swm.get_freq("ラ"),
            swm.get_freq("ラ") * (2 ** (-2))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(  #
        [
            swm.get_freq("レ") * 2,
            swm.get_freq("ファ"),
            swm.get_freq("ラ"),
            swm.get_freq("レ") * (2 ** (-1))
            
        ],
        duration    = 2.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ミ"),
            swm.get_freq("ド"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ラ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ミ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ソ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ファ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ファ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ミ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ミ"),
            swm.get_freq("ド"),
            swm.get_freq("ソ"),
            swm.get_freq("ド") * (2 ** (-1))
            
        ],
        duration    = 1.5,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ミ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 0.5,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("シ"),
            swm.get_freq("ソ") * (2 ** (-1))
            
        ],
        duration    = 2.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ファ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ファ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ド") * 2,
            swm.get_freq("ラ"),
            swm.get_freq("ド") * 2,
            swm.get_freq("ファ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )

    swm.output(
        [
            swm.get_freq("レ") * 2,
            swm.get_freq("ラ"),
            swm.get_freq("ラ"),
            swm.get_freq("ファ") * (2 ** (-1))
            
        ],
        duration    = 2.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ド") * 2,
            swm.get_freq("ミ"),
            swm.get_freq("ラ"),
            swm.get_freq("ラ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("レ") * 2,
            swm.get_freq("ファ"),
            swm.get_freq("ラ"),
            swm.get_freq("レ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ラ"),
            swm.get_freq("ラ"),
            swm.get_freq("ラ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ソ"),
            swm.get_freq("ソ"),
            swm.get_freq("ソ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ラ"),
            swm.get_freq("ラ"),
            swm.get_freq("ラ"),
            swm.get_freq("ラ") * (2 ** (-1))
            
        ],
        duration    = 1.0,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ソ"),
            swm.get_freq("ソ"),
            swm.get_freq("ソ"),
            swm.get_freq("ソ") * (2 ** (-1))
            
        ],
        duration    = 0.5,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("ミ"),
            swm.get_freq("ミ"),
            swm.get_freq("ミ"),
            swm.get_freq("ミ") * (2 ** (-1))
            
        ],
        duration    = 0.5,
        wait        = True
    )
    swm.output(
        [
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ"),
            swm.get_freq("レ") * (2 ** (-1))
            
        ],
        duration    = 2.0,
        wait        = True
    )
    

    # sleep(5)
