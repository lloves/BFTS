#coding=utf-8

"""
Date:20191010
Function: 稳定性测试
"""

import os
import sys
import threading
import time
import random
from threading import Timer
from com.android.monkeyrunner import MonkeyRunner as MR
from com.android.monkeyrunner import MonkeyDevice as MD
from java.net import SocketException
from com.android.ddmlib import TimeoutException

import inspect
import ctypes

class StableTest(object):
    def __init__(self, mIp, mPort):
        self.ip = mIp
        self.port = mPort
    # 这一步需要单独列出来，增加一个点击按钮，不断刷新，直到全部的设备识别成功
    def connect2Device(self):
        connectCmd = "adb connect " + self.ip + ":" + self.port
        os.system(connectCmd)
        return

class Tools():
    def __init__(self):
        return

    def getdeviceSerial(self):
        # print("获取所有的devices，并返回devices[]")
        # 创建一个数组用来存放devices
        devices = []
        # 将所有的devices 写入devicesList.txt
        # devicesPath = str(os.getcwd())
        os.system("adb devices > " + "devicesList.txt")
        # 读取devices.text
        f = open("devicesList.txt", "r")
        content = f.readlines()
        i = 1  # 因为第一行没有device的信息 所以下标从1开始，而且最后一行空白的所以i要小于len-1
        # print(len(content))
        while i < len(content)-1:
            # 找到空格的位置或者有时识别不出空客 用device
            # findNumber = content[i].find(" ")
            findNumber = content[i].find("device")-1
            # print(findNumber)
            # 截取空格之前的字符串保存到devices[]
            devices.append(content[i][0:findNumber])
            i += 1
        f.close()
        # 读取所有的devices
        # for device in devices:
        #     print(device)
        return devices

    def getAppList(self):
        apps = []
        # 读取AppList.txt
        f = open("AppList.txt", "r")
        content = f.readlines()
        print(content)
        i = 0  # 因为第一行没有device的信息 所以下标从1开始，而且最后一行空白的所以i要小于len-1
        # print(len(content))
        while i < len(content):
            # 找到空格的位置或者有时识别不出空客 用device
            # findNumber = content[i].find(" ")
            app = content[i]
            # print("app: ", app)
            # 字符串保存到apps[]
            apps.append(content[i])
            i += 1
        f.close()
        return apps

    # 读取devices.txt配置文件，此文件包含局域网内被测试机器上报上来的ip和端口号
    def getDeviceIpAndPortList(self):
        deviceIpAndPortList = []

        if not os.path.exists("devices.txt"):
            return deviceIpAndPortList

        f = open("devices.txt", "r")
        content = f.readlines()
        i = 0
        while i < len(content):
            ip = content[i].split(" ")[0]
            port = content[i].split(" ")[1]
            deviceIpAndPortList.append((ip, port))
            i += 1
        f.close()

        return deviceIpAndPortList

    def _async_raise(tid, exctype):
        """raises the exception, performs cleanup if needed"""
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def stop_thread(thread):
        _async_raise(thread.ident, SystemExit)


class StableTestThread(threading.Thread):
    def __init__(self, deviceSerial):
        threading.Thread.__init__(self)
        self.deviceSerial = deviceSerial
        self.device = MR.waitForConnection(5.0, self.deviceSerial)

        self.keyCodes = ['KEYCODE_HOME', 'KEYCODE_BACK', 'KEYCODE_DPAD_DOWN', 'KEYCODE_DPAD_UP', 'KEYCODE_DPAD_CENTER', 'KEYCODE_DPAD_LEFT', 'KEYCODE_DPAD_RIGHT']
        t = Tools()
        self.apps = t.getAppList()
        self.appIndex = 0
        self.cutApp = False

    def cutTestApp(self):
        self.randomIndex = random.randint(0, len(self.apps) - 1)
        print("App " + self.apps[self.randomIndex] + " Will be test.")
        self.cutApp = True


    def run(self):
        if __name__ == '__main__':
            print(self.deviceSerial)
            size = len(self.keyCodes)
            # Timer(60*5, self.cutTestApp).start()

            while True:
                # 如果定时超过5分钟，切换一个APP列表中的其他app测试
                if self.cutApp:
                    self.device.startActivity(self.apps[randomIndex])
                    self.cutApp = False

                randomIndex = random.randint(0, size-1)
                print("Key code :", self.keyCodes[randomIndex])
                try:
                    self.device.press(self.keyCodes[randomIndex], MD.DOWN_AND_UP)
                    MR.sleep(1)
                    posX = random.randint(0, 1280)
                    posY = random.randint(0, 720)
                    self.device.touch(posX, posY, "DOWN_AND_UP")
                except (SocketException):
                    print("send keycode error.")
                MR.sleep(1)

"""
def restartThread(threads):
    print("restart thread.")
    try:
        for t in threads:
            t.join()

        MR.sleep(5)

        for t in threads:
            MR.sleep(1)
            t.start()
    except:
        print("重启稳定性测试线程失败")
"""


if __name__ == "__main__":
    print("开始稳定性测试...")
    # s = StableTest("192.168.199.59", "5556")
    # s.connect2Device()
    os.system("adb disconnect")

    t = Tools()
    # 遍历使用 adb connect 连接所有的机器，为MonketRunner测试做准备
    devIpAndPortList = t.getDeviceIpAndPortList()
    for item in devIpAndPortList:
        print(item)
        s = StableTest(item[0], item[1])
        s.connect2Device()

    devicesSerial = t.getdeviceSerial()

    # 线程组
    tt = []

    try:
        for deviceSerial in devicesSerial:
            thread = StableTestThread(deviceSerial)
            tt.append(thread)

        for t in tt:
            t.start()
            MR.sleep(5)

        for t in tt:
            t.join()

    except Exception:
        print("线程启动失败")


