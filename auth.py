import config
import os
import json
import log
from threading import Thread

super_admin = '猫眼螺'
user_list = []
admin_list = []
user_cmd = ['help', 'keys', 'keyinfo', 'whoami']

TAG = 'auth'


def is_super_admin(username):
    log.logi(TAG, 'is_super_admin username: ' + username)
    return username == super_admin


def check_user_permission(username):
    log.logi(TAG, 'check_user_permission username: ' + username)
    if check_admin_permission(username):
        return True
    return username in user_list


def check_admin_permission(username):
    log.logi(TAG, 'check_admin_permission username: ' + username)
    if is_super_admin(username):
        return True
    return username in admin_list


def is_user_cmd(cmd):
    log.logi(TAG, 'is_user_cmd cmd: ' + cmd)
    return cmd in user_cmd


def add_admin(user):
    log.logi(TAG, 'add_admin user: ' + user)
    if user in admin_list:
        return
    admin_list.append(user)
    return save_file(config.get_admin_path(), admin_list)


def remove_admin(user):
    log.logi(TAG, 'remove_admin user: ' + user)
    admin_list.remove(user)
    return save_file(config.get_admin_path(), admin_list)


def add_user(user):
    log.logi(TAG, 'add_user user: ' + user)
    if user in user_list:
        return
    user_list.append(user)
    return save_file(config.get_user_path(), user_list)


def remove_user(user):
    log.logi(TAG, 'remove_user user: ' + user)
    user_list.remove(user)
    return save_file(config.get_user_path(), user_list)


def save_file(file, data):
    task = Thread(target=save_file_inner, args=(file, data))
    task.start()
    return task


def save_file_inner(file, data):
    dirname = os.path.dirname(file)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    with open(file, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(data))
        f.close()


def init_data():
    task = Thread(target=init_data_inner)
    task.start()
    return task


def init_data_inner():
    log.logi(TAG, 'init data')
    admin_path = config.get_admin_path()
    user_path = config.get_user_path()
    log.logi(TAG, 'admin: %s, user: %s' % (admin_path, user_path))
    log.logi(TAG, 'init admin data')
    init_data_to_mem(admin_path, admin_list)
    log.logi(TAG, 'init user data')
    init_data_to_mem(user_path, user_list)
    log.logi(TAG, 'init data end')


def init_data_to_mem(path, data_list):
    if os.path.exists(path):
        log.logi(TAG, 'file %s is exists' % path)
        with open(path, 'r', encoding='UTF-8') as f:
            rawdata = f.readline()
            read_data = json.loads(rawdata)
            if type(read_data) is list:
                for i in read_data:
                    data_list.append(i)
            f.close()
            log.logi(TAG, 'load data from %s end' % path)
