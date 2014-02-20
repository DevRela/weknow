# -*- coding: utf-8 -*-
import os
#关闭fetchurl，让httplib直接使用socket服务来连接
os.environ['disable_fetchurl'] = "1" 

import sys   
import time #import time, gmtime, strftime, localtime
from datetime import datetime
import traceback
import httplib
import urllib 
import urllib2
# 打开urllib2的debug开关
urllib2.install_opener(urllib2.build_opener(urllib2.HTTPSHandler(1)))

import hashlib
import json
import string
import base64
import cPickle
#import ConfigParser
from os.path import splitext as os_splitext
from os.path import exists as os_exists

from copy import deepcopy
import xml.etree.ElementTree as etree

import pyfsm
from pyfsm import state, transition

from wechat.official import WxApplication, WxRequest, WxTextResponse, WxNewsResponse, WxArticle

from bottle import *
from bottle import __version__ as bottleVer
#from bottle import jinja2_template as template

from auth import _query2dict, _chkQueryArgs

from utility import INCR4KV as __incr
from utility import TSTAMP, GENID, USRID, DAMAID
from utility import ADD4SYS
from utility import PUT2SS

#print sys.path
from config import CFG
from xsettings import XCFG
KV = CFG.KV #sae.kvdb.KVClient(debug=1)
BK = CFG.BK
debug(True)

APP = Bottle()

@APP.get('/echo')
@APP.get('/echo/')
def echo_wechat():
    '''wechat app token echo
    '''
    #print request.query.keys()
    #print request.query.echostr
    #print request.query_string
    #print dir(BaseRequest.query_string)
    return request.query.echostr

'''
def wechat(request):
    app = EchoApp()
    result = app.process(request.GET, request.body, token='your token')
    return HttpResponse(result)
'''

# echo for RESTful remote actions
'''[api]RESTful管理事务设计 on lbTC-开发协调 | Trello
	https://trello.com/c/ztdsulpM/82-api-restful
- 全部基于: `/api/cli` 前缀
    - 版本区隔为: `/api/v2/cli` 前缀
- 签名检验
- 时间检验(4.2秒以内, 并发不得超过 `N` 次)
query_string 
'''

@APP.get('/cli/info/<uuid>/<qstr>')
def info_kv(uuid, qstr):
    '''查询 UUID 的信息
    '''
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/info/%s"% uuid, q_dict, "GET"):
        feed_back = {'data':[]}
        print "info_kv()>>> ",uuid
        print KV.get(uuid)
        #return KV.get(uuid)
        feed_back['msg'] = "safe quary;-)"
        feed_back['data'] = KV.get(uuid)
        return feed_back
    else:
        return "alert quary!-("

@APP.get('/cli/sum/<matter>/<qstr>')
def st_kv(matter, qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/sum/%s"% matter, q_dict, "GET"):
        feed_back = {'data':[]}

        if 'db' == matter:
            feed_back['msg'] = "all SYS_* status."

            for k in CFG.K4D.keys():
                if "incr" == k:
                    feed_back['data'].append("%s is %s "%(
                        CFG.K4D['incr']
                        , KV.get(CFG.K4D['incr'])
                        ))
                elif 'fw' == k:
                    tot = 0
                    all_fw = KV.get(CFG.K4D[k])
                    for k in all_fw:
                        tot += len(all_fw[k])
                    feed_back['data'].append("FW %s users %s msg.s"% (
                        len(all_fw)
                        , tot
                        ))
                else:
                    feed_back['data'].append("%s hold %s nodes,"% (
                        CFG.K4D[k]
                        , len(KV.get(CFG.K4D[k]))
                        ))





        elif 'bk' == matter:
            count = 0
            for dump in BK.list():
                count += 1
                feed_back['data'].append("%s ~ %s"%(dump['name']
                    , dump['bytes']
                    ))

            feed_back['msg'] = "all Storaged %s dumps"% count




        elif 'dm' == matter:
            count = 0
            k4dm = KV.get(CFG.K4D[matter] )
            for k in k4dm:
                count += 1
                crt_dm = KV.get(k)
                _dm = {}
                _dm['UUID'] = k
                _dm['pp'] = crt_dm['pp']
                _dm['nm'] = crt_dm['nm']
                _dm['desc'] = crt_dm['desc']
                _dm['em'] = crt_dm['em']
                _dm['mo'] = crt_dm['mo']    # Mobile
                feed_back['data'].append(_dm)
                
            feed_back['msg'] = "all Storaged %s dumps"% count



        elif 'fw' == matter:
            count = 0
            k4dm = KV.get(CFG.K4D[matter] )
            print k4dm
            for k in k4dm.keys():
                count += 1
                #feed_back['data'].append(_dm)

            feed_back['msg'] = "all Storaged %s dumps"% count


            
        else:
            if matter in CFG.K4D.keys():
                feed_back['msg'] = "base %s data."% CFG.K4D[matter]
                feed_back['data'] = "%s hold %s node info."% (CFG.K4D[matter]
                    , len(KV.get(CFG.K4D[matter] )) 
                    )
            else:
                feed_back['msg'] = "sum key is OUT CFG.K4D !-("

        return feed_back
    else:
        return "alert quary !-("


@APP.get('/cli/st/kv/<qstr>')
def st_kv(qstr):
    '''查询 KVDB 整体现状
    '''
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/st/kv", q_dict, "GET"):
        feed_back = {'data':[]}
        #data.append(KV.get_info())
        return KV.get_info()
        feed_back['msg'] = "safe quary;-)"
        feed_back['data'] = KV.get_info()
        return feed_back
    else:
        return "alert quary!-("

# collection KVDB mana. matters
'''
'''
@APP.post('/cli/bk/<matter>')
def bkup_dump(matter):
    q_dict = request.forms
    if _chkQueryArgs("/cli/bk/%s"% matter, q_dict, "PUT"):
        feed_back = {'data':[]}
        if 'db' ==  matter:
            print "try dumps all nodes from KVDB"
            kb_objs = {}
            total = 0
            for k in CFG.K4D:
                #print k
                if 'incr' == k:
                    # 只要替换一个自增值
                    #kb_objs[k] = CFG.K4D[k]
                    kb_objs[CFG.K4D[k] ] = KV.get(CFG.K4D[k])
                    total += 1
                else:
                    # 需要根据索引值列逐一提取数据
                    #kb_objs[k] = CFG.K4D[k]
                    kb_objs[CFG.K4D[k] ] = KV.get(CFG.K4D[k])
                    total += 1
                    if 0 != len(kb_objs[CFG.K4D[k] ] ):
                        for k4v in kb_objs[CFG.K4D[k] ]:
                            crt_v = KV.get(k4v)
                            if None != crt_v:
                                kb_objs[k4v] = crt_v
                                total += 1
            dumps = cPickle.dumps(kb_objs)
            feed_back['data'].append("%s pointed %s nodes"%(CFG.K4D, total) )

            #print kb_objs

            msg = "bkup KVDB dumped"
        else:
            kb_objs = {}
            kb_objs[CFG.K4D[matter] ] = KV.get(CFG.K4D[matter])
            if 0 != len(kb_objs[CFG.K4D[matter] ] ):
                for k in kb_objs[CFG.K4D[matter] ]:
                    kb_objs[k] = KV.get(k)
            dumps = cPickle.dumps(kb_objs)
            feed_back['data'].append("%s pointed %s nodes"%(CFG.K4D[matter] 
                , len(kb_objs[CFG.K4D[matter] ] )))
            #print kb_objs
            msg = "bkup %s dumped"% CFG.K4D[matter]
        
        sid, uri = PUT2SS(dumps, name=matter)
        feed_back['data'].append( BK.stat_object(sid) )
        feed_back['msg'] = msg
        feed_back['uri'] = uri
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("

@APP.put('/cli/revert/<matter>')
def revert_dump(matter):
    '''从服务端恢复数据用, 注意,全部恢复的步骤:
    - 删除  --kvdb-file=./logs/kv.db
    - CLI.py -D revert/db set=...   导入备份
    - CLI.py -D resolve/wx set=all  检查反指 K/V 对
    '''
    
    q_dict = request.forms
    if _chkQueryArgs("/cli/revert/%s"% matter, q_dict, "PUT"):
        feed_back = {'data':[]}
        set_key = list(set(q_dict.keys())-set(CFG.SECURE_ARGS))[0]
        set_var = base64.urlsafe_b64decode(request.forms[set_key])
        #print set_key, set_var
        if 'db' ==  matter:
            print "try revert ALL date from KVDB"
            dumps = BK.get_object_contents(set_var)
            re_obj = cPickle.loads(dumps)
            feed_back['msg'] = "reverted %s nodes for whole KVDB "% len(re_obj.keys())
            _INX_KEYS = [CFG.K4D[k] for k in CFG.K4D.keys()]
            # replace global idx K/V, maybe make ghost K/V
            _his = set()#KV.get(CFG.K4D['his'])            
            for k in re_obj.keys():
                if k in _INX_KEYS:
                    # 索引键处理
                    if k == CFG.K4D['incr']:
                        # 只要替换一个自增值
                        KV.set(k, re_obj[k])
                        _his.add(k)
                    elif k == CFG.K4D['his']:
                        # 统一增替
                        _his.add(k)
                    else:
                        print "revert ->", k 
                        #print _his
                        #print type(re_obj[k])
                        _his.add(k)
                        _his.update(set(re_obj[k]))
                        print "_his ", len(_his)
                        KV.set(k, re_obj[k])
                else:
                    # 数据键恢复
                    #print k, re_obj[k]
                    if None == KV.get(k):
                        KV.add(k, re_obj[k])
                    else:
                        KV.replace(k, re_obj[k])
            KV.set(CFG.K4D['his'], list(_his) )
            #print KV.get(CFG.K4D['his'])



        else:
            dumps = BK.get_object_contents(set_var)
            re_obj = cPickle.loads(dumps)
            feed_back['msg'] = "reverted %s nodes as %s "% (len(re_obj[CFG.K4D[matter]])
                , CFG.K4D[matter]
                )
            # replace global idx K/V, maybe make ghost K/V
            _his = KV.get(CFG.K4D['his'])
            _his.append(re_obj[CFG.K4D[matter]] )
            _his = list(set(CFG.K4D['his']) )
            KV.set(CFG.K4D['his'], _his)

            uuids = re_obj[CFG.K4D[matter]]
            KV.replace(CFG.K4D[matter], uuids)
            for uuid in uuids:
                #print uuid, re_obj[uuid]
                if None == KV.get(uuid):
                    KV.add(uuid, re_obj[uuid])
                else:
                    KV.replace(uuid, re_obj[uuid])





                    
        feed_back['data'].append( BK.stat_object(set_var) )
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("

@APP.put('/cli/resolve/<matter>')
def resolve_his(matter):
    q_dict = request.forms
    if _chkQueryArgs("/cli/resolve/%s"% matter, q_dict, "PUT"):
        feed_back = {'data':[]}
        set_key = list(set(q_dict.keys())-set(CFG.SECURE_ARGS))[0]
        set_var = base64.urlsafe_b64decode(request.forms[set_key])
        print "resolve_his()  ", set_key, set_var
        if 'his' ==  matter:
            print "try resolve_his ALL from KVDB"
            _INX_KEYS = [CFG.K4D[k] for k in CFG.K4D.keys()]
            _his = set() #KV.get(CFG.K4D['his'])  
            feed_back['msg'] = []
            #print _INX_KEYS, type(_INX_KEYS)
            for k in _INX_KEYS:
                # 索引键处理
                print k
                if 'SYS_TOT' == k:
                    _his.add(k)
                elif 'SYS_pubs_HIS' == k:
                    # 统一合并
                    _his.add(k)
                else:
                    _idx = KV.get(k)
                    print "revert -> %s <- %s nodes"% (k, len(_idx) ) 
                    _his.add(k)
                    _his.update(set(_idx) )
                    #KV.set(CFG.K4D['his'], KV.get(CFG.K4D['his']).update(set(re_obj[k])) )
                    feed_back['msg'].append("%s >>> %s nodes"% (k, len(_idx) ) ) 

            KV.set(CFG.K4D['his'], list(_his) )
            #print KV.get(CFG.K4D['his'])




            feed_back['data'] = "re-merged all KVDB info into %s nodes"% len(_his)
        elif 'wx' ==  matter:
            print "try rebuild Passpord->UUID"
            # 根据 K4D['m'] 的索引,建立 成员 Passpord->UUID 的索引字典
            users = KV.get(CFG.K4D['m'])
            count = 0
            for m in users:
                upp = KV.get(m)['pp']
                #print "try: %s -> %s"%(m, upp)
                ppu = KV.get(upp)
                if not ppu:
                    count +=1
                    KV.add(upp, m)
            #KV.set(CFG.K4D['his'], list(_his) )
            #print KV.get(CFG.K4D['his'])
            feed_back['data'] = "re-point %s pp->UUID in %s Members"% (count, len(users))







            feed_back['msg'] = "re-build Passpord->UUID" 
        elif 'fw' ==  matter:
            print "reset SYS_fw_ALL [] --> {}"
            KV.set(CFG.K4D['fw'], {})
            feed_back['msg'] = "reset SYS_fw_ALL as {}" 
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("

@APP.delete('/cli/del/bk/<uuid>/<qstr>')
def del_bk(uuid, qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/del/bk/%s"% uuid, q_dict, "DELETE"):
        feed_back = {'data':[]}
        feed_back['msg'] = "deleted: %s"% uuid
        feed_back['data'].append( BK.stat_object(uuid) )
        BK.delete_object(uuid)
        return feed_back
    else:
        return "alert quary!-("

# collection wechat papers mana. matters
'''
'''
@APP.get('/cli/sum/p/<tag>/<qstr>')
def st_p_tag(tag, qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/sum/p/%s"% tag, q_dict, "GET"):
        feed_back = {'data':[]}
        #print tag
        all_papers = KV.get(CFG.K4D['p'])
        #print type(all_papers)
        all_papers.sort()
        tmp = {}
        for puuid in KV.get(CFG.K4D['p']):
            #print puuid, " --> ", KV.get(puuid)
            if tag ==  puuid[:2]:
                p = KV.get(puuid)
                #print p
                if 0 == p['del']:
                    exp = "%s:%-28s"%(p['code'], puuid)
                    tmp[exp] = p['title']
                    feed_back['data'].append(exp) 
        feed_back['data'].sort()
        for i in range(len(feed_back['data'])):
            k = feed_back['data'][i]
            feed_back['data'][i] = "%s%s"% (k, tmp[k])
        feed_back['msg'] = "%s papers had %s ."% (tag, len(feed_back['data']))
        return feed_back
        
    else:
        return "alert quary !-("

@APP.delete('/cli/del/p/<uuid>/<qstr>')
def del_p(uuid, qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/del/p/%s"% uuid, q_dict, "DELETE"):
        feed_back = {'data':[]}
        p = KV.get(uuid)
        p['del'] = 1
        KV.replace(uuid, p)
        feed_back['data'].append("%s:%s"% (p['code'],p['title']))
        feed_back['msg'] = "deleted: %s"% uuid
        return feed_back
    else:
        return "alert quary!-("

@APP.post('/cli/push/p/<qstr>')
def push_papers(qstr):
    q_dict = _query2dict(qstr)
    q_form = request.forms
    q_file = request.files.get('json')
    #f_name, f_ext = os_splitext(q_file.filename)
    #print f_name, f_ext
    set_var = q_file.file.read()
    if _chkQueryArgs("/cli/push/p", q_dict, "POST"):
        feed_back = {'data':[]}
        #set_key = list(set(q_form.keys())-set(CFG.SECURE_ARGS))[0]
        #set_var = base64.urlsafe_b64decode(request.forms[set_key])
        j = eval(set_var) #, set_var
        p_tag = j.keys()[0]
        #print j.keys()
        #return None
        for paper in j[p_tag]:
            uuid = GENID(p_tag)
            feed_back['data'].append(uuid)
            #print uuid
            new_paper = deepcopy(CFG.K4WD)
            new_paper['uuid'] = uuid # 对象创建时, 变更时间戳同 UUID
            new_paper['his_id'] = uuid
            new_paper['lasttm'] = time.time()
            new_paper['tag'] = p_tag
            new_paper['title'] = paper['title']
            new_paper['url'] = paper['uri']
            new_paper['picurl'] = paper['picuri']
            new_paper['code'] = paper['code']
            KV.add(uuid, new_paper)
            ADD4SYS('p', uuid)
            #print uuid, new_paper

        #feed_back['data'].append( BK.stat_object(sid) )
        feed_back['msg'] = "uploaded %s papers info."% len(j[p_tag])
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("



@APP.put('/cli/fix/p/<tag>/<uuid>')
def fix_paper(tag, uuid):
    q_dict = request.forms
    if _chkQueryArgs("/cli/fix/p/%s/%s"% (tag, uuid), q_dict, "PUT"):
        feed_back = {'data':[]}
        set_key = list(set(q_dict.keys())-set(CFG.SECURE_ARGS))[0]
        set_var = base64.urlsafe_b64decode(request.forms[set_key])
        print "\t", set_key
        print set_var
        #return None
        
        if set_key in CFG.K4WD.keys():
            print set_key, set_var
            uuid, pub = __chkPAPER(tag, uuid)
            if not uuid:
                feed_back['msg'] = "BAD tag: %s out pre-defined"% tag
            else:
                pub[set_key] = set_var.decode('utf-8')#注意将一切字串,变成 unicode 统一储存
                KV.replace(uuid, pub)
                #print pub
                feed_back['data'].append(pub)
                feed_back['uuid'] = uuid
        else:
            feed_back['msg'] = "out keys, NULL fixed!" 
            feed_back['can_fix_keys'] = CFG.K4WD.keys()
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("




def __chkPAPER(tag, uuid):
    '''chk or init. webchat paper:
        - if uuid == null init. node
        - else try get it
    '''
    paper = KV.get(uuid)
    if paper:
        print uuid, paper
        ADD4SYS('p', uuid)  # for old sys, collected uuid into idx node!
        return uuid, paper
    else:
        # inti.
        if tag not in CFG.ESSAY_TAG.keys():
            return None, None
        uuid = GENID(tag)
        if not uuid:
            print "tag out GENID() accept area!"
            return None, None
        ADD4SYS('p', uuid)
        new_paper = deepcopy(CFG.K4WD)
        new_paper['uuid'] = uuid
        new_paper['tag'] = tag
        new_paper['his_id'] = GENID('his')
        new_paper['lasttm'] = time.time()
        new_paper['title'] = "waiting set..."
        KV.add(uuid, new_paper)
        print uuid, new_paper
        return uuid, new_paper



        
        
@APP.put('/cli/fix/e/<code>')
def fix_event(code):
    '''events info. editor
    '''
    q_dict = request.forms
    if _chkQueryArgs("/cli/fix/e/%s"% code, q_dict, "PUT"):
        feed_back = {'data':[]}
        set_key = list(set(q_dict.keys())-set(CFG.SECURE_ARGS))[0]
        set_var = base64.urlsafe_b64decode(request.forms[set_key])
        if set_key in CFG.K4DM.keys():
            print set_key, set_var
            feed_back['msg'] = "func. not working now..." 
        else:
            feed_back['msg'] = "out keys, NULL fixed!" 
            feed_back['can_fix_keys'] = CFG.K4DM.keys()
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("

# collection usr ACL matter
'''
'''
@APP.get('/cli/find/m/<kword>/<qstr>')
def find_m(kword, qstr):
    #print request.query_string #query.keys()#.appkey
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/find/m/%s"% kword, q_dict, "GET"):
        feed_back = {'data':[]}
        print "find_m-> ", kword
        usrs = KV.get(CFG.K4D['m'])
        #print usrs
        for u in usrs:
            m = KV.get(u)
            m_info = "%s %s %s"%(m['em'].strip()
                , m['nm'].strip()
                , m['desc'].strip()
                )
            if kword in m_info.lower():
                feed_back['data'].append(m)
    
        feed_back['msg'] = "safe quary;-)"
        return feed_back
    else:
        return "alert quary!-("

@APP.put('/cli/fix/dm/<nm>')
def fix_dm(nm):
    q_dict = request.forms
    if _chkQueryArgs("/cli/fix/dm/%s"% nm, q_dict, "PUT"):
        feed_back = {'data':[]}
        set_key = list(set(q_dict.keys())-set(CFG.SECURE_ARGS))[0]
        set_var = base64.urlsafe_b64decode(request.forms[set_key])
        if set_key in CFG.K4DM.keys():
            #print set_key, set_var
            #print "<nm>", nm
            uuid, dm = __chkDAMA(nm.strip())
            #print uuid,dm
            if uuid:
                dm[set_key] = set_var.decode('utf-8')#注意将一切字串,变成 unicode 统一储存
                KV.replace(uuid, dm)
                feed_back['data'].append(dm)
                feed_back['uuid'] = uuid
        else:
            feed_back['msg'] = "out keys, NULL fixed!" 
            feed_back['can_fix_keys'] = CFG.K4DM.keys()
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("

@APP.put('/cli/fix/m/<uuid>')
def fix_member(uuid):
    q_dict = request.forms
    if _chkQueryArgs("/cli/fix/m/%s"% uuid, q_dict, "PUT"):
        feed_back = {'data':[]}
        set_key = list(set(q_dict.keys())-set(CFG.SECURE_ARGS))[0]
        set_var = base64.urlsafe_b64decode(request.forms[set_key])
        if set_key in CFG.K4DM.keys():
            print set_key, set_var
            feed_back['msg'] = "func. not working now..." 
            
        else:
            feed_back['msg'] = "out keys, NULL fixed!" 
            feed_back['can_fix_keys'] = CFG.K4DM.keys()
        #data.append(KV.get_info())
        return feed_back
    else:
        return "alert quary!-("

def __chkDMID(text):
    for DM in CFG.DM_ALIAS.keys():
        #print CFG.DM_ALIAS[DM]
        if text in CFG.DM_ALIAS[DM]:
            print "found DAMA!", CFG.DM_ALIAS[DM][0]
            return DM
    
    print "not march DAMA!"
    return None

def __chkDAMA(zipname):
    '''chk or init. webchat usr.:
        - gen KV uuid, try get
        - if no-exited, init. DM node
    '''
    k4dm = __chkDMID(zipname)
    if not k4dm:
        return None, None
    uuid = DAMAID(k4dm)
    ADD4SYS('dm', uuid)  # for old sys, collected uuid into idx node!
    usr = KV.get(uuid)
    if usr:
        #print uuid, usr
        return uuid, usr
    else:
        # inti.
        new_usr = deepcopy(CFG.K4DM)
        new_usr['his_id'] = uuid # 对象创建时, 变更时间戳同 UUID #GENID('his')
        new_usr['lasttm'] = time.time()
        new_usr['nm'] = CFG.DM_ALIAS[k4dm][0]
        KV.add(uuid, new_usr)
        #ADD4SYS('dm', uuid)
        #print uuid, new_usr
        return uuid, new_usr


# collection usr ACL matter
'''

  统计节点(任意)修订次数
    sum/his
  检阅最后一次节点(任意)修订
    his/last

'''
@APP.get('/cli/sum/his/<qstr>')
def sum_tag(qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/sum/his", q_dict, "GET"):
        data = []
        for u in CFG.HIS.find({}
            , {'_id':0, 'usrid':1, 'hisobj':1, 'uuid':1, 'actype':1}
            , limit=2):
            data.append(u)
        return {'msg':"safe quary;-)"
            , 'data':data
            , 'count': CFG.HIS.find({}).count()
            }
    else:
        return "alert quary!-("

@APP.get('/cli/his/last/<qstr>')
def sum_tag(qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/his/last", q_dict, "GET"):
        #data = []
        q_mongo = CFG.HIS.find({},{'_id':0},limit=1).sort("uuid", pymongo.DESCENDING)
        #print q_mongo[0] cPickle.loads('N.')
        return {'msg':"safe quary;-)"
            , 'data':q_mongo[0]
            , 'count': CFG.HIS.find({}).count()
            }
    else:
        return "alert quary!-("

'''FW flow:
 0.
usr> msg
<< if not cmd/number alert dd command.
>> stored msg
 1.
dm> aa 
<< list no-answer msg.
dm> mm[No.for msg]  ~ ingore point msg
dm> cc[No.for msg]  ~ answer sting
<< storded answer
<< mv UUID from SYS_fw_ALL -> SYS_pubs_HIS
 2.
usr> dd
<< echo dm answered msg

data relation:: SYS_fw_ALL is 2 level tree
writing:
    SYS_fw_ALL->{"UUID:usr":[UUID:fw msg.s,,,]}
为了在 FW 事务的 aa/mm 操作中, 对成员有简短的编号可用
    必须对字典的键对应上固定的序号!
    所以,使用临时字典内索引 "sequence"
cheking:
    Passpoord=>"UUID:usr"
                    ~> SYS_fw_ALL
                        ~> UUID:usr
                            +-> UUID::fw msg.s

CLI FW support:
+ GET sum/fw list all fw status
+ GET fw/dd/:uuid  as member flush answer

+ GET fw/ll  as DM flush member msg.s
+ PUT fw/mm/:zip  as DM cancel some msg.
+ PUT fw/aa/:zip aa="" as answer the questin
'''

@APP.get('/cli/fw/ll/<qstr>')
def fw_ll(qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/fw/ll", q_dict, "GET"):
        data = {}
        all_fw = KV.get(CFG.K4D['fw'])
        _seq = all_fw['sequence']
        # 立即重建临时索引 ???
        # KV.set(CFG.K4D['fw'],{'sequence':[]})
        #print type(_seq), _seq
        tot = 0
        #print type(all_fw['sequence']) -><type 'list'>
        
        for u in all_fw.keys():
            if 'sequence' == u:
                pass
            else:
                #print "%s as %s"% (u, _seq.index(u))
                if u in _seq:
                    usr_as = "usr~%s"% _seq.index(u)
                    data[usr_as] = []
                    print usr_as

                    tot += len(all_fw[u])
                    for k in all_fw[u]:
                        _fw = KV.get(k)
                        echo = "%s~%s %s"% ( all_fw[u].index(k)
                            , _fw['qa'][0]
                            , k )
                        #print echo , type(echo)
                        data[usr_as].append(echo)

                else:
                    print "需要清除的空 回复 容器" 
                    all_fw.pop(u)
                #break
                
        print all_fw
        return None    
        return {'msg':";-) as DM aa FWmsg.s"
            , 'data': data
            , 'count': "FW %s users %s msg.s"% (
                len(all_fw.keys())-1
                , tot)
            }
    else:
        return "alert quary!-("


@APP.put('/cli/fw/mm/<zip_id>')
def fw_mm(zip_id):
    q_dict = request.forms
    if _chkQueryArgs("/cli/fw/mm/%s"% zip_id, q_dict, "PUT"):
        data = []
        usr_as = base64.urlsafe_b64decode(q_dict['set'])
        _uid = int(usr_as)
        _zid = int(zip_id)
        
        all_fw = KV.get(CFG.K4D['fw'])
        _seq = all_fw['sequence']
        uuid_usr = _seq[_uid]
        uuid_fw = all_fw[uuid_usr][_zid]
        _fw = KV.get(uuid_fw)
        #print _fw
        _fw['dm'] = XCFG.AS_USR
        _fw['aa'] = 1
        _fw['del'] = 1
        _fw['his_id'] = GENID('his')#   stamp updated

        KV.set(uuid_fw, _fw)

        #<< storded answer
        #<< mv UUID from SYS_fw_ALL -> SYS_pubs_HIS
        # 从对应用户消息索引列表中清除
        all_fw[uuid_usr].remove(uuid_fw)
        if 0 == len(all_fw[uuid_usr]):
            # 如果已经为空,则从 sequence 内部索引中清除用户ID
            all_fw['sequence'].remove(uuid_usr)
            # 再整个清除用户消息UUID 关系对结点
            all_fw.pop(uuid_usr)
        #print all_fw
        #return None
        KV.set(CFG.K4D['fw'] ,all_fw)

        # 收录到历史全集索引
        his_all = KV.get(CFG.K4D['his'])
        his_all.append(uuid_fw)
        KV.set(CFG.K4D['his'] ,his_all)


        
        return {'msg':";-) as DM mm msg.s:%s~%s"%(_uid, uuid_fw)
            , 'data': _fw
            }
    else:
        return "alert quary!-("


@APP.put('/cli/fw/aa/<zid>')
def fw_aa(zid):
    q_dict = request.forms
    if _chkQueryArgs("/cli/fw/aa/%s"% zid, q_dict, "PUT"):
        data = []
        return None
        
        fw_keys = KV.get(CFG.K4D['fw'])
        for k in fw_keys:
            _fw = KV.get(k)
            echo = "%s~%s %s"% (fw_keys.index(k)
                , _fw['qa'][0]
                , k )
            #print echo 
            data.append(echo)
        return {'msg':";-) as DM aa FWmsg.s"
            , 'data':data
            , 'count': len(fw_keys)
            }
    else:
        return "alert quary!-("

@APP.get('/cli/fw/dd/<uuid>/<qstr>')
def fw_dd(uuid, qstr):
    q_dict = _query2dict(qstr)
    if _chkQueryArgs("/cli/fw/dd/%s"% uuid, q_dict, "GET"):
        #data = []
        return None
        q_mongo = CFG.HIS.find({},{'_id':0},limit=1).sort("uuid", pymongo.DESCENDING)
        #print q_mongo[0] cPickle.loads('N.')
        return {'msg':"safe quary;-)"
            , 'data':q_mongo[0]
            , 'count': CFG.HIS.find({}).count()
            }
    else:
        return "alert quary!-("

def __chkRegUsr(passport):
    '''chk or init. webchat usr.:
        - gen KV uuid, try get
        - if no-exited, init. fsm
    '''
    #sha1_name = hashlib.sha1(passport).hexdigest()
    uuid = USRID(passport)
    ADD4SYS('m', uuid)  # for old sys, collected uuid into idx node!
    usr = KV.get(uuid)
    # 检查反向索引键对
    ppu = KV.get(passport)
    if not ppu:
        # inti.
        KV.add(passport, uuid)
    # 检查用户键值对
    if usr:
        #print usr
        return usr
    else:
        # inti.
        new_usr = deepcopy(CFG.objUSR)
        new_usr['his_id'] = uuid # 对象创建时, 变更时间戳同 UUID
        new_usr['pp'] = passport
        new_usr['lasttm'] = time.time()
        new_usr['fsm'] = None
        KV.add(uuid, new_usr)
        #ADD4SYS('m', uuid)
        #print new_usr
        return new_usr






def __update_usr(objUsr):
    #sha1_name = hashlib.sha1(objUsr['pp']).hexdigest()
    uuid = USRID(objUsr['pp'])
    #   stamp updated
    objUsr['his_id'] = GENID('his')
    KV.replace(uuid, objUsr)



@APP.post('/echo/')
@APP.post('/echo')
def wechat_post():
    # usage jeff SDK for wechat...
    if CFG.AS_SAE:
        wxa = WxApplication(token=XCFG.TOKEN)
        chkwx = wxa.is_valid_params(request.query)
        if not chkwx:
            return None
    else:
        print "Debugging localhost..."
    ## 注意! 从公众号来的消息和订阅号完全不同的,需要另外解析!
    #print "request.forms.keys()[0]\t\n", request.forms.keys()[0]
    wxreq = WxRequest(request.forms.keys()[0])
    G_CRT_USR = __chkRegUsr(wxreq.FromUserName)
    wxreq.crt_usr = G_CRT_USR
    # usage pyfsm as FSM echo all kinds of usr ask
    weknow = pyfsm.Registry.get_task('weknow')
    #print G_CRT_USR
    wxreq.FSM = "start2" # 使用对象加载状态区分后续处理
    # 恢复用户 FSM 状态
    if G_CRT_USR['fsm']:
        #print "if G_CRT_USR"
        weknow.start2(G_CRT_USR['fsm'], wxreq)
    else:
        #print "else G_CRT_USR"
        weknow.start2('setup', wxreq)
        G_CRT_USR['fsm'] = "setup"
        __update_usr(G_CRT_USR)
    #return None
    # 执行用户 FSM 业务
    wxreq.FSM = "send2"
    return weknow.send2(wxreq.Content.strip(), wxreq)











@state('weknow')
@transition('e', 'events')
@transition('E', 'events')
@transition('re', 'reg_event')
@transition('rc', 'reg_cancel')
@transition('ri', 'reg_info')
@transition('i', 'info_me')
@transition('I', 'info_me')
@transition('me', 'info_me')
@transition('ei', 'edit_info')
@transition('s', 'seek')
@transition('S', 'seek')
@transition('h', 'helpme')
@transition('H', 'helpme')
@transition('?', 'helpme')
@transition('help', 'helpme')
@transition('V', 'version')
@transition('v', 'version')
@transition('version', 'version')
@transition('log', 'version')
@transition('st', 'status')
@transition('stat', 'status')
@transition('nn', 'niuniu')
def setup(self, wxreq):
    print 'setup->{h V e re rc ir i ei s}|大妈信息'
    if wxreq.FSM == "send2":
        # 使用对象加载状态 放弃 FSM 状态恢复时的回调 执行
        #print crt_usr['msg']
        #print wxreq.Content
        cmd = wxreq.Content
        # 只对非命令进行处理
        if cmd not in CFG.CMD_ALIAS:
            #if 8 > len(crt_usr['msg']):
            #print cmd
            if cmd.isdigit():
                pass    #忽略过程中的数字输入
            '''
            elif False not in [i in string.printable for i in cmd]:
                # 全部是 ASCII 字串
                if "::" == cmd[:2]:
                    print cmd[2:]
                    print dir()

            '''
            #print len(cmd)
            if 8 > len(cmd):
                print "try march dama"
                uuid, dm = __chkDAMA(cmd)
                if uuid:
                    #print dm
                    msg = CFG.TXT_CRT_DM% (dm['nm'], dm['desc'])
                    return WxTextResponse(msg, wxreq).as_xml()


            else:
                usr_pp = wxreq.FromUserName
                if usr_pp in XCFG.P__DM:    #XCFG.WX_DM:
                    print "FW2DM >>> is ZQ self"
                    pass
                else:
                    print "FW2DM >>> is usr"
                    #print cmd, type(cmd.decode('utf-8'))    #注意将一切字串,变成 unicode 统一储存
                    print __putFW(usr_pp, cmd.decode('utf-8'))
                    
                #pub[set_key] = set_var.decode('utf-8')
                
                #print "FSM::setup()->cmd.decode ", type(cmd.decode('utf-8'))
                #return None
                if 0:
                    access_token = _wx_token_get()
                    wx_uri = 'wx/msg'
                    host = CFG.CLI_URI[wx_uri][0]
                    url = CFG.CLI_URI[wx_uri][1]    #"%s=%s"% (CFG.CLI_URI[wx_uri][1], access_token)

                    openid = XCFG.WX_ZQ
                    print cmd
                    print "<<< type(cmd) ", type(cmd)
                    content = cmd.decode('utf-8') #CFG.VERSION #u'#细思恐极....'#cmd.decode('utf-8') #_msg 
                    print "<<< cmd.decode", type(cmd.decode('utf-8'))
                    cc_msg = CFG.SRV_TXT_JSON% locals()
                    print "<<< type(cc_msg)", type(cc_msg)
                    print cc_msg

                    data = _https_post(host
                        , url
                        , cc_msg  #bytearray(_msg.encode('utf-8'))
                        , token = access_token
                        )
                    print "_https_post()>>> ", data




        '''FW flow:
         0.
        usr> msg
        << if not cmd/number alert dd command.
        >> stored msg
         1.
        dm> aa 
        << list no-answer msg.
        dm> mm[No.for msg]  ~ ingore point msg
        dm> cc[No.for msg]  ~ answer sting
        << storded answer
        << mv UUID from SYS_fw_ALL -> SYS_pubs_HIS
         2.
        usr> dd
        << echo dm answered msg

        data relation:: SYS_fw_ALL is 2 level tree
        writing:
            SYS_fw_ALL->{"UUID:usr":[UUID:fw msg.s,,,]}
        为了在 FW 事务的 aa/mm 操作中, 对成员有简短的编号可用
            必须对字典的键对应上固定的序号!
            所以,使用临时字典内索引 "sequence"
        cheking:
            Passpoord=>"UUID:usr"
                            ~> SYS_fw_ALL
                                ~> UUID:usr
                                    +-> UUID::fw msg.s

        CLI FW support:
        + GET sum/fw list all fw status
        + GET fw/dd/:uuid  as member flush answer

        + GET fw/ll  as DM flush member msg.s
        + PUT fw/mm/:zip  as DM cancel some msg.
        + PUT fw/aa/:zip aa="" as answer the questin
        '''







#@transition('::', 'docechor')

@state('weknow')
def end(self, wxreq):
    print '...->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    return None





def __putFW(pp, msg):
    '''chk or push usr msg.'s UUID into CFG.K4D['FW']:
        - usage pp as UUID 
        - deepcopy tpl. for obj.
        - return UUID:usr and obj.
    CFG.K4D['fw'] means:{}
    '''
    fw_uuid = GENID('fw')
    # inti.
    new_fw = deepcopy(CFG.K4FW)
    new_fw['his_id'] = fw_uuid # 对象创建时, 变更时间戳同 UUID
    new_fw['qa'].append(msg)
    #print uuid, new_fw
    KV.add(fw_uuid, new_fw)

    #uuid = GENID('fw')
    uuid = KV.get(pp)
    print "pp->uuid:: ", uuid
    all_fw = KV.get(CFG.K4D['fw'])
    if uuid not in all_fw.keys():
        all_fw[uuid] = []
    all_fw[uuid].append(fw_uuid)
    
    tmp_seq = all_fw['sequence'] # 为内部用户临时索引,为了精简码号
    #all_fw['sequence'] = []
    tmp_seq.append(uuid)
    all_fw['sequence'] = list(set(tmp_seq))
    #print all_fw
    #ADD4SYS('fw', uuid) 是双层结构了!
    return uuid, new_fw

'''K4FW = {"his_id":""   # 更新戮
    , "del":0
    , "aa":0    # 是否回答了
    , "dm":""   # 回答的大妈 uuid
    , "qa":[]   # [0]<- 消息,[1]<-回答 
    }
'''



@state('weknow')
@transition('gb', 'papers')
@transition('dd', 'papers')
@transition('gt', 'papers')
@transition('dm', 'papers')
@transition('hd', 'papers')
@transition('et', 'papers')
@transition('ot', 'papers')
@transition('q', 'helpme')
@transition('Q', 'helpme')
@transition('h', 'helpme')
@transition('H', 'helpme')
def seek(self, wxreq):
    print 'setup->seek->{gb dd gt dm ot q h} '
    crt_usr = wxreq.crt_usr
    #print "G_CRT_USR", crt_usr
    if wxreq.Content in CFG.PAPER_TAGS:
        crt_usr['fsm'] = "papers"
        __update_usr(crt_usr)
        return WxTextResponse(CFG.TXT_PLS_TAG, wxreq).as_xml()
    else:
        crt_usr['fsm'] = "seek"
        __update_usr(crt_usr)
        return WxTextResponse(CFG.TXT_OUT_TAG, wxreq).as_xml()


@state('weknow')
@transition('no', 'no_paper')
@transition('q', 'helpme')
@transition('Q', 'helpme')
@transition('h', 'helpme')
@transition('H', 'helpme')
def papers(self, wxreq):
    print 'setup->seek->[papers]->no'
    crt_usr = wxreq.crt_usr
    tag = wxreq.Content
    count = 0
    papers4tag = []
    if tag in CFG.ESSAY_TAG.keys():
        # right tag switch
        uuid_all_paper = KV.get(CFG.K4D['p'])
        for uuid in uuid_all_paper:
            # sometime reg. uuid as None
            if uuid and uuid[:2] == tag:
                paper =  KV.get(uuid)
                if 0 == paper['del']:
                    count += 1
                    #print paper['title']
                    #papers4tag.append((str(paper['code']),paper['title']))
                    #print paper['title']
                    #print type(paper['title'])
                    if isinstance(paper['title'], unicode):
                        #print '%s is a unicode object'%paper['title']
                        crt_title = paper['title'].encode('utf-8')
                        #print type(crt_title)
                    else:
                        #print '%s is a str object'%paper['title']
                        crt_title = paper['title']
                    papers4tag.append((int(paper['code']), crt_title))
                    #print paper['title'].enconde('utf-8')
                    #AttributeError: 'str' object has no attribute 'encode'
        #return None
        #print "count ", count
        if 0 == count:
            # not paper in the tag yet
            crt_usr['fsm'] = "setup"
            crt_usr['buffer'] = ""
            __update_usr(crt_usr)
            return WxTextResponse(CFG.TXT_PUB_WAIT, wxreq).as_xml()
        else:
            # waiting paper Number code, jump into FSM:number_paper
            #for p in papers4tag: print p
            papers4tag.sort()
            #return None
            p_list = "    ".join(["%s: %s\n"%(p[0], p[1]) for p in papers4tag])
            crt_usr['fsm'] = "number_paper"
            crt_usr['buffer'] = tag
            __update_usr(crt_usr)
            return WxTextResponse(CFG.TXT_TAG_PAPERS% (CFG.ESSAY_TAG[tag]
                , p_list.decode('utf-8')), wxreq).as_xml()
            
    else:    
        crt_usr['fsm'] = "papers"
        __update_usr(crt_usr)
        return WxTextResponse(CFG.TXT_PLS_TAG, wxreq).as_xml()

    return None
    
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    return WxTextResponse(CFG.TXT_PUB_WAIT, wxreq).as_xml()


@state('weknow')
@transition('end', 'end')
@transition('q', 'helpme')
@transition('Q', 'helpme')
@transition('h', 'helpme')
@transition('H', 'helpme')
def number_paper(self, wxreq):
    print 'setup->seek->...->no->end'
    crt_usr = wxreq.crt_usr
    code = wxreq.Content
    #print code, code.isdigit()
    if code.isdigit():
        print "exp URI xml..."
        #print code
        tag = crt_usr['buffer']
        resp = None
        for puuid in KV.get(CFG.K4D['p']):
            # 根据指定的类别,逐一从文章索引中过滤出指定代号的文章
            # 要求, del==0 && code==指定数
            if tag == puuid[:2]:
                p = KV.get(puuid)
                #print p['code'], "\n\t", p
                if 0 == p['del']:
                    if int(code) == int(p['code']):
                        #print p
                        resp = WxNewsResponse([WxArticle(p['title'],
                                    Description="",
                                    Url=p['url'],
                                    PicUrl=p['picurl'])], wxreq).as_xml()
                        #return resp
                        break


        #return None
        crt_usr['fsm'] = "setup"
        __update_usr(crt_usr)
        if resp:
            return resp
        else:
            return WxTextResponse("图文消息返回异常,议案吼 大妈!", wxreq).as_xml()
    else:
        crt_usr['fsm'] = "number_paper"
        __update_usr(crt_usr)
        return WxTextResponse(CFG.TXT_PLS_INT, wxreq).as_xml()
        
        return __echo_txt(crt_usr['fromUser']
            , crt_usr['toUser']
            , CFG.TXT_PLS_INT
            )

'''
resp = WxNewsResponse([WxArticle(Title="iPhone 6 is here!",
                        Description="It is not a joke",
                        Url="http://jeffkit.info",
                        PicUrl="http://jeffkit.info/avatar.jpg")], wxreq).as_xml()
                        
'''

'''
WxNewsResponse, WxArticle
resp = WxNewsResponse([WxArticle(Title="iPhone 6 is here!",
                        Description="It is not a joke",
                        Url="http://jeffkit.info",
                        PicUrl="http://jeffkit.info/avatar.jpg")], wxreq).as_xml()
'''

    
@state('weknow')
@transition('q', 'helpme')
@transition('Q', 'helpme')
@transition('h', 'helpme')
@transition('H', 'helpme')
def info_me(self, wxreq):
    print 'setup->info_me->end'
    crt_usr = wxreq.crt_usr
    #print "wxreq.crt_usr: ", crt_usr
    #print crt_usr['fsm']
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    if "" == crt_usr['em']:
        # not set info. yet
        return WxTextResponse(CFG.TXT_NO_INIT, wxreq).as_xml()
        return __echo_txt(crt_usr['fromUser']
            , crt_usr['toUser']
            , CFG.TXT_NO_INIT
            )
    else:
        msg = CFG.TXT_CRT_ME% (crt_usr['nm'], crt_usr['em'])
        return WxTextResponse(msg, wxreq).as_xml()
        return __echo_txt(crt_usr['fromUser']
            , crt_usr['toUser']
            , CFG.TXT_CRT_ME% (crt_usr['nm'].encode('utf-8'), crt_usr['em'])
            )


@state('weknow')
@transition('ia', 'info_alias')
@transition('q', 'helpme')
@transition('Q', 'helpme')
@transition('h', 'helpme')
@transition('H', 'helpme')
def edit_info(self, wxreq):
    print 'setup->edit_info->info_alias 提醒输入妮称'
    crt_usr = wxreq.crt_usr
    print "edit_info::", wxreq.Content   #crt_usr['msg']
    crt_usr['fsm'] = "info_alias"
    __update_usr(crt_usr)
    return WxTextResponse(CFG.TXT_PLS_ALIAS, wxreq).as_xml()
        
    return __echo_txt(crt_usr['fromUser']
        , crt_usr['toUser']
        , CFG.TXT_PLS_ALIAS
        )

'''    if isinstance(crt_usr['msg'], unicode):
        print "可能是中文"
        crt_usr['fsm'] = "edit_info"
        return __echo_txt(crt_usr['fromUser']
            , crt_usr['toUser']
            , CFG.TXT_PLS_EN4NM
            )
    else:
'''    


@state('weknow')
@transition('im', 'info_mail')
@transition('q', 'helpme')
@transition('Q', 'helpme')
@transition('h', 'helpme')
@transition('H', 'helpme')
def info_alias(self, wxreq):
    print 'setup->edit_info->info_alias->info_mail 提醒输入邮箱'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "info_mail"
    crt_usr['nm'] = wxreq.Content   #crt_usr['msg']
    __update_usr(crt_usr)
    return WxTextResponse(CFG.TXT_PLS_EM, wxreq).as_xml()
    
    return __echo_txt(crt_usr['fromUser']
        , crt_usr['toUser']
        , CFG.TXT_PLS_EM
        )

@state('weknow')
@transition('q', 'helpme')
@transition('Q', 'helpme')
@transition('h', 'helpme')
@transition('H', 'helpme')
def info_mail(self, wxreq):
    print 'setup->edit_info->info_alias->info_mail->end 回报收集的'
    crt_usr = wxreq.crt_usr
    print "info_mail::", wxreq.Content  #crt_usr['msg']
    #if "@" in crt_usr['msg']:
    if "@" in wxreq.Content.strip():
        print "get user em.."
        crt_usr['em'] = "+".join(wxreq.Content.strip().split())   #crt_usr['msg']
        crt_usr['fsm'] = "setup"
        __update_usr(crt_usr)
        
        msg = CFG.TXT_DONE_EI% (crt_usr['nm'], crt_usr['em'])
        return WxTextResponse(msg, wxreq).as_xml()
    
        return __echo_txt(crt_usr['fromUser']
            , crt_usr['toUser']
            , CFG.TXT_DONE_EI% (crt_usr['nm'].encode('utf-8'), crt_usr['em'])
            )
    else:
        print "error emil format?"
        crt_usr['fsm'] = "info_mail"
        __update_usr(crt_usr)
        #print WxTextResponse(CFG.TXT_REALY_EM, wxreq).as_xml()
        return WxTextResponse(CFG.TXT_REALY_EM, wxreq).as_xml()
    
        return __echo_txt(crt_usr['fromUser']
            , crt_usr['toUser']
            , CFG.TXT_REALY_EM
            )

'''
Traceback (most recent call last):
  File "/data1/www/htdocs/466/weknow/3/bottle.py", line 764, in _handle
    return route.call(**args)
  File "/data1/www/htdocs/466/weknow/3/bottle.py", line 1575, in wrapper
    rv = callback(*a, **ka)
  File "/data1/www/htdocs/466/weknow/3/web/mana4api.py", line 76, in wechat_post
    weknow.start2(G_CRT_USR['fsm'], wxreq)
  File "/data1/www/htdocs/466/weknow/3/3party/pyfsm.py", line 284, in start2
    return self.current_state.enter2(self, obj)
  File "/data1/www/htdocs/466/weknow/3/3party/pyfsm.py", line 444, in enter2
    return self.func(task, obj)
  File "/data1/www/htdocs/466/weknow/3/web/mana4api.py", line 357, in info_mail
    print WxTextResponse(CFG.TXT_REALY_EM, wxreq).as_xml()
UnicodeEncodeError: 'ascii' codec can't encode character u'\u4eb2' in position 236: ordinal not in range(128) yq30 
'''



@state('weknow')
@transition('end', 'end')
def niuniu(self, wxreq):
    print 'setup->niuniu->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    _today = datetime.now()
    return WxTextResponse(CFG.TXT_NN% (_today-CFG.NIUNIU).days, wxreq).as_xml()

@state('weknow')
@transition('end', 'end')
def docechor(self, wxreq):
    print 'setup->docechor->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    code = wxreq.Content
    print code
    return None
    _today = datetime.now()
    return WxTextResponse(CFG.TXT_NN% (_today-CFG.NIUNIU).days, wxreq).as_xml()

@state('weknow')
@transition('end', 'end')
def events(self, wxreq):
    print 'setup->events->end'
    crt_usr = wxreq.crt_usr
    print "crt_usr['fsm']~~", crt_usr['fsm']
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    return WxTextResponse(CFG.TXT_EVENT_NULL, wxreq).as_xml()


@state('weknow')
@transition('end', 'end')
def reg_event(self, crt_usr):
    print 'setup->reg_event->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)




@state('weknow')
@transition('end', 'end')
def reg_cancel(self, crt_usr):
    print 'setup->reg_cancel->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)



@state('weknow')
@transition('end', 'end')
def reg_info(self, crt_usr):
    print 'setup->info_reg->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)



@state('weknow')
@transition('end', 'end')
def helpme(self, wxreq):
    print 'setup->helpme->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    return WxTextResponse(CFG.TXT_HELP, wxreq).as_xml()
    
    return __echo_txt(crt_usr['fromUser']
        , crt_usr['toUser']
        , CFG.TXT_HELP
        )


@state('weknow')
@transition('end', 'end')
def status(self, wxreq):
    print 'setup->status->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    _msg = ""   #u"是也乎 "
    #_msg += "\nget_info()-> "+str(KV.get_info())
    _INX_KEYS = [CFG.K4D[k] for k in CFG.K4D.keys()]
    for k in _INX_KEYS:
        # 索引键处理
        if 'SYS_TOT' == k:
            _msg += u"\n SYS_TOT::"+str(KV.get(k))
        else :
            # 统一合并
            _msg += u"\n %s :: %snodes"%(k, len(KV.get(k)))

    #print "pp2u-->", KV.get(KV.get('oFNShjiOhclfJ-CtOO81p2sPrBfs'))
    _msg += "\n\t FromUserName:: %s"% wxreq.FromUserName
    _msg += "\n\t ToUserName:: %s"% wxreq.ToUserName
    
    return WxTextResponse(_msg, wxreq).as_xml()
    
    # 确认订阅号无法指向发送
    wxreq.FromUserName = XCFG.WX_ZQ
    print "rewrite as onoK2t_msg>>> %s"% wxreq.FromUserName
    print WxTextResponse(_msg, wxreq).as_xml()
    
    return __echo_txt(crt_usr['fromUser']
        , crt_usr['toUser']
        , KV.get_info()
        )

    #_msg += "\n\t usr:: %s"% crt_usr
    #_msg += "\n\t FromUserName:: %s"% wxreq.FromUserName
    #_msg += "\n\t ToUserName:: %s"% wxreq.ToUserName
    #return WxTextResponse(_msg, wxreq).as_xml()
    #    access_token = _wx_token_get()
    wx_uri = 'wx/msg'
    host = CFG.CLI_URI[wx_uri][0]
    url = CFG.CLI_URI[wx_uri][1]    #"%s=%s"% (CFG.CLI_URI[wx_uri][1], access_token)

    openid = XCFG.WX_ZQ
    content = _msg  #u'#细思恐极....'
    cc_msg = CFG.SRV_TXT_JSON% locals()
    print cc_msg
    data = _https_post(host
        , url
        , cc_msg  #bytearray(_msg.encode('utf-8'))
        , token = access_token
        )
    print data






@state('weknow')
@transition('end', 'end')
def version(self, wxreq):
    print 'setup->version->end'
    crt_usr = wxreq.crt_usr
    crt_usr['fsm'] = "setup"
    __update_usr(crt_usr)
    return WxTextResponse(CFG.TXT_VER, wxreq).as_xml()

    return __echo_txt(crt_usr['fromUser']
        , crt_usr['toUser']
        , CFG.TXT_VER
        )

def _https_post(uri, tpl, values, **args):
    '''esp. HTTPSConnection only POST bytearray, means:
    - values MUST 'unicode'
    '''
    url = "https://%s%s"% (uri, tpl % args)
    print url
    #return None
    data = bytearray(values.encode('utf-8'))    #urllib.urlencode(values)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    #print dir(response)
    #return None
    print response.code, response.msg
    result = response.read()
    print result
    return result
    
    ##########################################################
    
    c = httplib.HTTPSConnection(uri, 443)
    print uri
    values = "123123"
    print tpl % args
    c.request("POST"
        , tpl % args
        , bytearray(values.encode('utf-8'))
        #values#.encode('utf-16be') #.decode("utf-8")
        #, {'Content-Type': 'text/plain; charset=utf-8'}
        )
    #return None
    response = c.getresponse()
    print response.status, response.reason
    data = response.read()
    return data
    
    
    
'''
conn = httplib.HTTPSConnection(host='www.site.com', port=443, cert_file=_certfile)
   params  = urllib.urlencode({'cmd': 'token', 'device_id_st': 'AAAA-BBBB-CCCC',
                                'token_id_st':'DDDD-EEEE_FFFF', 'product_id':'Unit Test',
                                'product_ver':"1.6.3"})
    conn.request("POST", "servlet/datadownload", params)
    content = conn.getresponse().read()
    #print response.status, response.reason
    conn.close()
'''
def _wx_token_get():
    data = _https_get(CFG.CLI_URI['wx/t'][0]
        , CFG.CLI_URI['wx/t'][1]
        , appid = XCFG.WX_APPID
        , secret = XCFG.WX_SECRET
        )
    print data
    js = json.loads(data)
    print js
    print "access_token: ", js['access_token']
    return js['access_token']


def _https_get(uri, tpl, **args):
    c = httplib.HTTPSConnection(uri)
    #print args
    c.request("GET", tpl % args)
    response = c.getresponse()
    #print response.status, response.reason
    data = response.read()
    return data
def __echo_txt(fromUsr, toUsr, text):
    '''zip xml exp.
    '''
    tStamp = int(time.time())    #TSTAMP()
    fromUser = fromUsr
    toUser = toUsr
    content = text
    print CFG.TPL_TEXT% locals()
    return CFG.TPL_TEXT% locals()

@APP.route('/sysincr')
#@APP.route('/<ddd>/sysincr')
def sysincr():
    from utility import INCR4KV as __incr
    #kv = sae.kvdb.KVClient()
    #print  kv.get_info()
    return str(__incr())
    
    '''
    kv = sae.kvdb.KVClient()
    print dir(kv)
    print kv.get_info()
    print kv.get("TOT")
    
    if not kv.get("TOT"):
        kv.add("TOT", 1)
    print kv.get("TOT")
    print type(kv.get("TOT")+1)
    
    kv.replace("TOT",kv.get("TOT")+1)
    print kv.get("TOT")
    
    return str(kv.get("TOT"))
    '''



#@view('404.html')
@APP.error(404)
def error404(error):
    return '''


\          SORRY            /
 \                         /
  \    This page does     /
   ]   not exist yet.    [    ,'|
   ]                     [   /  |
   ]___               ___[ ,'   |
   ]  ]\             /[  [ |:   |
   ]  ] \           / [  [ |:   |
   ]  ]  ]         [  [  [ |:   |
   ]  ]  ]__     __[  [  [ |:   |
   ]  ]  ] ]\ _ /[ [  [  [ |:   |
   ]  ]  ] ] (#) [ [  [  [ :===='
   ]  ]  ]_].nHn.[_[  [  [
   ]  ]  ]  HHHHH. [  [  [
   ]  ] /   `HH("N  \ [  [
   ]__]/     HHH  "  \[__[
   ]         NNN         [
   ]         N/"         [
   ]         N H         [
  /          N            \

/                           \

roaring zoomquiet+404@gmail.com
'''
#    return template('404.html')

@APP.route('/favicon.ico')
def favicon():
    abort(204)
    
@APP.route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='static')
    






