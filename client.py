from PyQt5.QtWidgets import QPushButton, QWidget, QLCDNumber, QLabel
from PyQt5.QtCore import QTimer, QRect
from PyQt5.QtNetwork import QTcpServer,QHostAddress
import json
import socket


class ClientPanel(QWidget):
    def __init__(self,number):
        super().__init__()
        self.setWindowTitle(str(number))
        self.setMinimumSize(400, 300)
        self.setMaximumSize(400, 300)
        self.tarTemperaturetxt = QLabel("目标温度:", self)
        self.tarTemperaturetxt.move(10, 10)
        self.tarTemperaturelab = QLCDNumber(self)
        self.tarTemperaturelab.move(40, 40)
        self.tarTemperaturelab.setMaximumSize(100, 80)
        self.tarTemperaturelab.setMinimumSize(100, 80)
        self.tarTemperaturelab.setDigitCount(2)
        self.tarTemperaturelab.setSegmentStyle(QLCDNumber.Flat)
        self.tarTemperaturelab.setStyleSheet("border:5px black; color: red; background: blue; ")
        self.tarTemperature = 0
        self.mode = 'warm'
        self.frequency = 0
        self.roomid = ""
        self.curTemperaturetxt = QLabel("房间温度:", self)
        self.curTemperaturetxt.move(10, 140)
        self.curTemperaturelab = QLCDNumber(self)
        self.curTemperaturelab.move(40, 170)
        self.curTemperaturelab.setMaximumSize(100, 80)
        self.curTemperaturelab.setMinimumSize(100, 80)
        self.curTemperaturelab.setDigitCount(2)
        self.curTemperaturelab.setSegmentStyle(QLCDNumber.Flat)
        self.curTemperaturelab.setStyleSheet("border:5px black; color: red; background: blue; ")
        self.curTemperature = 25.0
        self.curTemperaturelab.display(str(int(round(self.curTemperature, 0))))

        self.addButton = QPushButton('+', self)
        self.addButton.move(280, 80)
        self.minusButton = QPushButton('-', self)
        self.minusButton.move(180, 80)
        self.changetem = 0
        self.buttonTimer = QTimer(self)
        self.buttonTimer.setInterval(1000)
        self.isClick = False
        self.addButton.clicked.connect(self.add_func)
        self.minusButton.clicked.connect(self.minus_func)
        self.buttonTimer.timeout.connect(self.opTempPanel)

        self.level = '中风'
        self.levelPanel = QLabel(self.level, self)
        self.levelPanel.setMaximumSize(100, 20)
        self.levelPanel.setMinimumSize(100, 20)
        self.levelPanel.move(260, 10)
        self.llevel = QPushButton('低', self)
        self.llevel.setMaximumWidth(30)
        self.llevel.setMinimumWidth(30)
        self.llevel.move(200, 45)
        self.llevel.clicked.connect(self.llevelFun)
        self.mlevel = QPushButton('中', self)
        self.mlevel.setMaximumWidth(30)
        self.mlevel.setMinimumWidth(30)
        self.mlevel.move(260, 45)
        self.mlevel.clicked.connect(self.mlevelFun)
        self.hlevel = QPushButton('高', self)
        self.hlevel.setMaximumWidth(30)
        self.hlevel.setMinimumWidth(30)
        self.hlevel.move(320, 45)
        self.hlevel.clicked.connect(self.hlevelFun)

        self.nowindTimer = QTimer(self)
        self.nowindTimer.setInterval(1000)
        self.nowindTimer.timeout.connect(self.SendWindRequest)

        self.sendwindTimer = QTimer(self)
        self.sendwindTimer.setInterval(1000)
        self.sendwindTimer.timeout.connect(self.EndSendWindRequest)

        self.CostThread = QTimer(self)  # 更新能耗的线程
        self.CostThread.timeout.connect(self.changeCost)

        self.Energy = QLabel('耗能：', self)
        self.Energy.setGeometry(QRect(200, 170, 60, 20))
        self.EnergyText = QLabel('0.0', self)
        self.EnergyText.setGeometry(QRect(280, 170, 100, 20))
        self.Money = QLabel('花费：', self)
        self.Money.setGeometry(QRect(200, 210, 60, 20))
        self.MoneyText = QLabel('0.0', self)
        self.MoneyText.setGeometry(QRect(280, 210, 100, 20))

        self.shutdownbutton = QPushButton('关机', self)
        self.shutdownbutton.move(230, 240)
        self.shutdownbutton.clicked.connect(self.shutdownFun)

        self.modelabel = QLabel('warm', self)
        self.modelabel.move(200, 140)

        self.statelabel = QLabel('送风关', self)
        self.statelabel.move(280, 140)

        self.StopThread = QTcpServer()
        self.StopThread.listen(QHostAddress.Any,6660+int(number))
        self.StopThread.newConnection.connect(self.termisendwind)
        #self.StopThread.start()

    def termisendwind(self):
        print(1)
        self.sendwindTimer.stop()
        self.nowindTimer.start()
        self.statelabel.setText("送风关")
        self.update()
        print(2)

    def changeCost(self):  # 更新能耗的界面
        print(3)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", 5553))
        print(1000)
        currentmsg = {'roomid': self.roomid, "cur_temp": str(self.curTemperature)}
        jsoncurrentmsg = json.dumps(currentmsg)
        client.send(jsoncurrentmsg.encode(encoding="utf-8"))
        ret = client.recv(1024).decode()
        print(2000)
        retData = json.loads(ret)
        cost = retData["energy"]
        cost = float(cost)
        client.close()
        self.EnergyText.setText(str(round(cost, 1)))
        self.MoneyText.setText(str(round(cost * 5, 1)))
        self.update()
        print(4)

    def EndSendWindRequest(self):
        print(5)
        if self.mode == 'warm':
            if self.level == '中风':
                self.curTemperature += 0.05
            elif self.level == '低风':
                self.curTemperature += 0.04
            elif self.level == '高风':
                self.curTemperature += 0.2 / 3

            if self.curTemperature >= self.tarTemperature:  # 达到目标温度，下面同理和sever通信请求停止送风
                try:
                    # 结束送风请求端口
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect(("127.0.0.1", 5557))
                    endsendwindrequest = {'roomid': self.roomid, "cur_temp": str(self.curTemperature),
                                          'target_temp': str(self.tarTemperature)}
                    print(endsendwindrequest)
                    jsonendsendwindrequest = json.dumps(endsendwindrequest)
                    client.send(jsonendsendwindrequest.encode(encoding="utf-8"))
                    ret = client.recv(1024).decode()
                    if ret == 'Ok':
                        self.nowindTimer.start()
                        self.sendwindTimer.stop()
                        self.statelabel.setText("送风关")
                    client.close()
                except:
                    pass
        elif self.mode == 'cold':
            if self.level == '中风':
                self.curTemperature -= 0.05
            elif self.level == '低风':
                self.curTemperature -= 0.04
            elif self.level == '高风':
                self.curTemperature -= 0.2 / 3
            if self.curTemperature <= self.tarTemperature:
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect(("127.0.0.1", 5557))
                    endsendwindrequest = {'roomid': self.roomid, "cur_temp": str(self.curTemperature),
                                          'target_temp': str(self.tarTemperature), }
                    print(endsendwindrequest)
                    jsonendsendwindrequest = json.dumps(endsendwindrequest)
                    client.send(jsonendsendwindrequest.encode(encoding="utf-8"))
                    ret = client.recv(1024).decode()
                    if ret == 'Ok':

                        self.nowindTimer.start()
                        self.statelabel.setText("送风关")
                        self.sendwindTimer.stop()
                    client.close()
                except:
                    pass
        self.curTemperaturelab.display(str(int(round(self.curTemperature, 0))))
        self.update()
        print(6)

    def SendWindRequest(self):
        print(7)
        if self.mode == 'warm':
            self.curTemperature -= 0.1
            if self.curTemperature + 1 <= self.tarTemperature:  # 满足送风条件，下面同理，和sever通信请求送风
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect(("127.0.0.1", 5556))
                    sendwindrequest = {'level': self.level, "cur_temp": str(self.curTemperature),
                                       'target_temp': str(self.tarTemperature), 'roomid': self.roomid}
                    print(sendwindrequest)
                    jsonsendwindrequest = json.dumps(sendwindrequest)
                    client.send(jsonsendwindrequest.encode(encoding="utf-8"))
                    ret = client.recv(1024).decode()

                    if ret == 'Ok':
                        self.nowindTimer.stop()
                        self.statelabel.setText("送风开")
                        self.sendwindTimer.start()
                        self.Stopthread.start()

                    else:
                        pass
                    client.close()
                except:
                    pass
        elif self.mode == 'cold':
            self.curTemperature += 0.1
            if self.curTemperature - 1 >= self.tarTemperature:
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect(("127.0.0.1", 5556))
                    sendwindrequest = {'level': self.level, "cur_temp": str(self.curTemperature),
                                       'target_temp': str(self.tarTemperature), 'roomid': self.roomid}
                    print(sendwindrequest)
                    jsonsendwindrequest = json.dumps(sendwindrequest)
                    client.send(jsonsendwindrequest.encode(encoding="utf-8"))
                    ret = client.recv(1024).decode()

                    if ret == 'Ok':
                        self.nowindTimer.stop()
                        self.statelabel.setText("送风开")
                        self.sendwindTimer.start()
                        self.Stopthread.start()
                    else:
                        pass
                    client.close()
                except:
                    pass
        self.curTemperaturelab.display(str(int(round(self.curTemperature, 0))))
        self.update()
        print(8)

    def add_func(self):
        print(9)
        if self.isClick:
            self.changetem += 1
        else:
            self.isClick = True
            self.buttonTimer.start()
            self.changetem += 1
        print(10)

    def minus_func(self):
        print(11)
        if self.isClick:
            self.changetem -= 1
        else:
            self.isClick = True
            self.buttonTimer.start()
            self.changetem -= 1
        print(12)

    def opTempPanel(self):
        print(13)
        self.isClick = False
        self.tarTemperature = self.tarTemperature + self.changetem
        self.changetem = 0
        if self.mode == 'cold':
            if self.tarTemperature < 18:
                self.tarTemperature = 18
            elif self.tarTemperature > 25:
                self.tarTemperature = 25
        elif self.mode == 'warm':
            if self.tarTemperature < 25:
                self.tarTemperature = 25
            elif self.tarTemperature > 30:
                self.tarTemperature = 30
        self.tarTemperaturelab.display(str(self.tarTemperature))
        self.update()
        self.buttonTimer.stop()
        print(14)

    def llevelFun(self):
        print(15)
        level = '低风'
        self.level = level
        self.levelPanel.setText(self.level)
        self.requestForLevelChange()
        self.update()
        print(16)

    def mlevelFun(self):
        print(17)
        level = '中风'
        self.level = level
        self.levelPanel.setText(self.level)
        self.requestForLevelChange()
        self.update()
        print(18)

    def hlevelFun(self):
        print(19)
        level = '高风'
        self.level = level
        self.levelPanel.setText(self.level)
        print(33)
        self.requestForLevelChange()
        self.update()
        print(20)

    # 改变风速请求
    def requestForLevelChange(self):
        print(21)
        if self.mode == 'warm':
            if self.curTemperature + 1 <= self.tarTemperature:  # 满足送风条件，下面同理，和sever通信请求送风
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect(("127.0.0.1", 5556))
                    sendwindrequest = {'level': self.level, "cur_temp": str(self.curTemperature),
                                       'target_temp': str(self.tarTemperature),
                                       'roomid': self.roomid}
                    jsonsendwindrequest = json.dumps(sendwindrequest)
                    client.send(jsonsendwindrequest.encode(encoding="utf-8"))
                    ret = client.recv(1024).decode()
                    if ret == 'Ok':
                        self.statelabel.setText("送风开")
                    else:
                        self.statelabel.setText("送风关")

                    client.close()
                except:
                    pass
        elif self.mode == 'cold':
            if self.curTemperature - 1 >= self.tarTemperature:
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.connect(("127.0.0.1", 5556))
                    sendwindrequest = {'level': self.level, "cur_temp": str(self.curTemperature),
                                       'target_temp': str(self.tarTemperature),
                                       'roomid': self.roomid}
                    jsonsendwindrequest = json.dumps(sendwindrequest)
                    client.send(jsonsendwindrequest.encode(encoding="utf-8"))
                    ret = client.recv(1024).decode()
                    if ret == 'Ok':
                        self.statelabel.setText("送风开")
                    else:
                        self.statelabel.setText("送风关")
                    client.close()
                except:
                    pass
        print(22)
    def shutdownFun(self):
        print(23)
        logoutmsg = {'roomid': self.roomid, "cur_temp": str(self.curTemperature),
                     'target_temp': str(self.tarTemperature)}
        logoutjson = json.dumps(logoutmsg)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", 5554))
        client.send(logoutjson.encode(encoding="utf-8"))
        ret = client.recv(1024).decode()
        if ret == 'Ok':
            self.previouswidget.show()
            self.hide()
        client.close()
        print(24)