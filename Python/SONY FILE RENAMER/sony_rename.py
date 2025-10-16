import glob, os, datetime, platform

class SonyFileRenamer:
    def __init__(
        self, 
        folder,
        config = [
            {
                "pattern" : "DSC*",
                "ext" : "JPG"
            }
        ]
    ):
        self.path       = folder.replace("\"","")
        self.nowTime    = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        self.config     = config
    
    def convert(self):
        i = 1
        for p in self.config:
            fileList = glob.glob(f"""{self.path}/{p["pattern"]}""")
            for file in fileList:
                newName = f"""{self.path}/{self.nowTime}_{i}.{p["ext"]}"""
                if not os.path.exists(newName):
                    os.rename(file, newName)
                    i+=1

if __name__ == "__main__":
    if platform.system() == 'Windows':
        os.system("title SONYファイルを変更")
    path = input("フォルダ名を入力 : ")

    config = [
        {
            "pattern" : "DSC*",
            "ext" : "JPG"
        },
        {
            "pattern" : "MOV*",
            "ext" : "mp4"
        },
        {
            "pattern" : "image*.webp",
            "ext" : "webp"
        },
        {
            "pattern" : "image*.png",
            "ext" : "png"
        },
        {
            "pattern" : "image*.jpg",
            "ext" : "jpg"
        },
    ]

    sfr = SonyFileRenamer(path, config)
    sfr.convert()
