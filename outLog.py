import pymysql
import datetime
from flask import Blueprint, jsonify, abort, Response, request


# 查找全部的符合时间限制的记录
def Generate_Report(start, end):
    # cnx = mysql.connector.connect(**config)

    db = pymysql.connect("127.0.0.1", "root", "newpassword", "AC", port=3306)
    cursor = db.cursor()

    file_log = open("record.txt", "w")
    file_log1 = open("DayReport.txt", "w")

    start_time = datetime.datetime.strptime(str(start), '%Y-%m-%d').strftime("%Y-%m-%d")
    end_time = (datetime.datetime.strptime(str(end), '%Y-%m-%d') +
                datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    Report = []
    # 查询记录表中不同的房间ID
    room_id = []
    query = ('SELECT DISTINCT roomid FROM `log`')
    cursor.execute(query)
    for m, each in enumerate(cursor):
        Report.append({})
        room_id.append(each[0])
    room_id.sort()
    # 依次统计每个从机

    print('运行日志：')
    file_log.write('详单文件：\n')
    file_log1.write('日报表：\n')
    file_log.write('\n')
    file_log1.write('\n')

    for n, id in enumerate(room_id):
        # print(n,id)
        query = (
                'SELECT * FROM `log` WHERE roomid = "%d" AND day >= "%s" AND day <= "%s" ORDER BY day'
                % (id, start_time, end_time))
        cursor.execute(query)
        # 统计开关机次数
        record = []
        Report[n]['ROOM_ID'] = id
        Report[n]['Count'] = 0  # 开关机次数
        for each in cursor:
            record.append(each)
            if each[3] == 'out':
                Report[n]['Count'] = Report[n]['Count'] + 1  # 风速为0即表示关机，则开关机次数加一
        # 整理房间从机的每一条记录
        Report[n]['Record'] = []
        a = []
        total_cost = 0.0
        cost = 0.0
        count = 0

        file_log.write('房间号:' + str(id) + '\n')
        file_log.write('\n')
        file_log1.write('时间：' + str(start) + '\n')
        file_log1.write('\n')
        file_log1.write('房间号:' + str(id) + '\n')
        file_log1.write('\n')

        for i in range(len(record) - 1):  # 对于一个房间的每一条记录
            # 记录请求的起止时间、温度、风速
            a.append({i: record[i]})
            # a.append(record[i])

            # print(a)
            # print('\n')
            # print('\n')
            # print(a[0])
            # print('\n')
            # print(a[0][0])
            # print('\n')
            # print(record)

            if record[i][3] == 'in':
                count = count + 1
                print('用户登录')
                print('用户登录时间：' + str(record[i][1]))
                # file_log.write('用户登录\n')
                # file_log.write('用户登录时间：'+str(record[i][1])+'\n')
                # file_log.write('\n')
                print('\n')
            if record[i][3] == 'out':
                count = count + 1
                print('用户登出')
                print('用户登出时间：' + str(record[i][1]))
                # file_log.write('用户登出\n')
                # file_log.write('用户登出时间：' + str(record[i][1])+'\n')
                # file_log.write('\n')
                print('\n')

            if record[i][4] != None:  # 一次温控请求开始标志
                a[i]['S_time'] = datetime.datetime.strptime((record[i][1]), "%Y-%m-%d %H:%M:%S")  # 开始时间)
                a[i]['Level'] = record[i][4]  # 风速
                a[i]['T_temp'] = record[i][5]  # 目标温度
                a[i]['S_temp'] = record[i][6]  # 开始温度

                print('一次送风请求')
                print('送风请求开始时间：' + str(a[i]['S_time']))
                print('送风风速：' + str(a[i]['Level']))
                print('目标温度：' + str(a[i]['T_temp']))
                print('开始温度：' + str(a[i]['S_temp']))
                print('\n')

                file_log.write('送风开始：\n')
                file_log.write('送风开始时间：' + str(a[i]['S_time']) + '\n')
                file_log.write('风速：' + str(a[i]['Level']) + '\n')
                file_log.write('目标温度：' + str(a[i]['T_temp']) + '\n')
                # file_log.write('开始温度：' + str(a[i]['S_temp'])+'\n')
                # file_log.write('\n')

                file_log1.write('一次送风请求\n')
                file_log1.write('送风请求开始时间：' + str(a[i]['S_time']) + '\n')
                file_log1.write('送风风速：' + str(a[i]['Level']) + '\n')
                file_log1.write('目标温度：' + str(a[i]['T_temp']) + '\n')
                file_log1.write('开始温度：' + str(a[i]['S_temp']) + '\n')

            if record[i][4] != None:
                cost = cost + Cost(record[i][1], record[i + 1][1],
                                   record[i][4])

            if (record[i][7] != None) & (record[i][3] != 'out'):
                a[i]['E_time'] = datetime.datetime.strptime((record[i][1]), "%Y-%m-%d %H:%M:%S")  # 结束时间
                a[i]['E_temp'] = record[i + 1][6]  # 结束温度
                a[i]['end_energy'] = record[i][7]  # 每次送风结束后的功率
                a[i]['cost'] = '%.2f' % cost
                total_cost = total_cost + cost
                cost = 0

                print('送风结束')
                print('送风结束时间：' + str(a[i]['E_time']))
                print('送风结束温度：' + str(a[i]['E_temp']))
                print('送风结束后的功率：' + str(a[i]['end_energy']))
                # print('送风结束后的费用：'+str(a[i]['cost']))
                print('\n')

                file_log.write('送风结束\n')
                file_log.write('送风结束时间：' + str(a[i]['E_time']) + '\n')
                file_log.write('送风结束温度：' + str(a[i]['E_temp']) + '\n')
                file_log.write('送风消耗能量：' + str(a[i]['end_energy']) + '\n')
                file_log.write('送风产生费用：' + str(a[i]['cost']) + '\n')
                file_log.write('\n')
                # file_log.write('送风结束后的费用：' + str(a[i]['cost'])+'\n')

                file_log1.write('送风结束\n')
                file_log1.write('送风结束时间：' + str(a[i]['E_time']) + '\n')
                file_log1.write('送风结束温度：' + str(a[i]['E_temp']) + '\n')
                file_log1.write('送风结束后的功率：' + str(a[i]['end_energy']) + '\n')
                file_log1.write('送风结束后的费用：' + str(a[i]['cost']) + '\n')
                file_log1.write('\n')

        file_log1.write('开关机次数：' + str(count) + '\n')
        file_log1.write('当日总费用：' + str(total_cost) + '\n')
        # 每一次送风结束后的费用

        Report[n]['Cost'] = '%.2f' % total_cost

        for each in a:
            if each:
                Report[n]['Record'].append(each)
    db.close()
    file_log.close()
    return Report


def Cost(start, end, level):
    start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
    time = end - start
    cost = 0.0
    if level == '低风':
        cost = (time.total_seconds() / 60) * 0.8 * 5
    elif level == '中风':
        cost = (time.total_seconds() / 60) * 1 * 5
    elif level == '高风':
        cost = (time.total_seconds() / 60) * 1.3 * 5
    return cost


'''
Report[n]['ROOM_ID']
Report[n]['Count']
Report[n]['Record']
    [{0:['114','2020-06-08 22:10:42','1','in','NULL','NULL','NULL','NULL']}]
Report[n]['Cost']

'''

Generate_Report((datetime.date.today() + datetime.timedelta(days=0)).strftime("%Y-%m-%d"),
                (datetime.date.today() + datetime.timedelta(days=0)).strftime("%Y-%m-%d"))


def get_today_log():
    return jsonify(
        Generate_Report(
            (datetime.date.today() + datetime.timedelta(days=0)).strftime("%Y-%m-%d"),
            (datetime.date.today() + datetime.timedelta(days=0)).strftime("%Y-%m-%d")))



