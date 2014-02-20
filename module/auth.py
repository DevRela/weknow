# -*- coding: utf-8 -*-
'''base: ms4py / bottle-wiki / source — Bitbucket
	https://bitbucket.org/ms4py/bottle-wiki/src/1586473a6ce1/auth.py
'''
import sys
from time import time, gmtime, strftime, localtime
import base64
import urllib2 as urilib
from base64 import urlsafe_b64encode

from hashlib import md5
from hashlib import sha256
from functools import partial

from bottle import request, HTTPError

from config import CFG
KV = CFG.KV
from xsettings import XCFG

def sha256_uhex(data):
    ''' Generates unicode hex value of given data with SHA-256. '''
    return str(unicode(sha256(data).hexdigest()))
def check_login(username, password, fullpath):
    '''根据用户名,以及口令:
        - 明确是否登录
        - 明确是否有当前级别的权限!
    '''
    pw_hash = sha256_uhex(password)
    suname = sha256_uhex(username)
    usrid = "%s%s"% (CFG.PREUID, suname)
    crtusr = KV.get(usrid)
    #print fullpath.split("/")[1]
    #print type(CFG.LEVEL4USR[fullpath.split("/")[1]])
    #print type(crtusr['level'])
    if crtusr:
        crtPathLevel = CFG.LEVEL4USR[fullpath.split("/")[1]]
        if str(crtPathLevel) == str(crtusr['level']):
            print "'%s' had crt. path right ;-)"% username
            return True
        else:
            print "'%s' disallow crt. path ;-("% username
            return False
    else:
        print "'%s' NOT exist!"% username
        return False
    '''
    #print fullpath.split("/")[1]
    print CFG.LEVEL4USR[fullpath.split("/")[1]]
    usr = 1#KV.get("usr:%s"% str(sha256_uhex(username.decode('utf-8'))))
    if usr is None:
        return False
    #return usr.password == pw_hash
    return 1
    '''

def auth_required(check_func=check_login, realm='bottle-authentication'):
    """
    Decorator for basic authentication. 
    
    "check_func" has to be a callable object with two 
    arguments ("username" and "password") and has to return 
    a bool value if login was sucessful or not.
    """
    def decorator(view):
        def wrapper(*args, **kwargs):
            try:
                user, password = request.auth
            except (TypeError, AttributeError):
                # catch AttributeError because of bug in bottle
                auth = False
            else:
                auth = check_login(user, password, request.fullpath)
                #print "\t path: ", request.keys()
                #print request.fullpath
            if auth:
                return view(*args, **kwargs)
            return HTTPError(401, 'Access denied!', 
                header={'WWW-Authenticate': 'Basic realm="%s"' % realm})
        return wrapper
    return decorator

def _genArgsStr(api_path, args):
    key_values = ["%s=%s"% (arg[0], arg[1]) for arg in args]
    base_string = api_path + "/" + "&".join(key_values)
    return base_string

def _genQueryArgs(api_matter, q="", rest_method="GET"):
    '''单向加密服务端核查:
        - [MatterURI] ~= cli/usr/info/<uuid> 不必包含http 域名部分
        - sign 制作:
            - GET 时将[MatterURI]/appkey_值--ts_值 参数字串缀上密文 md5 成 
            - POST 时 [MatterURI]为uri 提交时数据拼为仿GET字串 md5 成
        - 服务端使用相同算法,生成 sign 对比,并明确请求在 CFG.STLIMI 秒之内发生        
        - 注意! 参数的次序必须固定: 
            - appkey->ts->[q]->sign
            - appkey=***&ts=***&sign=***
            - 整体作base64.urlsafe_b64encode()包裹
        - GET/DELETE 时将参数拼为统一联合字串
        - PUT/POST 时提交唯一数据,同 GET 时的参数字串结构
    '''
    #print "_genQueryArgs as:", rest_method
    matter = "%s/%s"% (CFG.APIPRE, api_matter)
    args = []
    args.append(("appkey", XCFG.APPKEY ))
    args.append(("ts", "%.3f" % (time()) ))
    if 'PUT' == rest_method:
        if not q:
            print "缺少 set=*** 设定值"
            return None
        q_args = q.split("=")   
        #对于值中包含类似 appmsg/show?__biz=MjM$sign=sdfsfd .. 形式就失常了!
        #print "=".join(q_args[1:])
        #args.append((q_args[0], base64.urlsafe_b64encode(q_args[1])))
        args.append((q_args[0], base64.urlsafe_b64encode(
                        "=".join(q_args[1:]) 
                        )
                    ))
        
    # GET|POST|DELETE 一般不提交额外数据
    sign_base_string = _genArgsStr(matter, args)
    args.append(("sign"
        , md5(sign_base_string + XCFG.SECRET).hexdigest()))
    return args


'''
    if rest_method in ['GET', 'DELETE']:
        pass
        args.append(("sign"
            , md5(sign_base_string + XCFG.SECRET).hexdigest()))
    elif 'PUT' == rest_method:
        if not q:
            print "缺少 set=*** 设定值"
            return None
        q_args = q.split("=")
        args.append((q_args[0], base64.urlsafe_b64encode(q_args[1])))
        print args
    else:
        # POST cat not set=***
        pass
        #sign_base_string = _genArgsStr(matter, args)
        args.append(("sign"
            , md5(sign_base_string + XCFG.SECRET).hexdigest()))
    args.append(("sign"
        , md5(sign_base_string + XCFG.SECRET).hexdigest()))
    print args
    return args

'''


def _query2dict(qstr):
    q_dict = {}
    for q in base64.urlsafe_b64decode(qstr).split("&"):
        item = q.split("=")
        q_dict[item[0]] = item[1]
    return q_dict
def _chkQueryArgs(api_matter, q, rest_method="GET"):
    '''单向加密服务端核查:
        - [MatterURI] ~= cli/usr/info/<uuid> 不必包含http 域名部分
        - sign 制作:
            - GET 时将[MatterURI]/appkey_值--ts_值 参数字串缀上密文 md5 成 
            - POST 时 [MatterURI]为uri 提交时数据拼为仿GET字串 md5 成
        - 服务端使用相同算法,生成 sign 对比,并明确请求在 CFG.STLIMI 秒之内发生        
        - 注意! 参数的次序必须固定: 
            - appkey->ts->[q]->sign
            - appkey=***&ts=***&sign=***
            - 整体作base64.urlsafe_b64encode()包裹
        - GET/DELETE 时将参数拼为统一联合字串
        - PUT/POST 时提交唯一数据,同 GET 时的参数字串结构
    '''
    matter = api_matter #"%s/%s"% (CFG.APIPRE, api_matter)
    args = []
    args.append(("appkey", q['appkey'] ))
    args.append(("ts", q['ts'] ))
    #print rest_method
    if rest_method in ['GET', 'DELETE']:
        sign_base_string = _genArgsStr(matter, args)
        re_sign = md5(sign_base_string + XCFG.SECRET).hexdigest()
        chk_sign = (re_sign == q['sign'])
        chk_time = (CFG.STLIMI>float("%.3f" % (time())) - float(q['ts']))
    else:
        # POST PUT
        for k in q.keys():
            if k not in ['appkey', 'ts', 'sign']:
                args.append((k, q[k] ))
        sign_base_string = _genArgsStr(matter, args)
        re_sign = md5(sign_base_string + XCFG.SECRET).hexdigest()
        #print "getsign\t", q['sign']
        #print "re_sign\t", re_sign
        chk_sign = (re_sign == q['sign'])
        chk_time = (CFG.STLIMI>float("%.3f" % (time())) - float(q['ts']))
        #print api_matter, q
    return chk_time&chk_sign
    #return "debug"


