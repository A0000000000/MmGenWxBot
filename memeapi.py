import config
import requests
import json
import uuid
import os
from threading import Thread

import log

keys_list = []
TAG = 'memeapi'


def get_keys():
    log.logi(TAG, 'get_keys')
    keys = []
    for i in keys_list:
        keys.append(i['key'])
    return keys


def get_keys_by_server():
    log.logi(TAG, 'get_keys_by_server')
    url = config.get_base_http_path() + '/' + 'keys'
    res = requests.get(url)
    keys = json.loads(res.text)
    return keys


def get_keyinfo(key):
    log.logi(TAG, 'get_keyinfo - key is ' + key)
    for i in keys_list:
        if i['key'] == key:
            return i
        for j in i['keywords']:
            if j == key:
                return i

    for i in keys_list:
        for j in i['keywords']:
            if j in key or key in j:
                return i
    return None


def get_keyinfo_by_server(key):
    log.logi(TAG, 'get_keyinfo_by_server - key is ' + key)
    url = config.get_base_http_path() + '/' + key + '/info'
    res = requests.get(url)
    obj = json.loads(res.text)
    return obj


def gen_gen_pic(params):
    log.logi(TAG, 'gen_gen_pic params = ' + str(params))
    url = config.get_base_http_path() + '/' + params['key'] + '/'
    images = []
    if len(params['texts']) > 0 and len(params['images']) > 0:
        for img in params['images']:
            images.append(('images', (img, open(img, 'rb'), 'image/' + img.split('.')[-1], {})))
        res = requests.post(url, data={
            'texts': params['texts'],
            'args': json.dumps(params['args'])
        }, files=images)
    elif len(params['texts']) > 0:
        res = requests.post(url, data={
            'texts': params['texts'],
            'args': json.dumps(params['args'])
        })
    elif len(params['images']) > 0:
        for img in params['images']:
            images.append(('images', (img, open(img, 'rb'), 'image/' + img.split('.')[-1], {})))
        res = requests.post(url, files=images, data={'args': json.dumps(params['args'])})
    else:
        res = requests.post(url, data={'args': json.dumps(params['args'])})
    if res is None:
        return None
    log.logi(TAG, 'gen_gen_pic request end')
    ext = res.headers['content-type'].split('/')[-1]
    name = str(uuid.uuid4()) + '.' + ext
    pic_root_path = config.get_gen_path()
    if not os.path.isdir(pic_root_path):
        os.mkdir(pic_root_path)
    current_pic_path = pic_root_path + '/' + params['nickname']
    if not os.path.isdir(current_pic_path):
        os.mkdir(current_pic_path)
    fullname = current_pic_path + '/' + name
    with open(fullname, 'wb') as f:
        f.write(res.content)
        f.close()
    for img in images:
        img[1][1].close()
    log.logi(TAG, 'gen_gen_pic finish filename = ' + fullname)
    return fullname


def init_data_inner():
    keys = get_keys_by_server()
    for key in keys:
        obj = get_keyinfo_by_server(key)
        keys_list.append(obj)


def init_data():
    task = Thread(target=init_data_inner)
    task.start()
    return task
