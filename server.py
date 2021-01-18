#!/usr/bin/python3
# -*-coding:utf-8 -*-
import socket
import time
import threading
import pymysql
import sys
import json
from PyQt5.QtWidgets import QPushButton, QApplication, QLineEdit, QTextEdit, QWidget, QLabel
from PyQt5.QtCore import QTimer

LOGIN_FAILED = 0
AIR_MANAGER = 1
ACCOUNTTING = 2

COD = 'utf-8'
HOST = '0.0.0.0'  # 主机ip
PORT = 21566  # 软件端口号
BUFSIZ = 1024
ADDR = (HOST, PORT)
ROOM_SIZE = 5
CONN_SIZE = 3

WORKING = 0
WAITING = 1
IDLE = 2


class CenterSys:
    def __init__(self, mode=0, fq=1000):
        self.mode_list = ['cold', 'warm']
        self.default_temp_list = [22, 28]  # chill:22,warm:28
        self.range_list = [(18, 25), (25, 30)]  # temperature range:chill=18,25;warm=25,30

        self.mode = mode  # 0:chill 1: warm
        self.default_temp = self.default_temp_list[mode]
        self.range = self.range_list[mode]

        self.frequency = fq  # one update per x seconds
        self.conn_count = 3  # max request

        self.energy_post = [0.0] * ROOM_SIZE  # 前次已完成的温控使用的电
        self.energy_now = [0.0] * ROOM_SIZE  # 本次还未完成的温控已经使用的电
        self.last_request_time = [-1.0] * ROOM_SIZE
        self.last_level = [''] * ROOM_SIZE
        self.login_activate = [False] * ROOM_SIZE
        self.working = [IDLE] * ROOM_SIZE  # 送风状态

        self.cur_temp = [0.0] * ROOM_SIZE

        self.slave_ip = [6660, 6661, 6662, 6663, 6664]  # 从控机等待监听端口

    def login_ini(self, roomid):  # 初始化耗电计算

        self.energy_post[roomid] = 0.0  # 记录每一次登录的电
        self.energy_now[roomid] = 0.0  # 记录每一次温控的电
        self.last_request_time[roomid] = -1.0  # 浮点秒数时间戳
        self.last_level[roomid] = ''
        self.login_activate[roomid] = True

    def logout(self, roomid):  # 从控机关机
        energy_now_ = self.energy_archive(roomid)
        self.energy_post[roomid] = 0.0
        self.login_activate[roomid] = False
        return energy_now_

    def energy_add(self, roomid, level):  # 根据请求算耗电
        now = time.time()
        if self.last_request_time[roomid] != -1.0:
            if self.last_level[roomid] == "低风":
                self.energy_now[roomid] += 0.8 * (now - self.last_request_time[roomid]) / 60
            elif self.last_level[roomid] == "中风":
                self.energy_now[roomid] += (now - self.last_request_time[roomid]) / 60
            elif self.last_level[roomid] == "高风":
                self.energy_now[roomid] += 1.2 * (now - self.last_request_time[roomid]) / 60
        # 每次温控的第一次请求不计费
        self.last_request_time[roomid] = now
        self.last_level[roomid] = level
        self.working[roomid] = WORKING

    def energy_archive(self, roomid):  # 结束本次温控
        now = time.time()
        if self.last_level[roomid] == "低风":
            self.energy_now[roomid] += 0.8 * (now - self.last_request_time[roomid]) / 60.0
        elif self.last_level[roomid] == "中风":
            self.energy_now[roomid] += (now - self.last_request_time[roomid]) / 60.0
        elif self.last_level[roomid] == "高风":
            self.energy_now[roomid] += 1.2 * (now - self.last_request_time[roomid]) / 60.0

        energy_this = self.energy_now[roomid]

        self.energy_post[roomid] += self.energy_now[roomid]
        self.energy_now[roomid] = 0.0
        self.last_request_time[roomid] = -1.0
        self.last_level[roomid] = ''
        self.working[roomid] = IDLE
        return energy_this

    def fit_mode(self, target_temp):  # 检测send wind 要求是否符合模式要求
        return target_temp <= self.range_list[self.mode][1] and target_temp >= self.range_list[self.mode][0]

    def allHigh(self, mode):
        if mode == "低风":
            return True, -1
        elif mode == "中风":
            flag = 1
            a = 0
            for i in range(ROOM_SIZE):
                if(self.working[i]==WORKING and self.last_level[i]== "低风"):
                    flag = 0
                    a = i
                    print("被抢占的房间",a)
                    break
            if flag == 0:
                return False, a
            else:
                return True, -1
        elif mode == "高风":
            flag = 1
            a = 0
            for i in range(ROOM_SIZE):
                if (self.working[i] == WORKING and self.last_level[i] == "中风"):
                    flag = 0
                    a = i
                    break
            for i in range(ROOM_SIZE):
                if (self.working[i] == WORKING and self.last_level[i] == "低风"):
                    flag = 0
                    a = i
                    break
            if flag == 0:
                return False, a
            else:
                return True, -1

    def set_wait(self, roomid):
        if self.working[roomid] == WORKING:
            self.energy_archive(roomid)
        self.working[roomid] = WAITING

    def exist_wait(self):
        return WAITING in self.working

    def get_wait(self):
        return self.working.index(WAITING)

    def clear_wait(self):
        index = self.working.index(WAITING)
        self.working[index]


# 5556
class slave_sendwind_thread(threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.setDaemon(True)

    def run(self):
        sever = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sever.bind(("127.0.0.1", 5556))
        sever.listen()
        while True:
            conn, address = sever.accept()
            print(address)
            loginmsg = conn.recv(1024).decode()
            recData = json.loads(loginmsg)
            threadLock.acquire()
            if myCS.fit_mode(int(recData['target_temp'])):
                if myCS.working.count(WORKING) == CONN_SIZE and myCS.working[int(recData['roomid'])]!=WORKING:
                    all_high, low_index = myCS.allHigh(recData['level'])
                    if all_high:
                        # 1.请求需要等待
                        # send_back("Wait",int(recData['roomid']))
                        # myCS.set_wait(int(recData['roomid']))
                        myCS.last_level[int(recData['roomid'])] = recData['level']
                        conn.send("Wait".encode(encoding="utf-8"))
                    else:
                        # 2.2 低级别从控机被停,相当于end
                        this_energy = myCS.energy_archive(low_index)
                        self.db_slave_stop(low_index, this_energy)
                        self.send_back("Stop", low_index)
                        myCS.energy_add(int(recData['roomid']), recData['level'])
                        self.db_slave_sendwind(recData)
                        conn.send("Ok".encode(encoding="utf-8"))
                else:
                    # 2.1 因为连接不满而可以运行
                    myCS.energy_add(int(recData['roomid']), recData['level'])
                    self.db_slave_sendwind(recData)
                    conn.send("Ok".encode(encoding="utf-8"))
            else:
                conn.send("Bad".encode(encoding="utf-8"))
            threadLock.release()
            conn.close()

    def db_slave_sendwind(self, recData):
        db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
        cursor = db.cursor()
        sql = "insert into log (day,roomid,level,target_temp,cur_temp) " + \
              "values (NOW()," + recData['roomid'] + ",\"" + recData['level'] + "\"," + recData['target_temp'] + "," + \
              recData['cur_temp'] + ")"
        try:
            cursor.execute(sql)
            db.commit()
        except pymysql.InternalError as error:
            code, message = error.args
            print(code, message)
            db.rollback()

        db.close()

    def db_slave_stop(self, roomid, this_energy):
        db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
        cursor = db.cursor()
        sql = "insert into log (day,roomid,end_energy) " + \
              "values (NOW()," + str(roomid) + "," + str(this_energy) + ")"
        try:
            cursor.execute(sql)
            db.commit()
        except pymysql.InternalError as error:
            code, message = error.args
            print(code, message)
            db.rollback()
        db.close()

    def send_back(self, msg, roomid):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", myCS.slave_ip[roomid]))
        client.send(msg.encode(encoding="utf-8"))
        client.close()


# 5557
class slave_end_thread(threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.setDaemon(True)

    def run(self):
        sever = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sever.bind(("127.0.0.1", 5557))
        sever.listen()
        while True:
            conn, address = sever.accept()
            # print(address)
            loginmsg = conn.recv(1024).decode()
            recData = json.loads(loginmsg)
            threadLock.acquire()
            this_energy = myCS.energy_archive(int(recData['roomid']))
            self.db_slave_endwind(recData, this_energy)
            # if myCS.exist_wait():
            #     myCS.get_wait()
            # send_end_wait(myCS.get_wait())
            threadLock.release()
            conn.send("Ok".encode(encoding="utf-8"))
            conn.close()

    def db_slave_endwind(self, recData, this_energy):
        db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
        cursor = db.cursor()
        sql = "insert into log (day,roomid,target_temp,cur_temp,end_energy) " + \
              "values (NOW()," + recData['roomid'] + "," + recData['target_temp'] + "," + recData[
                  'cur_temp'] + "," + str(this_energy) + ")"

        try:
            cursor.execute(sql)
            db.commit()
        except pymysql.InternalError as error:
            code, message = error.args
            print(code, message)
            db.rollback()
        db.close()

    # def send_end_wait(self, roomid):
    #     client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     client.connect(("127.0.0.1", myCS.slave_ip[roomid]))
    #     client.send("End Wait".encode(encoding="utf-8"))
    #     client.close()


# 5555
class slave_login_thread(threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.setDaemon(True)

    def run(self):
        sever = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sever.bind(("127.0.0.1", 5555))
        sever.listen()
        while True:
            conn, address = sever.accept()
            loginmsg = conn.recv(1024).decode()
            recData = json.loads(loginmsg)
            # 数据库验证
            db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
            cursor = db.cursor()
            sql = "select * from roomsg where roomid = " + recData['roomid'] + " and personid = \"" + recData[
                'personid'] + "\""
            cursor.execute(sql)
            result = cursor.fetchall()
            db.close()

            if result:
                self.db_slave_login(recData['roomid'])
                conn.send("Success".encode(encoding="utf-8"))
                workmode = {"mode": myCS.mode_list[myCS.mode], "default": str(myCS.default_temp),
                            "frequency": str(myCS.frequency)}
                workmodejson = json.dumps(workmode)
                conn.send(workmodejson.encode(encoding="utf-8"))
                threadLock.acquire()
                myCS.login_ini(int(recData['roomid']))
                threadLock.release()

            else:
                conn.send("Fail".encode(encoding="utf-8"))
            conn.close()

    def db_slave_login(self, roomid):
        db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
        cursor = db.cursor()
        sql = "insert into log (day,roomid,log) values (NOW()," + str(roomid) + ",\"in\")"
        try:
            cursor.execute(sql)
            db.commit()
        except pymysql.InternalError as error:
            code, message = error.args
            print(code, message)
            db.rollback()

        db.close()


# 5554
class slave_logout_thread(threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.setDaemon(True)

    def run(self):
        sever = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sever.bind(("127.0.0.1", 5554))
        sever.listen()
        while True:
            conn, address = sever.accept()
            loginmsg = conn.recv(1024).decode()
            recData = json.loads(loginmsg)
            threadLock.acquire()
            this_energy = myCS.logout(int(recData['roomid']))
            self.db_slave_logout(recData, this_energy)
            threadLock.release()

            conn.send("Ok".encode(encoding="utf-8"))
            conn.close()

    def db_slave_logout(self, recData, this_energy):
        db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
        cursor = db.cursor()
        sql = "insert into log (day,roomid,log,target_temp,cur_temp,end_energy) " + \
              "values (NOW()," + recData['roomid'] + ",\"out\"," + recData['target_temp'] + "," + recData[
                  'cur_temp'] + "," + str(this_energy) + ")"
        try:
            cursor.execute(sql)
            db.commit()
        except pymysql.InternalError as error:
            code, message = error.args
            print(code, message)
            db.rollback()

        db.close()


# 5553
class slave_synchron_thread(threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.setDaemon(True)

    def run(self):
        sever = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sever.bind(("127.0.0.1", 5553))
        sever.listen()
        while True:
            conn, address = sever.accept()
            loginmsg = conn.recv(1024).decode()
            recData = json.loads(loginmsg)

            # 房间号(从机号或IP等)、开关状态、当前温度、送风状态、当前风速
            threadLock.acquire()
            myCS.cur_temp[int(recData['roomid'])] = float(recData['cur_temp'])
            print(recData["roomid"])
            threadLock.release()
            energy = str(myCS.energy_now[int(recData['roomid'])] + myCS.energy_post[int(recData['roomid'])])
            currentmsg = {'energy': energy}
            jsoncurrentmsg = json.dumps(currentmsg)
            conn.send(jsoncurrentmsg.encode(encoding="utf-8"))
            conn.close()


def person_login(act, pw):
    title, name = '', ''
    db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
    cursor = db.cursor()
    sql = "select * from staff where account = \"" + act + "\" and password = \"" + pw + "\""
    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        if result:
            for row in result:
                title = row[2]
                name = row[3]
    except:
        print("Error: unable to fecth data")
        return '', LOGIN_FAILED
    db.close()
    if title == '管理员':
        return name, AIR_MANAGER
    else:
        return name, ACCOUNTTING

class serverPanel(QWidget):
    def __init__(self, mode, frequency):
        super().__init__()
        self.setMinimumSize(800,600)
        self.setMaximumSize(800,600)
        self.isclick = 0
        self.mode = mode
        self.changemode = QPushButton("changemode",self)
        self.changemode.setMinimumSize(100, 40)
        self.changemode.setMaximumSize(100, 40)
        self.changemode.move(20, 20)
        self.changemode.clicked.connect(self.changemodeP)
        self.open = QPushButton("on/off",self)
        self.open.setMinimumSize(80,40)
        self.open.setMaximumSize(80,40)
        self.open.move(360,500)
        self.frequency = frequency
        self.frequencyText = QLineEdit(self)
        self.frequencyText.setMinimumSize(80, 40)
        self.frequencyText.setMaximumSize(80, 40)
        self.frequencyText.move(600, 20)
        self.modelabel = QLabel(self)
        self.modelabel.setMinimumSize(120, 40)
        self.modelabel.setMaximumSize(120, 40)
        self.modelabel.move(140, 20)
        self.defaultTem = QLabel(self)
        self.defaultTem.setMinimumSize(120, 40)
        self.defaultTem.setMaximumSize(120, 40)
        self.defaultTem.move(300, 20)
        self.changeButtom = QPushButton('change',self)
        self.changeButtom.setMinimumSize(80, 40)
        self.changeButtom.setMaximumSize(80, 40)
        self.changeButtom.move(500, 20)
        self.msgText = QTextEdit(self)
        self.msgText.setMinimumSize(600, 400)
        self.msgText.setMaximumSize(600, 400)
        self.msgText.move(100, 100)
        self.open.clicked.connect(self.showpanel)
        self.changeButtom.clicked.connect(self.changefruquency)
        self.flash = QTimer(self)
        self.flash.timeout.connect(self.changemsg)

    def changemodeP(self):
        global myCS
        if(self.mode==0):
            self.mode = 1
        else:
            self.mode=0
        if self.mode == 0:
            myCS.mode = self.mode
            myCS.default_temp = myCS.default_temp_list[self.mode]
            self.modelabel.setText('工作模式：Cold')
            self.defaultTem.setText('默认温度：22')
        else:
            myCS.mode = self.mode
            myCS.default_temp = myCS.default_temp_list[self.mode]
            self.modelabel.setText('工作模式：Warm')
            self.defaultTem.setText('默认温度：28')


    def showpanel(self):
        if(self.isclick==1):
            self.modelabel.clear()
            self.defaultTem.clear()
            self.frequencyText.clear()
            self.msgText.clear()
            self.flash.stop()
            self.isclick = 0
        else:
            if self.mode == 0:
                self.modelabel.setText('工作模式：Cold')
                self.defaultTem.setText('默认温度：22')
            else:
                self.modelabel.setText('工作模式：Warm')
                self.defaultTem.setText('默认温度：28')
            self.frequencyText.setText(str(self.frequency/1000))
            self.flash.start(self.frequency)
            self.isclick = 1
        self.update()

    def changefruquency(self):
        self.frequency = int(self.frequencyText.text())*1000
        self.flash.start(self.frequency)

    def changemsg(self):
        global myCS
        msg = ''
        for i in range(5):
            msg = msg+"第"+str(i+1)+"号房间：\n"
            msg +='当前温度：'+ str(round(myCS.cur_temp[i],1))+' '
            msg += '当前风速：' +myCS.last_level[i]+' '
            if myCS.login_activate[i]:
                msg += '开关状态：开 '
            else:
                msg += '开关状态：关 '
            if myCS.working[i] == 2:
                msg += '送风状态：空闲 '
            elif myCS.working[i] == 1:
                msg+= '送风状态：等待 '
            elif myCS.working[i] == 0:
                msg += '送风状态：工作 '
            msg += '\n'
        self.msgText.setText(msg)
        self.update()

myCS = CenterSys()
threadLock = threading.Lock()

if __name__ == '__main__':
    # account=input("账号:")
    # password=input("密码:")
    app = QApplication(sys.argv)
    account = 'xiaohua'
    password = 'xiaohua'
    name, login_result = person_login(account, password)  # 验证登录
    if login_result == AIR_MANAGER:
        print("管理员登录成功！请设置启动参数，设置完毕后启动：")
        mode = 0
        frequency = 1000
        # mode=int(input("运行模式：（0：制冷，1：制热）[0]"))
        # frequency = int(input("刷新频率/毫秒：[1000]"))
        myCS = CenterSys(mode, frequency)

        Panel = serverPanel(mode, frequency)
        Panel.show()
        thread_login = slave_login_thread(1)
        thread_logout = slave_logout_thread(2)
        thread_sendwind = slave_sendwind_thread(3)
        thread_end = slave_end_thread(4)
        thread_synchron = slave_synchron_thread(5)
        thread_login.start()
        thread_logout.start()
        thread_sendwind.start()
        thread_end.start()
        thread_synchron.start()
        '''thread_login.join()
        print(51)
        thread_logout.join()
        print(52)
        thread_sendwind.join()
        print(53)
        thread_end.join()
        print(54)
        thread_synchron.join()
        print(60)'''
    elif login_result == ACCOUNTTING:  # 酒店前台查账
        print("前台登录成功！有以下房间及时间段的信息可供查询：")

    else:
        print("登录失败: 密码或用户名错误")

    sys.exit(app.exec_())
