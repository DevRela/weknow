# -*- coding: utf-8 -*-
import sae
import config
from bottle import debug, run
from web import APP

application = sae.create_wsgi_app(APP)

'''
import sae
import config
from bottle import debug, run
from web import APP

application = sae.create_wsgi_app(APP)


from bottle import *
import sae

APP = Bottle()
application = sae.create_wsgi_app(APP)

@APP.get('/echo')
@APP.get('/echo/')
def echo_wechat():
    print request.query.keys()
    print request.query.echostr
    return request.query.echostr

'''
