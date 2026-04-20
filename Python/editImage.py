#!/usr/bin/env python3
import cv2, os

class EditImage:
    def __init__(self, imgPath):
        self.set_image(imgPath)
    
    def set_image(self, imgPath):
        self.imgPath    = imgPath
        self.img        = cv2.imread(self.imgPath, 1)
        if self.img     is None:
            raise ValueError(f"OpenCVで画像が読み込めません : {self.imgPath}")
    
    def gray_scale(self):
        if len(self.img.shape) == 3:
            self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)

    def binarize(self, threshold = 100):    # 二値化（閾値は100。必要なら変更）
        self.gray_scale()
        _, img          = cv2.threshold(    # 閾値と出力画像を返す
            self.img, 
            threshold, 
            255,                            # 最大値
            cv2.THRESH_BINARY
        )
        self.img        = img
    
    def invert(self):                       # 色反転（白↔黒）
        img_inv         = cv2.bitwise_not(self.img)
        self.img        = img_inv

    def output(self, path = None):
        if path is not None:
            outPath     = path
        else:
            base, ext   = os.path.splitext(self.imgPath)
            outPath     = f"{base}_edit{ext}"

        cv2.imwrite(outPath, self.img)

if __name__ == "__main__":
    imgPath             = input("加工する画像ファイルのパス : ")
    editImage           = EditImage(imgPath)
    editImage.binarize()
    editImage.invert()
    editImage.output()
