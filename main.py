import memeapi
import wxbot
import auth
import log
import config

TAG = 'main'


def main():
    log.log_level = log.INFO
    log.logi(TAG, 'App is launching.')
    config.init_root_path()
    log.logi(TAG, 'init root path end.')
    auth_task = auth.init_data()
    log.logi(TAG, 'init auth data end.')
    memeapi_task = memeapi.init_data()
    log.logi(TAG, 'init memeapi data end.')
    auth_task.join()
    memeapi_task.join()
    wxbot.run_forever()
    log.logi(TAG, 'app end.')


if __name__ == '__main__':
    main()
