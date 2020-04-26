
## 2.19

websocket连接，当car注册时给user发送消息。

接下来需要测试：不同的账号和小车之间的websocket通信会不会串。

尝试使用 `gunicorn` web服务，使用 `eventlet` 来部署 websocket。
