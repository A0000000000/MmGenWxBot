import json

import itchat
import os
import config
import auth
import memeapi
import log
from threading import Thread
from itchat.content import *


global_chat_session = {
    'private': {},
    'group': {}
}

TAG = 'wxbot'

# Todo：自定义参数暂时写死，后面看看要不要移动到配置文件中，主要meme-generator的文档里参数列表里就这几个
int_args = ['pic', 'number', 'ratio']
bool_args = ['person', 'circle', 'black']
enum_args = {
    'mode': ['normal', 'loop', 'circle'],
    'position': ['right', 'left', 'both'],
    'direction': ['left', 'right', 'top', 'bottom']
}
string_args = ['time', 'name']


def send_message(session, message):
    log.logi(TAG, 'send_message session = ' + str(session) + ', message = ' + str(message))
    username = session['session_username']
    group_name = session['session_group_name']
    if username == group_name:
        users = itchat.search_friends(nickName=username)
        if len(users) > 0:
            for user in users:
                res = user.send(message)
                if res['BaseResponse']['Ret'] == -1:
                    log.loge(TAG, 'send_message 消息发送失败. session = ' + str(session))
    else:
        rooms = itchat.search_chatrooms(name=group_name)
        if len(rooms) > 0:
            for room in rooms:
                if room.nickName == group_name:
                    res = room.send(message)
                    if res['BaseResponse']['Ret'] == -1:
                        log.loge(TAG, 'send_message 消息发送失败. session = ' + str(session))


def send_image_or_file(session, file):
    log.logi(TAG, 'send_image_or_file session = ' + str(session) + ', file = ' + str(file))
    target = []
    username = session['session_username']
    group_name = session['session_group_name']
    if username == group_name:
        users = itchat.search_friends(nickName=username)
        if len(users) > 0:
            for user in users:
                target.append(user)
    else:
        rooms = itchat.search_chatrooms(name=group_name)
        if len(rooms) > 0:
            for room in rooms:
                if room.nickName == group_name:
                    target.append(room)
    if len(target) > 0:
        for item in target:
            res = item.send_image(file)
            if res['BaseResponse']['Ret'] == -1:
                log.logw(TAG, 'send_image_or_file 图片发送失败, 已尝试使用文件方式发送. session = ' + str(session))
                item.send('@%s\u2005图片发送失败, 已尝试使用文件方式发送.' % username)
                res = item.send_file(file)
                if res['BaseResponse']['Ret'] == -1:
                    log.loge(TAG, 'send_image_or_file 文件发送失败. session = ' + str(session))


@itchat.msg_register([TEXT])
def private_chat_text(msg):
    log.logi(TAG, 'private_chat_text source = ' + msg.user.nickName)
    msg.actualNickName = msg.user.nickName
    if auth.is_super_admin(msg.actualNickName):
        if super_private_cmd_duel(msg):
            return
    log.logi(TAG, 'private_chat_text text = ' + msg.text)
    msg.text = '@' + msg.actualNickName + '\u2005' + msg.text
    # 私聊文本消息的处理与群聊类似, 只是少了权限校验
    if auth.check_admin_permission(msg.actualNickName) or auth.check_user_permission(msg.actualNickName):
        # 只有管理员和用户可以进行私聊操作, 这里用来创建session
        if msg.actualNickName not in global_chat_session['private']:
            global_chat_session['private'][msg.actualNickName] = {
                'session_username': msg.actualNickName,
                'session_group_name': msg.actualNickName
            }
        # 根据身份类型, 分发的不同的handler处理
        if auth.check_admin_permission(msg.actualNickName):
            admin_cmd(global_chat_session['private'][msg.actualNickName], msg.text)
        else:
            user_cmd(global_chat_session['private'][msg.actualNickName], msg.text)


@itchat.msg_register([PICTURE])
def private_chat_pic(msg):
    log.logi(TAG, 'private_chat_pic source = ' + msg.user.nickName)
    # 判断是否存在session, 不存在直接忽略消息
    msg.actualNickName = msg.user.nickName
    if msg.actualNickName not in global_chat_session['private']:
        return

    # 进行图片处理
    process_pic(global_chat_session['private'][msg.actualNickName], msg)


@itchat.msg_register(TEXT, isGroupChat=True)
def group_chat_text(msg):
    log.logi(TAG, 'group_chat_text source = [' + msg.actualNickName + ', ' + msg.user.nickName + ']')
    log.logi(TAG, 'group_chat_text text = ' + msg.text)
    # 群聊非@信息直接忽略
    if not msg.isAt:
        return

    # 创建群组的Session
    if msg.user.nickName not in global_chat_session['group']:
        global_chat_session['group'][msg.user.nickName] = {}

    # 创建当前消息的Session, 得益于傻逼的微信不支持富文本, 只能用这种折中的方式储存上下文
    if msg.actualNickName not in global_chat_session['group'][msg.user.nickName]:
        global_chat_session['group'][msg.user.nickName][msg.actualNickName] = {
            'session_username': msg.actualNickName,
            'session_group_name': msg.user.nickName
        }

    current_session = global_chat_session['group'][msg.user.nickName][msg.actualNickName]

    if auth.check_admin_permission(msg.actualNickName):
        # 如果是管理员@, 并且是设置权限, 放行
        admin_cmd(current_session, msg.text)
        return

    if not auth.check_user_permission(msg.actualNickName):
        # 如果是用户无权限, 提示用户无权限
        send_message(current_session, u'@%s\u2005 无权限' % msg.actualNickName)
        remove_session(current_session)
        return

    # 到这里, 说明是一个有权限的用户, 进行用户指令处理
    user_cmd(current_session, msg.text)


@itchat.msg_register(PICTURE, isGroupChat=True)
def group_chat_pic(msg):
    log.logi(TAG, 'group_chat_pic source = [' + msg.actualNickName + ', ' + msg.user.nickName + ']')
    # 判断是否已经存在Session, 若不存在Session, 直接返回
    if (msg.user.nickName not in global_chat_session['group'] or
            msg.actualNickName not in global_chat_session['group'][msg.user.nickName]):
        return

    # 已经存在Session, 说明是指令后面附加的图片, 进行图片处理逻辑
    process_pic(global_chat_session['group'][msg.user.nickName][msg.actualNickName], msg)


# 解析原始的命令
def parse_raw_cmd(current_session, raw_cmd_text):
    log.logi(TAG, 'parse_raw_cmd')
    cmds = []
    raw_cmds = raw_cmd_text.split(' ')
    for raw_cmd in raw_cmds:
        items = raw_cmd.split('\u2005')
        for item in items:
            if len(item) > 0:
                cmds.append(item)
    return cmds


# 对指令进行初步判断, 分发给不同的handler处理指令
def dispatch_cmd(current_session, cmds):
    log.logi(TAG, 'dispatch_cmd')
    if len(cmds) < 2:
        send_message(current_session, '@%s\u2005 想要做点什么?' % current_session['session_username'])
        remove_session(current_session)
        return

    if cmds[1] == 'cmd':
        process_cmd(current_session, cmds)
    else:
        process_gen_text(current_session, cmds)


# admin操作不需要权限校验
def admin_cmd(current_session, raw_cmd):
    log.logi(TAG, 'admin_cmd')
    cmds = parse_raw_cmd(current_session, raw_cmd)
    dispatch_cmd(current_session, cmds)


# user操作需要过滤部分操作
def user_cmd(current_session, raw_cmd):
    log.logi(TAG, 'user_cmd')
    cmds = parse_raw_cmd(current_session, raw_cmd)
    if len(cmds) < 2:
        send_message(current_session, '@%s\u2005 想要做点什么?' % current_session['session_username'])
        remove_session(current_session)
        return
    if cmds[1] == 'cmd':
        # 需要校验权限
        if len(cmds) > 2 and auth.is_user_cmd(cmds[2]):
            dispatch_cmd(current_session, cmds)
        else:
            send_message(current_session, '@%s\u2005 dont have permission or cmd not exist.' %
                         current_session['session_username'])
            remove_session(current_session)
    else:
        dispatch_cmd(current_session, cmds)


# 处理命令等逻辑
def process_cmd(current_session, cmds):
    log.logi(TAG, 'process_cmd')
    if len(cmds) < 2:
        send_message(current_session, '@%s\u2005 no command.' % current_session['session_username'])
        remove_session(current_session)
        return
    cmd = cmds[2]
    if cmd == 'help':
        with open(config.get_help(), 'r', encoding='UTF-8') as f:
            help_text = f.read()
            send_message(current_session, '@%s\u2005 \n%s' % (current_session['session_username'], help_text))
            f.close()
    elif cmd == 'keys':
        keys_list = memeapi.get_keys()
        result = ''
        for key in keys_list:
            result = result + key + '\n'
        send_message(current_session, '@%s\u2005 keys:\n%s' % (current_session['session_username'], result))
    elif cmd == 'keyinfo':
        if len(cmds) > 3:
            key = cmds[3]
            keyinfo = memeapi.get_keyinfo(key)
            send_message(current_session, '@%s\u2005 keyinfo is \n%s' % (current_session['session_username'], keyinfo))
        else:
            send_message(current_session, '@%s\u2005 empty key.' % current_session['session_username'])
    elif cmd == 'add':
        deal_add_remove(current_session, cmds)
    elif cmd == 'remove':
        deal_add_remove(current_session, cmds)

    elif cmd == 'whoami':
        res = 'You ident is: '
        if auth.is_super_admin(current_session['session_username']):
            res = res + 'super admin'
        elif auth.check_admin_permission(current_session['session_username']):
            res = res + 'admin'
        elif auth.check_user_permission(current_session['session_username']):
            res = res + 'user'
        else:
            res = res + 'no permission'
        send_message(current_session, '@%s\u2005 %s' % (current_session['session_username'], res))
    else:
        send_message(current_session, '@%s\u2005 unknown command.' % current_session['session_username'])
    remove_session(current_session)


# Todo: 现在用户权限是全局的作用域，这里设计并不是很好，应该按照“私聊”、“群聊”分别设置权限
# Todo：后续这里重构一下
def deal_add_remove(current_session, cmds):
    log.logi(TAG, 'deal_add_remove')
    cmd = cmds[2]
    if len(cmds) > 3:
        op_type = cmds[3]
        if op_type == 'user':
            add_user_list = cmds[4::]
            if len(add_user_list) == 0:
                send_message(current_session, '@%s\u2005 指令缺少参数' % current_session['session_username'])
                return
            reply = ''
            for add_user in add_user_list:
                if add_user[0] == '@':
                    if cmd == 'add':
                        auth.add_user(add_user[1::])
                    if cmd == 'remove':
                        auth.remove_user(add_user[1::])
                    reply = reply + add_user + '\u2005'
            if cmd == 'add':
                send_message(current_session, '@%s\u2005 %s用户权限添加成功' % (current_session['session_username'], reply))
            if cmd == 'remove':
                send_message(current_session, '@%s\u2005 %s用户权限移除成功' % (current_session['session_username'], reply))
            return
        elif op_type == 'admin':
            if not auth.is_super_admin(current_session['session_username']):
                send_message(current_session, '@%s\u2005 无权限操作此项' % current_session['session_username'])
                return
            add_admin_list = cmds[4::]
            if len(add_admin_list) == 0:
                send_message(current_session, '@%s\u2005 指令缺少参数' % current_session['session_username'])
                return
            reply = ''
            for add_admin in add_admin_list:
                if add_admin[0] == '@':
                    if cmd == 'add':
                        auth.add_admin(add_admin[1::])
                    if cmd == 'remove':
                        auth.remove_admin(add_admin[1::])
                    reply = reply + add_admin + '\u2005'
            if cmd == 'add':
                send_message(current_session, '@%s\u2005 %s管理员权限添加成功' % (current_session['session_username'], reply))
            if cmd == 'remove':
                send_message(current_session, '@%s\u2005 %s管理员权限移除成功' % (current_session['session_username'], reply))
            return
        else:
            send_message(current_session, '@%s\u2005 未知操作类型: %s' % (current_session['session_username'], op_type))
    else:
        send_message(current_session, '@%s\u2005 缺少指令' % current_session['session_username'])


# 处理文本等逻辑
def process_gen_text(current_session, cmds):
    log.logi(TAG, 'process_gen_text')
    if len(cmds) < 3:
        send_message(current_session, '@%s\u2005 缺少参数' % current_session['session_username'])
        remove_session(current_session)
        return
    text_params = []
    args = {}
    index = 2
    while index < len(cmds):
        item = cmds[index]
        if item.startswith('#') and index + 1 < len(cmds):
            cmd = item[1::]
            arg = cmds[index + 1]
            if cmd in int_args and arg.isdigit():
                args[cmd] = int(arg)
                index += 2
            elif cmd in bool_args:
                if arg.lower() == 'false' or arg == '0':
                    args[cmd] = False
                else:
                    args[cmd] = True
                index += 2
            elif cmd in enum_args:
                args_list = enum_args[cmd]
                flag = False
                for arg_item in args_list:
                    if arg_item.startswith(arg):
                        args[cmd] = arg_item
                        index += 2
                        flag = True
                        break
                if not flag:
                    text_params.append(item)
                    index += 1
            elif cmd in string_args:
                args[cmd] = arg
                index += 2
            else:
                text_params.append(item)
                index += 1
            continue
        text_params.append(item)
        index += 1
    key = cmds[1]
    info = memeapi.get_keyinfo(key)
    if info is None:
        send_message(current_session, '@%s\u2005 没有对应的key' % current_session['session_username'])
        remove_session(current_session)
    else:
        current_session['text_params'] = text_params
        if 'pic' in args:
            current_session['pic_count'] = args['pic']
            del args['pic']
        current_session['info'] = info
        current_session['pic_list'] = []
        current_session['pic_result'] = ''
        current_session['args'] = args
        process_gen(current_session)


# 处理图片下载等逻辑
def process_pic(current_session, msg):
    log.logi(TAG, 'process_pic')
    pic_root_path = config.get_gen_path()
    if not os.path.isdir(pic_root_path):
        os.mkdir(pic_root_path)
    current_pic_path = pic_root_path + '/' + msg.actualNickName
    if not os.path.isdir(current_pic_path):
        os.mkdir(current_pic_path)
    full_filename = current_pic_path + '/' + msg.fileName
    msg.download(full_filename)
    current_session['pic_list'].append(full_filename)
    process_gen(current_session)


# 最后生成结果的逻辑
def process_gen(current_session):
    log.logi(TAG, 'process_gen')
    info = current_session['info']
    if not (info['params']['min_texts'] <= len(current_session['text_params']) <= info['params']['max_texts']):
        send_message(current_session, '@%s\u2005 文本数量不符合预期' % current_session['session_username'])
        remove_session(current_session)
        return
    if not (info['params']['min_images'] <= current_session['pic_count'] <= info['params']['max_images']):
        send_message(current_session, '@%s\u2005 图片数量不符合预期' % current_session['session_username'])
        remove_session(current_session)
        return
    target_args = filter_and_gen_args(current_session['args'], info)
    if len(current_session['pic_list']) == current_session['pic_count']:
        params = {
            'texts': current_session['text_params'],
            'images': current_session['pic_list'],
            'key': current_session['info']['key'],
            'nickname': current_session['session_username'],
            'args': target_args
        }
        task = Thread(target=gen_pic_inner, args=(current_session, params))
        task.start()
    if len(current_session['pic_list']) > current_session['pic_count']:
        send_message(current_session, '@%s\u2005 图片数量过多' % current_session['session_username'])
        remove_session(current_session)
        return


def filter_and_gen_args(args, info):
    # Todo: 增加真实的参数校验，主要是类型太复杂了，不好校验，暂时先不校验了
    # 先占好位置
    return args


def gen_pic_inner(current_session, params):
    log.logi(TAG, 'gen_pic_inner')
    result = memeapi.gen_gen_pic(params)
    current_session['pic_result'] = result
    if result is not None:
        send_image_or_file(current_session, result)
    remove_session(current_session)


def remove_session(current_session):
    log.logi(TAG, 'remove_session')
    gen_path = config.get_gen_path() + '/' + current_session['session_username']
    if os.path.isdir(gen_path):
        files = os.listdir(gen_path)
        for file in files:
            os.remove(os.path.join(gen_path, file))
    if (current_session['session_username'] == current_session['session_group_name']
            and current_session['session_username'] in global_chat_session['private']):
        del global_chat_session['private'][current_session['session_username']]
    elif (current_session['session_group_name'] in global_chat_session['group']
          and current_session['session_username'] in global_chat_session['group'][current_session['session_group_name']]):
        del global_chat_session['group'][current_session['session_group_name']][current_session['session_username']]
        if len(global_chat_session['group'][current_session['session_group_name']]) == 0:
            del global_chat_session['group'][current_session['session_group_name']]


def super_private_cmd_duel(msg):
    log.logi(TAG, 'super_private_cmd_duel')
    cmd = msg.text
    if cmd == 'global':
        msg.user.send('global data: ' + str(json.dumps(global_chat_session)))
        return True
    if cmd == 'user':
        msg.user.send('user data: ' + str(json.dumps(auth.user_list)))
        return True
    if cmd == 'admin':
        msg.user.send('admin data: ' + str(json.dumps(auth.admin_list)))
        return True
    if cmd == 'clear':
        global_chat_session['private'] = {}
        global_chat_session['group'] = {}
        msg.user.send('clear data success. global data = ' + str(json.dumps(global_chat_session)))
        return True
    return False


def run_forever():
    log.logi(TAG, 'run_forever')
    login_path = config.get_login_path()
    if not os.path.exists(login_path):
        os.makedirs(login_path)
    itchat.auto_login(
        hotReload=True,
        enableCmdQR=True,
        picDir=config.get_login_pic(),
        statusStorageDir=config.get_user_session()
    )
    log.logi(TAG, 'login success')
    itchat.run()
