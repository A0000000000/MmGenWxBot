# 用于生成meme图的微信机器人

* 项目依赖于以下两个开源项目:
  * https://github.com/MeetWq/meme-generator/blob/main/docs/memes.md
  * https://github.com/why2lyj/ItChat-UOS

* 项目纯属做着玩, 出现任何问题(例如微信号被封), 作者不负任何责任


# 部署说明
1. 首先部署一个meme-generator的web服务, 我这里使用docker部署, 详细部署方式, 可见上面第一个开源项目
2. 完善config.properties, 主要是指定好meme-generator web服务的地址
3. 使用pip安装好项目依赖(应该是只有requests和itchat-uos-fix, 记不太清了, 如果运行时, 提示还缺依赖, 缺啥安装啥就行)
4. 执行`python3 main.py`, 然后会在项目目录的resource/user/login.png生成一个二维码, 用当作机器人的微信号扫码登录即可
