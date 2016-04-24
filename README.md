
#web_ctp

目标:使用web界面监控ctp期货接口的运行

当前:web界面用brython控制，通过websocket与ctp交互，ctp通过zmq与策略层(zmq_server中)通信


技术交流群 515942461
====================


环境搭建
========

win7 x86

安装activepython2.7 x86 (群共享内有下载)

安装vcredist x86最新版 (群共享内有下载)

运行pip_install.bat


试运行
======

启动ZMQ.bat (若不用zmqServer可跳过此步)

启动RUN.bat

用firefox打开http://localhost:9789

若要配置，点击"CTP帐户管理"配置ctp帐户信息及合约交易

若要监控，点击"CTP监控界面"监控帐户运行状况

回测
====

运行python py/rebuild.py即可使用实时运行时保存的tick数据完成回测
可更改rebuild.py中的exchange和symbol来指定回测品种


