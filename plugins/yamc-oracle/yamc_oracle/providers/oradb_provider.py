# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import re
import time
import os

import cx_Oracle

from yamc.providers import BaseProvider 

def makeDictFactory(cursor):
    columnNames = [d[0].lower() for d in cursor.description]
    def createRow(*args):
        return dict(zip(columnNames, args))
    return createRow        

def hide_password(connstr):
    return re.sub("\/(.+)@","/(secret)@",connstr)

class OraDBProvider(BaseProvider):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.connection = None
        self.connect_time = None
        self.cache = {}

        # configuration
        self.connstr = self.config.value_str("connstr", required=True)
        self.reconnect_after = self.config.value_int("reconnect_after", required=False, default=3600)
        self.sql_files_dir = self.config.get_dir_path(self.config.value_str("sql_files_dir", required=True), check=True)

    def open(self):
        if self.connection is None or time.time()-self.connect_time > self.reconnect_after:
            if self.connection is not None:
                self.close()
            self.log.info(f"Opening the DB connection, connstr={hide_password(self.connstr)}")
            self.connection = cx_Oracle.connect(self.connstr)
            self.connect_time = time.time()
        
    def close(self):
        if self.connection is not None:
            self.log.info("Closing the DB connection.")
            self.connection.close()
            self.connection = None
            
    def destroy(self):    
        super().destroy()        
        self.close()
        
    def load_statement(self, sql_file):
        if self.cache.get(sql_file) is None:
            fname = "%s/%s"%(self.sql_files_dir, sql_file)
            if not os.path.isfile(fname):
                raise Exception("The SQL file %s does not exist!"%fname)
            lines=[]
            with open(fname, 'r') as file:
                lines = [x for x in file]
            self.cache[sql_file] = "\n".join(lines)
        return self.cache.get(sql_file)
        
    def sql(self, sql_file, variables=[]):
        statement = self.load_statement(sql_file)
        self.open()
        self.log.debug("Running the SQL statement: %s"%re.sub("\s+", " ", statement))
        cursor = self.connection.cursor()
        try:
            query_time = time.time()
            cursor.execute(statement, variables)
            cursor.rowfactory = makeDictFactory(cursor)
            data = []
            for row in cursor:
                row["time"] = query_time
                data.append(row)
            self.log.info(f"The OraDB sql operation retrieved {len(data)} records in {time.time()-query_time:0.04f} seconds.")
            self.log.trace(f"The following data were retrieved from the DB: {str(data)}")
            return data
        finally:
            cursor.close()
        
