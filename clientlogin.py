import sys
import json
from PyQt5.QtWidgets import QPushButton, QApplication, QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from client import ClientPanel
import socket


class LoginWindow(QWidget):  # 登陆窗口
    def __init__(self,number):
        super().__init__()
        self.setWindowTitle(str(number))
        self.setMinimumSize(400, 300)
        self.setMaximumSize(400, 300)
        sum = QVBoxLayout(self)
        self.roomId = QLabel("房间号")
        self.roomIdText = QLineEdit()
        self.personId = QLabel("身份证号")
        self.personIdText = QLineEdit()
        self.hint = QLabel(self)
        self.hint.setMinimumSize(300, 40)
        self.hint.setMaximumSize(300, 40)
        self.hint.move(70,220)
        # L2 = QHBoxLayout(self)
        # L2.addWidget(self.presonId)
        # L2.addWidget(self.presonIdText)
        # sum.addLayout(L2)
        L1 = QHBoxLayout()
        L1.addWidget(self.roomId)
        L1.addWidget(self.roomIdText)
        L1.addWidget(self.personId)
        L1.addWidget(self.personIdText)
        sum.addLayout(L1)
        self.login = QPushButton("登陆")
        sum.addWidget(self.login)
        self.setLayout(sum)
        self.nextwiget = ClientPanel(number)
        self.login.clicked.connect(self.btn_login_fuc)  # 登陆按钮点击触发登陆事件

    def btn_login_fuc(self):
        connect = False
        while not connect:
            try:
                dbConnection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                dbConnection.connect(("127.0.0.1", 5555))
                connect = True
                loginmsg = {'roomid': self.roomIdText.text(), 'personid': self.personIdText.text()}
                loginjson = json.dumps(loginmsg)
                dbConnection.send(loginjson.encode(encoding="utf-8"))
                rcv = dbConnection.recv(1024).decode()  # 和sever进行通信验证数据库中信息是否正确


                if rcv == 'Success':  # 登陆成功
                    workmode = dbConnection.recv(1024).decode()
                    print(workmode)
                    workmodetext = json.loads(workmode)
                    self.nextwiget.mode = workmodetext['mode']
                    self.nextwiget.tarTemperature = int(workmodetext['default'])
                    self.nextwiget.frequency =int(workmodetext['frequency'])
                    self.nextwiget.modelabel.setText(self.nextwiget.mode)
                    self.nextwiget.tarTemperaturelab.display(str(self.nextwiget.tarTemperature))
                    self.nextwiget.nowindTimer.start()  # 从控机未开启是环境温度的变化
                # 能耗线程
                    self.nextwiget.CostThread.start(self.nextwiget.frequency)
                    self.nextwiget.roomid = self.roomIdText.text()
                    self.nextwiget.previouswidget = self
                    self.nextwiget.show()
                    print(1)
                    self.hint.clear()
                    self.hide()
                else:
                    self.hint.setText('Incorrect room id or person id')
                    self.update()
                dbConnection.close()
                self.roomIdText.clear()
                self.personIdText.clear()
                print(1)

            except:
                self.hint.setText('no connect and try connect')
                self.update()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    print('请输入第几号控机：')
    number = int(input())
    b = LoginWindow(number)
    b.show()
    sys.exit(app.exec_())
