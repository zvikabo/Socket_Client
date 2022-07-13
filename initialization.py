import logging
import logging.handlers
import re,os
from logging.config import fileConfig
import logging.handlers
import configparser





class cfgFile:
    def __init__(self,cfgFileName):
        self.v_cfgFileName = cfgFileName

    def get_cfg_data(self):
        config = configparser.ConfigParser()
        config.read(self.v_cfgFileName)
        dict_cfg = {s: dict(config.items(s)) for s in config.sections()}
        return dict_cfg



class MyLogger:
    def __init__(self,Logfile,MaxBytes,BackupCount,Encoding='utf8',Fmt="%(levelname)s:%(name)s | %(message)s '' | (%(asctime)s |  %(filename)s  |  %(lineno)d)",DateFmt="%Y-%m-%d %H:%M:%S"):
        self.v_Logfile=Logfile
        self.v_MaxBytes=MaxBytes
        self.v_BackupCount=BackupCount
        self.v_Encoding=Encoding
        self.v_Fmt = Fmt
        self.v_DateFmt = DateFmt

    def getLogger(self):

        f = logging.Formatter(fmt=self.v_Fmt,datefmt=self.v_DateFmt)
        handlers = [logging.handlers.RotatingFileHandler( self.v_Logfile, encoding=self.v_Encoding, maxBytes= self.v_MaxBytes,backupCount=self.v_BackupCount)]

        LoggerFileName = logging.getLogger(self.v_Logfile)
        LoggerFileName.setLevel(logging.DEBUG)
        for h in handlers:
            h.setFormatter(f)
            h.setLevel(logging.DEBUG)
            LoggerFileName.addHandler(h)
        return LoggerFileName

