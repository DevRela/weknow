# -*- coding: utf-8 -*-
import os
import sys
import traceback
from copy import deepcopy
from time import time, gmtime, strftime, localtime
import hashlib





from config import CFG
#from xsettings import XCFG
#_k4incr = CFG.TOT
KV = CFG.KV #sae.kvdb.KVClient()
BK = CFG.BK

def PUT2SS(raw, actype='bkup', name='db'):
    if 'bkup' == actype:
        sid = "%s.dump"% GENID('bkup', name)
    print "\n PUT2SS:", sid
    #   初始化一个Storage客户端。
    BK.put_object(sid, raw)
    uri = BK.generate_url(sid)
    return sid, uri





def INIobjSYS(key):
    '''try and init. all kinds of objSYS K/V
    '''    
    if key not in CFG.K4D.keys():
        return None
    else:
        #print CFG.K4D[key]
        if not KV.get(CFG.K4D[key]):
            KV.add(CFG.K4D[key],[])
        return (CFG.K4D[key], KV.get(CFG.K4D[key]))




def ADD4SYS(k4sys, uuid):
    '''try safty insert SOMETHING to SYS:** K/V
    only dm|m|p means dama|member|paper
    '''
    uuid_idx = KV.get(CFG.K4D[k4sys])
    #print "listobj:\t", uuid_idx
    if None == uuid:
        appended = uuid_idx
    elif uuid in uuid_idx:
        appended = uuid_idx
    else:
        # 防止意外重复
        uuid_idx.append(uuid)
        appended = list(set(uuid_idx))
        KV.replace(CFG.K4D[k4sys],  appended)
    
    return (CFG.K4D[k4sys], appended)



def TSTAMP():
    '''通用时间戳生成器:
        yymmddHHMMSS+5位微秒
        e.g.
        12080110561431076
    '''
    date = strftime("%y%m%d%H%M%S", localtime())
    mms = "%.5f"% time()
    ms = mms[-5:]
    return "%s%s"% (date, ms)




def GENID(obj, name=""):
    '''通用ID生成器:
        yymmddHHMMSS+5位微秒+对象鍵3位+全局序号
        - 对分标签的文章分级选择,包含额外标识信息:
            - dd_ 前缀就是分类 tag
            - __** 后缀就是指定的文章编号
    '''
    timestamp = TSTAMP()
    tot = INCR4KV()
    #sha1name = hashlib.sha1(name).hexdigest()
    GOBJMAP = {'his':'h_%(timestamp)s_HIS%(tot)d'
        ,'bkup':'bk_%(timestamp)s_SG%(tot)d_%(name)s'
        ,'tag':'t_%(timestamp)s_TAG%(tot)d'
        ,'event':'e_%(timestamp)s_EVE%(tot)d'
        ,'paper':'p_%(timestamp)s_PUB%(tot)d'
        ,'ot':'ot_%(timestamp)s_PUB%(tot)d'
        ,'gb':'gb_%(timestamp)s_PUB%(tot)d'
        ,'dd':'dd_%(timestamp)s_PUB%(tot)d'
        ,'gt':'gt_%(timestamp)s_PUB%(tot)d'
        ,'dm':'dm_%(timestamp)s_PUB%(tot)d'
        ,'hd':'hd_%(timestamp)s_PUB%(tot)d'
        ,'et':'et_%(timestamp)s_PUB%(tot)d'
        #,'dm':'m:%(timestamp)s:DM%(tot)d'
        ,'fw':'fw_%(timestamp)s_PUB%(tot)d'
        }
    if obj in GOBJMAP.keys():
        return GOBJMAP[obj]% locals()
    else:
        return None


def USRID(Passpord):
    '''base Passpord make UUID
    '''
    sha1_name = hashlib.sha1(Passpord).hexdigest()
    return 'u_%s'% sha1_name



def DAMAID(name):
    return 'm_%s_DM'% name



def INCR4KV():
    '''BASE KVDB make GLOBAL increaser
    '''
    #print CFG.KEY4_incr
    #print None == CFG.KV.get(CFG.KEY4_incr)
    if None == KV.get(CFG.K4D['incr']):
        #print "\t EMPTY?!"
        KV.add(CFG.K4D['incr'], 0)
    else:
        #print "\t incr. BASE HISTORIC"
        KV.set(CFG.K4D['incr'], KV.get(CFG.K4D['incr'])+1)
    return KV.get(CFG.K4D['incr'])






if __name__ == '__main__':
    if 2 != len(sys.argv) :
        print '''Usage:
            utility.py test
        '''
    else:
        print "hand testing ..."

