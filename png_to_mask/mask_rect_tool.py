import cv2
import numpy as np
import os

class RectMaskTool:
    def __init__(self, image_path, mask_save_path):
        self.img = cv2.imread(image_path)
        if self.img is None:
            raise FileNotFoundError(image_path)
        self.clone = self.img.copy()
        self.mask = np.zeros(self.img.shape[:2], dtype=np.uint8)
        self.rects = []
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.current_rect = None
        self.mask_save_path = mask_save_path

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y
            self.current_rect = None
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.current_rect = (self.ix, self.iy, x, y)
        elif event == cv2.EVENT_LBUTTONUP and self.drawing:
            self.drawing = False
            self.current_rect = (self.ix, self.iy, x, y)
            self.rects.append(self.current_rect)
            # 画到mask
            x1, y1, x2, y2 = self.current_rect
            cv2.rectangle(self.mask, (x1, y1), (x2, y2), 255, -1)
            self.current_rect = None

    def run(self):
        cv2.namedWindow("image")
        cv2.setMouseCallback("image", self.mouse_callback)
        print("操作说明：\n"
              "鼠标左键拖动画矩形，可多次画\n"
              "'z' 撤销上一步\n"
              "'s' 保存mask并退出\n"
              "'r' 重置所有矩形\n"
              "ESC 退出不保存")
        while True:
            display = self.img.copy()
            # 画已完成的矩形
            for rect in self.rects:
                x1, y1, x2, y2 = rect
                cv2.rectangle(display, (x1, y1), (x2, y2), (0,255,0), 2)
            # 画当前正在拖动的矩形
            if self.drawing and self.current_rect:
                x1, y1, x2, y2 = self.current_rect
                cv2.rectangle(display, (x1, y1), (x2, y2), (0,0,255), 1)
            cv2.imshow("image", display)
            key = cv2.waitKey(10) & 0xFF
            if key == ord('z'):
                if self.rects:
                    # 撤销
                    self.rects.pop()
                    self.mask = np.zeros(self.img.shape[:2], dtype=np.uint8)
                    for rect in self.rects:
                        x1, y1, x2, y2 = rect
                        cv2.rectangle(self.mask, (x1, y1), (x2, y2), 255, -1)
            elif key == ord('r'):
                self.rects.clear()
                self.mask = np.zeros(self.img.shape[:2], dtype=np.uint8)
            elif key == ord('s'):
                cv2.imwrite(self.mask_save_path, self.mask)
                print(f"Mask saved to {self.mask_save_path}")
                break
            elif key == 27:  # ESC
                print("退出，不保存。")
                break
        cv2.destroyAllWindows()

if __name__ == "__main__":
    img_path = "sagittal_midResize_0000.png"
    mask_path = "sagittal_midResize.png"
    RectMaskTool(img_path, mask_path).run()