#coding=utf-8
from socket import *
import os, sys
import _thread as thread
import threading
import time
from threading import Timer
import wx
from wx.lib.pubsub import pub
# from wx.lib.pubsub import Publisher

class BFTS:

    LOCAL_ADDRESS = ''
    SOCKET_PORT = 9001
    tcpSocket = None
    udpSocket = None
    cmdStr = ''
    portList = []
    currentPort = 5556

    def __init__(self):
        # 创建socket套接字
        self.tcpSocket = socket(AF_INET, SOCK_STREAM)
        self.LOCAL_ADDRESS = self.getHostIp()

        # 绑定相关信息，如果一个网络程序不绑定，则系统会随机分配
        bindAddress = (self.LOCAL_ADDRESS, self.SOCKET_PORT)
        self.tcpSocket.bind(bindAddress)
        self.tcpSocket.listen(5)
        self.udpSocket = socket(AF_INET, SOCK_DGRAM)

        # 如果存在设备列表(devices.txt)则删除
        if os.path.exists("devices.txt"):
            os.remove("devices.txt")


    # 发送UDP广播，发送服务端IP到局域网唤醒下位机，使下位机与服务端建立连接。
    def sendBroadcastWakeTest(self):
        print('Start broadcast thread.')
        while True:
            # 捕获异常，避免在网络不可用的时候广播线程中断，新机器无法连接
            try:
                self.udpSocket = socket(AF_INET, SOCK_DGRAM)
                # send broadcast address must set as below.
                self.udpSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
                sendAddress = ('255.255.255.255', 9002)
                sendData = self.getHostIp() #input("please input content:")
                self.udpSocket.sendto(sendData.encode(), sendAddress)
            except:
                print("Network error.", "Broadcast maybe reboot.")

            time.sleep(5)
        self.udpSocket.close()


    # 服务端TCP连接，监听下位机发送上来的信息，统计下位机数量、ip等信息，下发测试指令
    def startListenClient(self):
        while True:
            print("Start test server.")
            client_socket, client_addr = self.tcpSocket.accept()
            print('New clinet is ready', client_addr)

            self.portList.append(self.currentPort)
            tempBoxInfo = client_addr[0] + " " + str(self.currentPort) + " " + "1234567890123\n"
            self.saveBoxInfo2File(tempBoxInfo, "devices.txt")
            self.currentPort = self.currentPort + 1

            box = BoxInfo(client_addr, "1234567890123", "0", "0")
            # 传递的消息是字符串，而不能是一个对象
            wx.CallAfter(pub.sendMessage, "update", newDevInfo = client_addr[0] + "|" + "1234567890123" + "|"+ "0" + "|" + "0")

            # 重启客户端的adbd服务，指定不同的adb端口
            self.cmdStr = "setprop service.adb.tcp.port " + str(self.currentPort - 1) + " & stop adbd & start adbd"
            cmd = '{"cmdId":1002, "cmdStr": "' + self.cmdStr + '", "cmdParam": "123"}'
            print("send to client: ", cmd)
            # client_socket.send('{"cmdId":1002, "cmdStr": "mkdir /mnt/sdcard/BFTS1", "cmdParam": "123"}'.encode())
            client_socket.send(cmd.encode())
            client_socket.close()
        self.tcpSocket.close()



    def sendBroadCastToClient(self):
        cmd = '{"cmdId":1000, "cmdStr": "' + self.cmdStr + '", "cmdParam": "123"}'
        print(cmd)
        times = 0
        while times < 1:
            # 捕获异常，避免在网络不可用的时候广播线程中断，新机器无法连接
            try:
                sendAddress = ('255.255.255.255', 9002)
                self.udpSocket.sendto(cmd.encode(), sendAddress)
            except:
                print("send cmd error .....................")

            # time.sleep(2)
            times = times + 1



    # 启动一个log上传的FTP服务器
    def startFtpServer(self):
        return

    def start(self):
        broadcastThread = threading.Thread(name='1001', target=self.sendBroadcastWakeTest)
        listenThread = threading.Thread(name='1002', target=self.startListenClient)
        broadcastThread.start()
        listenThread.start()

        #broadcastThread().join()
        #listenThread().join()

    def deinit(self):
        self.udpSocket.close()
        self.tcpSocket.close()

    def getHostIp(self):
        try:
            s = socket(AF_INET, SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except:
            return ""
        finally:
            s.close()
        return ip

    def setCmdStr(self, cmdStr):
        self.cmdStr = cmdStr

    def saveBoxInfo2File(self, boxInfo, fileName):
        fp = open(fileName, "a")
        fp.write(boxInfo)
        fp.close()

class BoxInfo:
    # 机顶盒的IP信息
    ip = None
    # 机顶盒的SN信息
    sn = None
    # 目前的执行的测试是什么<Monkey, VDK, CTS>
    testItem = None
    # 测试状态 <测试中、测试成功、测试失败>
    testStatus = None

    def __init__(self, ip, sn, testItem, testStatus):
        self.ip = ip
        self.sn = sn
        self.testItem = testItem
        self.testStatus = testStatus


class MainWindow(wx.Frame):
    mBoxDevList = []
    bfts = None

    def __init__(self, parent, title):
        super(MainWindow, self).__init__(parent, title = title,size = (800, 600))

        os.system("adb disconnect")

        self.bfts = BFTS()
        self.bfts.start()
        Timer(60, self.moniterMachineStatus).start()

        panel = wx.Panel(self)
        # box = wx.BoxSizer(wx.HORIZONTAL)

        # 命令输入Dialog
        self.cmdTextArea = wx.TextCtrl(panel, value = u"请输入下发给下位机的命令", size = (600, 60), style = wx.TE_MULTILINE)
        self.startButton = wx.Button(panel, size = (-1, 60), label = u"下发新命令")
        self.stableTestButton = wx.Button(panel, size = (-1, 60), label = u"稳定性测试")
        hbox1 = wx.BoxSizer()
        hbox1.Add(self.cmdTextArea, proportion = 0, flag = wx.EXPAND)
        hbox1.Add(self.startButton, proportion = 0, flag = wx.LEFT, border = 5)
        hbox1.Add(self.stableTestButton, proportion = 0, flag = wx.LEFT, border = 5)

        self.startButton.Bind(wx.EVT_BUTTON, self.startService)
        self.stableTestButton.Bind(wx.EVT_BUTTON, self.startStableThread)


        self.label1 = wx.StaticText(panel, -1, size = (350, -1), style = wx.ALIGN_LEFT)
        self.label1.SetLabel("[机器信息 - 列表]")
        self.label2 = wx.StaticText(panel, -1, style = wx.ALIGN_RIGHT)
        self.label2.SetLabel("[详细信息 - 状态]")

        hbox2 = wx.BoxSizer()
        hbox2.Add(self.label1, proportion = 0, flag = wx.LEFT, border = 5)
        hbox2.Add(self.label2, proportion = 0, flag = wx.EXPAND)

        # 机器列表
        self.text = wx.TextCtrl(panel, size = (450, 450), style = wx.TE_MULTILINE)
        self.listBox = wx.ListBox(panel,  choices = [], size = (350, 450), style = wx.LB_SINGLE)
        hbox3 = wx.BoxSizer()
        hbox3.Add(self.listBox, proportion = 0, flag = wx.EXPAND)
        hbox3.Add(self.text, proportion = 0, flag = wx.LEFT, border = 5)

        # 组合布局
        vbox = wx.BoxSizer(wx.VERTICAL)
        # vbox = wx.BoxSizer(wx.HORIZONTAL | wx.VERTICAL)
        vbox.Add(hbox1, proportion = 0, flag = wx.EXPAND | wx.ALL, border = 5)
        vbox.Add(hbox2, proportion = 0, flag = wx.EXPAND | wx.ALL, border = 5)
        vbox.Add(hbox3, proportion = 0, flag = wx.EXPAND | wx.ALL, border = 5)

        #box.Add(self.listBox, 0, wx.EXPAND)
        #box.Add(self.text, 1, wx.EXPAND)

        panel.SetSizer(vbox)
        panel.Fit()

        # 注册一个监控，更新UI
        pub.subscribe(self.refreshUI, "update")

        # 点击左侧机器列表中机器信息，右侧同步更新.
        self.Centre()
        self.Bind(wx.EVT_LISTBOX, self.onListBox, self.listBox)

        self.Show(True)

    def updateBoxList(self, boxInfo):
        self.mBoxDevList.append(boxInfo)


    def getAdbConnectedDevices(self):
        # print("获取所有的devices，并返回devices[]")
        # 创建一个数组用来存放devices
        devices = []
        # 将所有的devices 写入devicesList.txt
        # devicesPath = str(os.getcwd())
        os.system("adb devices > " + "devicesList1.txt")
        # 读取devices.text
        f = open("devicesList1.txt", "r")
        content = f.readlines()
        i = 1  # 因为第一行没有device的信息 所以下标从1开始，而且最后一行空白的所以i要小于len-1
        # print(len(content))
        while i < len(content)-1:
            # 找到空格的位置或者有时识别不出空客 用device
            # findNumber = content[i].find(" ")
            findNumber = content[i].find("device")-1
            # print(findNumber)
            # 截取空格之前的字符串保存到devices[]
            devices.append(content[i][0:findNumber].split(":")[0])
            i += 1
        f.close()
        # 读取所有的devices
        # for device in devices:
        #     print(device)
        return devices


    def getdeviceSerial(self):
        devices = []
        file = open('devices.txt')
        for line in file:
            ip = line.strip('\n').split(' ')[0]
            if ip not in devices:
                devices.append(ip)
        return devices

    def refreshUI(self, newDevInfo):

        devIpList = []
        # infoList = newDevInfo.split("|")
        # boxInfo = BoxInfo(infoList[0], infoList[1], infoList[2], infoList[3])
        # self.mBoxDevList.append(boxInfo)
        cIndex = 0
        # boxLis中设备重复，需要根据ip去重
        # flag = 0
        # for devItem in self.mBoxDevList:
        #    if devItem.ip
        """
        # print(set(self.mBoxDevList))
        #for item in list(set(self.mBoxDevList)):
        #    cIndex = cIndex + 1
        #    devIpList.append( str(cIndex) + " 机顶盒 - " + item.ip)
        # boxIpList.append('机顶盒 - ' + boxInfo.split("|")[0])
        # 有序，不重复
        # list(set(boxIpList)).sort(key=boxIpList.index)
        # UI 更新
        """
        #self.listBox.Set(list(set(devIpList)))
        adb_connect_devices = self.getAdbConnectedDevices()

        for item in self.getdeviceSerial():
            cIndex = cIndex + 1
            if item in adb_connect_devices:
                devIpList.append( str(cIndex) + " 机顶盒 - " + item + " : ADB状态 已连接")
            else:
                devIpList.append( str(cIndex) + " 机顶盒 - " + item + " : ADB状态 未连接")

        self.listBox.Set(devIpList)

    def moniterMachineStatus(self):
        print("Moniter machine status.")
        self.refreshUI(" ")
        Timer(60, self.moniterMachineStatus).start()

    def onListBox(self, event):
        self.text.AppendText( "Current selection:"
            + event.GetEventObject().GetStringSelection()+"\n")


    def startService(self, event):
        print(self.cmdTextArea.GetValue())
        self.bfts.setCmdStr(self.cmdTextArea.GetValue())
        # 这里还可以修改为服务端变成客户端，请求机顶盒建立TCP链接，下发指令的方式
        cmdThread = threading.Thread(name='1003', target=self.bfts.sendBroadCastToClient)
        cmdThread.start()
        # self.sendBroadCastToClient(self.bfts.cmdStr)
        # 定义一个设备标记位列表，可以根据选择的设备，给特定设备下发特定的指令，比如设置ip地址、重启等操作

    def startStableThread(self, event):
        broadcastThread = threading.Thread(name='stable test', target=self.startStableTest)
        broadcastThread.start()
        # print("Stable thread id ", broadcastThread)

    def startStableTest(self):
        print("Start table test.")
        cmd = '''kill -9 `ps -aux | grep "./android-sdk-linux/tools/monkeyrunner" | awk '{print $2}'`'''
        while True:
            os.system('./android-sdk-linux/tools/monkeyrunner StableTest.py')
            time.sleep(60)
            print("restart test thread")
            os.system(cmd)
            time.sleep(2)

if __name__ == "__main__":
    # bfts = BFTS()
    # bfts.start()

    ex = wx.App()
    MainWindow(None, "基础固件测试上位机-v0.9.1")
    ex.MainLoop()

    """
    app = wx.App()
    version = '0.5.0'
    window = wx.Frame(None, title = "基础固件测试上位机-" + version, size = (800,600))
    listView = wx.ListView(window)
    label = wx.StaticText(listView, label = "Hello World", pos = (100,100))
    window.Show(True)
    app.MainLoop()
    """

