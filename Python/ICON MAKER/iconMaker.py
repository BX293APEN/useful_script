from PIL import Image, ImageFilter
import os, subprocess

class png2icon():
    def __init__(self, filePath, extension = "ico"):
        self.file                       = filePath
        self.baseExtension              = os.path.splitext(self.file)[1].lower()
        self.extension                  = extension.lower()
        self.saveFile                   = f"{os.path.splitext(self.file)[0]}.{self.extension}"
        if self.baseExtension           != ".mp4":
            self.im                     = Image.open(self.file)
        
        self.resizeFlag                 = False
    
    def resize(self,x,y):
        if (self.baseExtension          != ".mp4"):
            self.frames                 = []
            self.duration               = []

            # オリジナルのフレームをすべて読み込む
            while True:
                try:
                    if ((x!=0) and (y!=0)):
                        frame           = self.im.copy().resize((x, y))
                    else:
                        frame           = self.im.copy()
                    self.frames.append(frame)
                    self.duration.append(self.im.info.get('duration', 100))
                    self.im.seek(self.im.tell() + 1)
                except:
                    break

        self.resizeFlag     = True

    def save(self):
        if self.baseExtension   != ".mp4":
            if self.resizeFlag  == False:
                self.resize(0,0)

            if len(self.frames) == 1:
                self.frames[0].save(self.saveFile)
            else:
                self.frames[0].save(
                    self.saveFile, 
                    save_all=True,
                    append_images=self.frames[1:],
                    loop=0, # 0は無限ループ
                    duration=self.duration,
                    minimize_size=True
                )
        else:
            cmd = [
                "ffmpeg",
                "-i", self.file,
                "-filter:v", "fps=30",
                "-lossless", "0",
                "-compression_level", "6",
                "-q:v", "60",
                "-loop", "0",
            ]

            option = []
            if self.extension == "webp":
                option = ["-vcodec", "libwebp"]

            for o in option:
                cmd.append(o)

            cmd.append(self.saveFile)
            try:
                subprocess.run(cmd)
            except:
                print("生成失敗")

if __name__ == "__main__":
    ext = "ico"
    filePath        = input("画像のパス : ")
    extension       = input("出力ファイルの拡張子 (デフォルト : ico) : ")
    if extension    != "":
        ext         = extension
    sizeX = input("横のサイズ : ")
    if sizeX        == "":
        sizeX       = 0
    else:
        sizeX       = int(sizeX)
    
    sizeY           = input("縦のサイズ : ")
    if sizeY        == "":
        sizeY       = 0
    else:
        sizeY       = int(sizeY)
    ico             = png2icon(filePath, ext)
    ico.resize(sizeX,sizeY)
    ico.save()
