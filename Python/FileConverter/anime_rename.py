import os, platform, sys

class MovieRename:
    def __init__(
        self,
        folder,
        config = {
            "id" : "25-221",
            "title" : "陰の実力者になりたくて",
        }
    ):
        self.path       = folder.replace("\"","")
        self.config     = config
    
    def convert(self):
        for filename in os.listdir(self.path):
            if self.config["id"] in filename:  # 置換対象文字列
                newName = filename.replace(self.config["id"], self.config["title"])
                if "_s1_" in newName:
                    newName = newName.replace("_s1", "")
                elif "_s2_" in newName:
                    newName = newName.replace("_s", "")
                elif "_s30_" in newName:
                    newName = newName.replace("_s30", "3")
                elif "_s0_" in newName:
                #    newName = newName.replace("_s0", f"SP {self.config["id"]}")
                    newName = newName.replace("_s0", f"")
                else:
                    newName = newName.replace("_s", "")

                newName = newName.replace("_p", " ")
                name, ext = os.path.splitext(newName)
                newName = f"{name}話{ext}"
                os.rename(
                    f"{self.path}/{filename}",
                    f"{self.path}/{newName}"
                )


if __name__ == "__main__":
    if platform.system() == 'Windows':
        os.system("title Movie Rename")
    path = input("フォルダ名を入力 : ")
    print(path)
    try:
        for file in os.listdir(path):
            print(f"├── {file}")
    except Exception as e:
        print(e)
        sys.exit(1)

    
    title = input("アニメタイトル : ")
    id = input("アニメID : ")
    

    config = {
        "id" : id,
        "title" : title,
    }
    
    animeRename = MovieRename(
        path, config
    )

    animeRename.convert()