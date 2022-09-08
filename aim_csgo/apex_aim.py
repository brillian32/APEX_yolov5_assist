import win32con
import win32gui

import aim_csgo.ghub_mouse as ghub
from math import *
import time


def lock(aims, mouse, top_x, top_y, len_x, len_y, args, pidx, pidy):
    mouse_pos_x, mouse_pos_y = mouse.position
    aims_copy = aims.copy()
    # 取消瞄准的范围设置
    # detect_arange = args.detect_arange  # 範圍可自行調整
    # print("(len_x * float(x[1]) + top_x - mouse_pos_x) ** 2 + (len_y * float(x[2]) + top_y - mouse_pos_y) ** 2---",
    # (len_x * float(aims_copy[1]) + top_x - mouse_pos_x) ** 2 + (len_y * float(aims_copy[2]) + top_y - mouse_pos_y)
    # ** 2) 取消瞄准的范围设置 aims_copy = [x for x in aims_copy if x[0] in args.lock_choice and (len_x * float(x[1]) + top_x
    # - mouse_pos_x) ** 2 + (len_y * float(x[2]) + top_y - mouse_pos_y) ** 2 < detect_arange] k = 1 * (1 /
    # args.lock_smooth)
    if len(aims_copy):
        dist_list = []
        for det in aims_copy:
            _, x_c, y_c, _, _ = det
            dist = (len_x * float(x_c) + top_x - mouse_pos_x) ** 2 + (len_y * float(y_c) + top_y - mouse_pos_y) ** 2
            print("dist", dist)
            dist_list.append(dist)

        if dist_list:
            det = aims_copy[dist_list.index(min(dist_list))]
            tag, x_center, y_center, width, height = det
            x_center, width = len_x * float(x_center) + top_x, len_x * float(width)
            y_center, height = len_y * float(y_center) + top_y, len_y * float(height)
            # rel_x = int(k / args.lock_sen * atan((mouse_pos_x - x_center) / 640) * 640)
            rel_x = -(mouse_pos_x - x_center) * args.lock_smooth
            rel_y = -(mouse_pos_y - y_center + args.head_to_foot / 10.0 * height / 2) * args.lock_smooth
            # rel_y = int(k / args.lock_sen * atan((mouse_pos_y - y_center + 1 / 4 * height) / 640) * 640)#瞄準高度可自行調整(建議為1/4)
            # pid_movex = pidx(rel_x)
            # pid_movey = pidy(rel_y)
            # print(pid_movex, pid_movey)
            # ghub.mouse_xy(round(pid_movex), round(pid_movey))
            print(rel_x, rel_y)
            if abs(mouse_pos_x - x_center) > 5 or abs(mouse_pos_y - y_center) > 5:
                ghub.mouse_xy(round(rel_x), round(rel_y))
                print('move mouse  ...', mouse_pos_x - x_center)


count = 0  # 频率控制


def show_fps(cv2, lock_mode, team_mode, img0, t0):
    global count
    count = count + 1

    cv2.putText(img0, "FPS:{:.1f}".format(1. / (time.time() - t0)), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (27, 0, 221), 2)
    cv2.putText(img0, "lock:{:.1f}".format(lock_mode), (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (27, 0, 221),
                2)
    # cv2.putText(img0, "team:{:.1f}".format(team_mode), (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (27, 0, 221),
    #             2)
    # 打印fps 控制频率
    if int(count) % 100 == 0:
        print(1. / (time.time() - t0))
        count = 0

    cv2.imshow('aim', img0)


def show_top_most():
    hwnd = win32gui.FindWindow(None, 'aim')
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
