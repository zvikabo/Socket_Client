#!/usr/bin/python3

import requests
import json
import datetime
from time import sleep

# ======================  ppv client for testing ==============================================================
v_url_ppv = 'http://KFS-APP-LNX:8070/api/v1/ppv'
f = {'connid': '0128031c21578752', 'EV': '553403'}
v_param_ppv = {'content-type': 'application/json', 'content': f}

def send_request(url, params):
    try:
        send_time = (datetime.datetime.now())
        print('Send time time : ', send_time)
        res = requests.get(url, json=params, timeout=60)
        print(res.content.decode('utf-8'))
        response_time = (datetime.datetime.now())
        print('response time : ', response_time)
        print('Time left = ', (response_time - send_time))

    except Exception as e:
        print('Error :   ', e)

def main():


    print('send time    : ',  datetime.datetime.now())
    print(f)
    r=send_request(v_url_ppv, v_param_ppv)
    print(r)

if __name__ == '__main__':
    main()