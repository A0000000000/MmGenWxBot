import configparser
import os

configFile = 'config.properties'
config = configparser.ConfigParser()
config.read(configFile)


def get_config(selection, key):
    return config.get(selection, key)


def get_login_path():
    return get_config('resource', 'loginPath')


def get_login_pic():
    return get_login_path() + '/' + get_config('resource', 'loginPic')


def get_user_session():
    return get_login_path() + '/' + get_config('resource', 'session')


def get_gen_path():
    return get_config('resource', 'genPath')


def get_base_http_path():
    return get_config('http', 'baseURL')


def get_admin_path():
    return get_config('auth', 'admin')


def get_user_path():
    return get_config('auth', 'user')


def init_root_path():
    root_path = get_config('resource', 'rootPath')
    if not os.path.exists(root_path):
        os.makedirs(root_path)
