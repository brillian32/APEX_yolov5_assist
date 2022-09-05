from aim_csgo.apex_aim import lock, show_fps, show_top_most
from aim_csgo.screen_inf import grab_screen_mss, grab_screen_win32, get_parameters
from aim_csgo.cs_model import load_model
import cv2
import win32gui
import win32con
import torch
import numpy as np

import sys
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from aim_csgo.verify_args import verify_args
from utils.general import non_max_suppression, scale_coords, xyxy2xywh
from utils.augmentations import letterbox
import pynput
import argparse
import time
import os
from simple_pid import PID

from widget import ui_mainFrom

parser = argparse.ArgumentParser()
parser.add_argument('--model-path', type=str, default='weights/best.pt', help='模型位址 model address')
parser.add_argument('--imgsz', type=int, default=640, help='和訓練模型时imgsz一樣')
parser.add_argument('--conf-thres', type=float, default=0.1, help='置信閥值')
parser.add_argument('--iou-thres', type=float, default=0.7, help='交並比閥值')
parser.add_argument('--use-cuda', type=bool, default=True, help='是否使用cuda')
parser.add_argument('--show-window', type=bool, default=True,
                    help='是否顯示實時檢測窗口(debug用,若是True,不要去點右上角的X)')
parser.add_argument('--top-most', type=bool, default=False, help='是否保持窗口置頂')
parser.add_argument('--resize-window', type=float, default=1, help='缩放窗口大小,缩放系数')
parser.add_argument('--thickness', type=int, default=4, help='邊框粗細，需大於1/resize-window')
parser.add_argument('--show-fps', type=bool, default=True, help='是否顯示fps')
parser.add_argument('--show-label', type=bool, default=True, help='是否顯示標籤')

parser.add_argument('--use_mss', type=str, default=True, help='是否使用mss截屏；为False時使用win32截屏')

parser.add_argument('--region', type=list, default=[0.18, 0.35],
                    help='檢測範圍；分别为x軸和y軸，(1.0, 1.0)表示全屏檢測，越低檢測範圍越小(以屏幕中心為檢測中心)')

parser.add_argument('--hold-lock', type=bool, default=True, help='lock模式；True為按住，False為切換')
parser.add_argument('--lock-sen', type=float, default=1.0, help='lock幅度系數,遊戲中靈敏度(建議不要調整)')
parser.add_argument('--lock-smooth', type=float, default=0.5, help='lock平滑系数；越大越平滑')
parser.add_argument('--lock-button', type=str, default='right', help='lock按鍵；只支持鼠標按键')
parser.add_argument('--head-first', type=bool, default=False, help='是否優先瞄頭')
parser.add_argument('--lock-tag', type=list, default=[0], help='對應標籤；person(若模型不同請自行修改對應標籤)')
parser.add_argument('--lock-choice', type=list, default=[0], help='目標選擇；决定鎖定的目標，從自己的標籤中選')

parser.add_argument('--detect-arange', type=int, default=80000, help='检测范围')
parser.add_argument('--head-to-foot', type=float, default=0, help='准星位置，从头到脚')

global args
args = parser.parse_args()

'------------------------------------------------------------------------------------'
# def AIFunc():
verify_args(args)

cur_dir = os.path.dirname(os.path.abspath(__file__)) + '\\'

args.model_path = cur_dir + args.model_path
args.lock_tag = [str(i) for i in args.lock_tag]
args.lock_choice = [str(i) for i in args.lock_choice]

device = 'cuda' if args.use_cuda else 'cpu'
half = device != 'cpu'
imgsz = args.imgsz

conf_thres = args.conf_thres
iou_thres = args.iou_thres

top_x, top_y, x, y = get_parameters()
len_x, len_y = int(x * args.region[0]), int(y * args.region[1])
top_x, top_y = int(top_x + x // 2 * (1. - args.region[0])), int(top_y + y // 2 * (1. - args.region[1]))

monitor = {'left': top_x, 'top': top_y, 'width': len_x, 'height': len_y}

model = load_model(args)
stride = int(model.stride.max())
names = model.module.names if hasattr(model, 'module') else model.names

lock_mode = False
team_mode = True

mouse = pynput.mouse.Controller()

# pid係數可自行調整(以下為我自己使用的參數)
pidx = PID(1.2, 3.51, 0.0, setpoint=0, sample_time=0.001, )
pidy = PID(1.22, 0.12, 0.0, setpoint=0, sample_time=0.001, )
pidx.output_limits = (-4000, 4000)
pidy.output_limits = (-3000, 3000)

if args.show_window:
    cv2.namedWindow('aim', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('aim', int(len_x * args.resize_window), int(len_y * args.resize_window))

exit_loop = False
lock_mode_toggle = True

def on_click(x, y, button, pressed):
    global lock_mode
    if button == eval('pynput.mouse.Button.' + args.lock_button):
        if args.hold_lock:
            if pressed:
                lock_mode = True
                # globals()['lock_mode_toggle'] = True
                print('locking...')
            else:
                lock_mode = False
                print('lock mode off')
                # globals()['lock_mode_toggle'] = False
        else:
            if pressed:
                lock_mode = not lock_mode
                print('lock mode', 'on' if lock_mode else 'off')


listener = pynput.mouse.Listener(on_click=on_click)
listener.start()

print('enjoy yourself!')

# def AIFunc(a):


# AIFunc()



# 继承QThread
class Mythread(QThread):
    # 定义信号
    lockingSig = pyqtSignal(object, object, object, object, object, object, object, object, object)
    showFpsSig = pyqtSignal(object, object, object, object, object)
    showTopMost = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # 下面的初始化方法都可以，有的python版本不支持
        # super(Mythread, self).__init__()

    def run(self):
        # 要定义的行为，比如开始一个活动什么的
        print('start....')
        t0 = time.time()
        cnt = 0
        while True:
            if globals()['lock_mode_toggle'] == False:
                time.sleep(1)
                print("globals()['lock_mode_toggle'] ", globals()['lock_mode_toggle'])
                continue
            if cnt % 20 == 0:
                top_x, top_y, x, y = get_parameters()
                len_x, len_y = int(x * args.region[0]), int(y * args.region[1])
                top_x, top_y = int(top_x + x // 2 * (1. - args.region[0])), int(top_y + y // 2 * (1. - args.region[1]))
                monitor = {'left': top_x, 'top': top_y, 'width': len_x, 'height': len_y}
                cnt = 0

            if args.use_mss:
                t1 = time.time()
                img0 = grab_screen_mss(monitor)
                img0 = cv2.resize(img0, (len_x, len_y))
                # print('111', time.time() -t1)
            else:
                t2 = time.time()
                img0 = grab_screen_win32(region=(top_x, top_y, top_x + len_x, top_y + len_y))
                img0 = cv2.resize(img0, (len_x, len_y))
                # print('222', time.time() - t2)

            img = letterbox(img0, imgsz, stride=stride)[0]

            img = img.transpose((2, 0, 1))[::-1]
            img = np.ascontiguousarray(img)

            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()
            img /= 255.

            if len(img.shape) == 3:
                img = img[None]

            pred = model(img, augment=False, visualize=False)[0]
            pred = non_max_suppression(pred, conf_thres, iou_thres, agnostic=False)

            aims = []
            for i, det in enumerate(pred):
                gn = torch.tensor(img0.shape)[[1, 0, 1, 0]]
                if len(det):
                    det[:, :4] = scale_coords(img.shape[2:], det[:, :4], img0.shape).round()

                    for *xyxy, conf, cls in reversed(det):
                        # bbox:(tag, x_center, y_center, x_width, y_width)
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh)  # label format
                        aim = ('%g ' * len(line)).rstrip() % line
                        aim = aim.split(' ')
                        aims.append(aim)

                if len(aims):
                    if lock_mode:
                        print("lock_mode", lock_mode)
                        # lock(aims, mouse, top_x, top_y, len_x, len_y, args, pidx, pidy)
                        self.lockingSig.emit(aims, mouse, top_x, top_y, len_x, len_y, args, pidx, pidy)

                if args.show_window:
                    for i, det in enumerate(aims):
                        tag, x_center, y_center, width, height = det
                        x_center, width = len_x * float(x_center), len_x * float(width)
                        # print("width:" , width)
                        # print("x_center:", x_center)
                        y_center, height = len_y * float(y_center), len_y * float(height)
                        top_left = (int(x_center - width / 2.), int(y_center - height / 2.))
                        # print("top_left:", top_left)
                        bottom_right = (int(x_center + width / 2.), int(y_center + height / 2.))
                        # print("bottom_right:", bottom_right)
                        cv2.rectangle(img0, top_left, bottom_right, (0, 255, 0), thickness=args.thickness)
                        if args.show_label:
                            cv2.putText(img0, tag, top_left, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (235, 0, 0), 4)

            if args.show_window:
                if args.show_fps:
                    self.showFpsSig.emit(cv2, lock_mode, team_mode, img0, t0)
                    t0 = time.time()

                if args.top_most:
                    self.showTopMost.emit()
                cv2.waitKey(1)
            cnt += 1
            if globals()['exit_loop'] == True:
                break
        print('end....')


def setParam(ui):
    args.conf_thres = ui.value_belive.value()
    args.iou_thres = ui.iou.value()
    args.use_cuda = ui.cuda.isChecked()
    args.lock_smooth = ui.smooth.value()
    args.hold_lock = True if ui.plan.currentIndex() == 0 else False
    args.show_window = ui.debug.isChecked()
    args.lock_button = 'right' if ui.mouse.currentIndex() == 0 else 'left'
    args.use_mss = ui.mess.isChecked()
    args.region[0] = ui.x_value.value()
    args.region[1] = ui.y_value.value()
    # 暂未设置 不生效状态
    #args.model_path = ui.model_path.text()
    args.detect_arange = ui.area_detect.value()
    args.head_to_foot = ui.headtofoot.value()

    globals()['lock_mode_toggle'] = ui.start_lock.isChecked()
    print("globals()['lock_mode_toggle'] ", globals()['lock_mode_toggle'])

def exit_loop_func():
    globals()['exit_loop'] = True



app = QApplication(sys.argv)
main_window = QMainWindow()
auto_ui_window = ui_mainFrom.Ui_MainWindow()  # 实例化部件
auto_ui_window.setupUi(main_window)  # 调用setupUi()方法，并传入 主窗口 参数。

auto_ui_window.pushButton.clicked.connect(lambda: setParam(auto_ui_window))
auto_ui_window.exit_btn.clicked.connect(lambda: exit_loop_func())
# auto_ui_window.exit_btn.clicked.connect(lambda: os._exit(0))  # 强退进程

main_window.setWindowTitle('Apex 辅助')
main_window.show()

# 瞄准线程实例化
aim_worker = Mythread()
aim_worker.start()

# lock函数在主线程
aim_worker.lockingSig.connect(lock)
aim_worker.showFpsSig.connect(show_fps)
aim_worker.showTopMost.connect(show_top_most)

main_window.activateWindow()
app.exec()
exit_loop_func()

# 等待AI线程结束
time.sleep(1)
os._exit(0)  # 强退进程
