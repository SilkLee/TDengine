﻿###################################################################
#           Copyright (c) 2016 by TAOS Technologies, Inc.
#                     All rights reserved.
#
#  This file is proprietary and confidential to TAOS Technologies.
#  No part of this file may be reproduced, stored, transmitted,
#  disclosed or used in any form or by any means other than as
#  expressly provided by the written permission from Jianhui Tao
#
###################################################################

# -*- coding: utf-8 -*-

import sys
import os
import time
import datetime
import inspect
from util.log import *


class TDSql:
    def __init__(self):
        self.queryRows = 0
        self.queryCols = 0
        self.affectedRows = 0

    def init(self, cursor, log=True):
        self.cursor = cursor

        if (log):
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            self.cursor.log(caller.filename + ".sql")

    def close(self):
        self.cursor.close()

    def prepare(self):
        tdLog.info("prepare database:db")
        s = 'reset query cache'
        self.cursor.execute(s)
        s = 'drop database if exists db'
        self.cursor.execute(s)
        s = 'create database db'
        self.cursor.execute(s)
        s = 'use db'
        self.cursor.execute(s)

    def error(self, sql):
        expectErrNotOccured = True
        try:
            self.cursor.execute(sql)
        except BaseException:
            expectErrNotOccured = False
        if expectErrNotOccured:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            tdLog.exit("%s(%d) failed: sql:%s, expect error not occured" % (caller.filename, caller.lineno, sql))
        else:
            self.queryRows = 0
            self.queryCols = 0
            self.queryResult = None
            tdLog.info("sql:%s, expect error occured" % (sql))

    def query(self, sql):
        self.sql = sql
        try:
            self.cursor.execute(sql)
            self.queryResult = self.cursor.fetchall()
            self.queryRows = len(self.queryResult)
            self.queryCols = len(self.cursor.description)
        except Exception as e:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            args = (caller.filename, caller.lineno, sql, repr(e))
            tdLog.notice("%s(%d) failed: sql:%s, %s" % args)
            raise Exception(repr(e))
        return self.queryRows

    def waitedQuery(self, sql, expectRows, timeout):
        tdLog.info("sql: %s, try to retrieve %d rows in %d seconds" % (sql, expectRows, timeout))
        self.sql = sql
        try:
            for i in range(timeout):
                self.cursor.execute(sql)
                self.queryResult = self.cursor.fetchall()
                self.queryRows = len(self.queryResult)
                self.queryCols = len(self.cursor.description)
                if self.queryRows >= expectRows:
                    return (self.queryRows, i)
                time.sleep(1)
        except Exception as e:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            args = (caller.filename, caller.lineno, sql, repr(e))
            tdLog.notice("%s(%d) failed: sql:%s, %s" % args)
            raise Exception(repr(e))
        return (self.queryRows, timeout)

    def checkRows(self, expectRows):
        if self.queryRows == expectRows:
            tdLog.info("sql:%s, queryRows:%d == expect:%d" % (self.sql, self.queryRows, expectRows))
        else:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            args = (caller.filename, caller.lineno, self.sql, self.queryRows, expectRows)
            tdLog.exit("%s(%d) failed: sql:%s, queryRows:%d != expect:%d" % args)

    def checkRowCol(self, row, col):
        caller = inspect.getframeinfo(inspect.stack()[2][0])
        if row < 0:
            args = (caller.filename, caller.lineno, self.sql, row)
            tdLog.exit("%s(%d) failed: sql:%s, row:%d is smaller than zero" % args)
        if col < 0:
            args = (caller.filename, caller.lineno, self.sql, row)
            tdLog.exit("%s(%d) failed: sql:%s, col:%d is smaller than zero" % args)
        if row > self.queryRows:
            args = (caller.filename, caller.lineno, self.sql, row, self.queryRows)
            tdLog.exit("%s(%d) failed: sql:%s, row:%d is larger than queryRows:%d" % args)
        if col > self.queryCols:
            args = (caller.filename, caller.lineno, self.sql, col, self.queryCols)
            tdLog.exit("%s(%d) failed: sql:%s, col:%d is larger than queryCols:%d" % args)

    def checkDataType(self, row, col, dataType):
        self.checkRowCol(row, col)
        return self.cursor.istype(col, dataType)

    def checkData(self, row, col, data):
        self.checkRowCol(row, col)
        if self.queryResult[row][col] != data:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            args = (caller.filename, caller.lineno, self.sql, row, col, self.queryResult[row][col], data)
            tdLog.exit("%s(%d) failed: sql:%s row:%d col:%d data:%s != expect:%s" % args)

        if data is None:
            tdLog.info("sql:%s, row:%d col:%d data:%s == expect:%s" %
                       (self.sql, row, col, self.queryResult[row][col], data))
        elif isinstance(data, str):
            tdLog.info("sql:%s, row:%d col:%d data:%s == expect:%s" %
                       (self.sql, row, col, self.queryResult[row][col], data))
        elif isinstance(data, datetime.date):
            tdLog.info("sql:%s, row:%d col:%d data:%s == expect:%s" %
                       (self.sql, row, col, self.queryResult[row][col], data))
        else:
            tdLog.info("sql:%s, row:%d col:%d data:%s == expect:%d" %
                       (self.sql, row, col, self.queryResult[row][col], data))

    def getData(self, row, col):
        self.checkRowCol(row, col)
        return self.queryResult[row][col]

    def executeTimes(self, sql, times):
        for i in range(times):
            try:
                return self.cursor.execute(sql)
            except BaseException:
                time.sleep(1)
                continue

    def execute(self, sql):
        self.sql = sql
        try:
            self.affectedRows = self.cursor.execute(sql)
        except Exception as e:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            args = (caller.filename, caller.lineno, sql, repr(e))
            tdLog.notice("%s(%d) failed: sql:%s, %s" % args)
            raise Exception(repr(e))
        return self.affectedRows

    def checkAffectedRows(self, expectAffectedRows):
        if self.affectedRows != expectAffectedRows:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            args = (caller.filename, caller.lineno, self.sql, self.affectedRows, expectAffectedRows)
            tdLog.exit("%s(%d) failed: sql:%s, affectedRows:%d != expect:%d" % args)

        tdLog.info("sql:%s, affectedRows:%d == expect:%d" % (self.sql, self.affectedRows, expectAffectedRows))


tdSql = TDSql()
