from flask import g, request, abort, jsonify
from . import car
from . import utils
from db import redis_cli, db
from auth import token_auth
from models import Car
from socket_io import socketio
from flask_socketio import emit


@socketio.on('connect')
@token_auth.login_required
def connect():
    emit('connect', {'status': 'success'})


@car.route('/regist', methods=['POST'])
def regist():
    car_id = request.form.get('id')
    ip_port = request.form.get("ip_port")
    car = Car.query.filter_by(id=car_id).first()
    if not car or not ip_port or not utils.judge_legal_ip(ip_port):
        abort(400)
    redis_cli.set('car:'+car_id, ip_port)
    redis_cli.expire('car:'+car_id, 60*60*2)

    # if the own is online
    user_id = car.own_id
    keys = redis_cli.keys(f"token:*:{user_id}:*")
    if keys:
        car_ip, car_port = ip_port.split(':')
        redis_cli.hmset(keys[0], mapping={'car_ip': car_ip, "car_port": car_port})
        new_key = keys[0][:52] + car_id
        redis_cli.rename(keys[0], new_key)
        utils.send(g.car_ip, g.car_port)

    return jsonify({'status': 'success'})

@car.route('/', methods=['POST'])
@token_auth.login_required
def add():
    car = Car(own_id=g.user_id)
    db.session.add(car)
    db.session.commit()
    return jsonify({'status': 'success', 'data': car.id})


@car.route('/run', methods=['POST'])
@token_auth.login_required
def run():
    msg = None
    isbackward = request.form.get('backward')
    isreset = request.form.get("reset")
    if isbackward:
        msg = 'backward'
    else:
        msg = 'forward'
    if isreset:
        msg = 'reset_run'

    if g.car_ip and g.car_port:
        try:
            # utils.send(g.car_ip, g.car_port, msg)
            emit('my_response', {'data': msg}, room='101', namespace=name_space)
            print(g.car_ip, g.car_port, msg)
        except Exception:
            return jsonify({"status": "fail", "msg": "socket error"}),501
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail", "msg": 'Car`s ip or port is error.'})


@car.route("/turn", methods=['POST'])
@token_auth.login_required
def turn():
    '''转向：1 2 3 4 5
    '''
    angle = request.form.get('angle')
    msg = angle
    #
    # if g.car_ip and g.car_port:
    #     try:
    #         # utils.send(g.car_ip, g.car_port, msg)
    emit('my_response', {'data': msg}, room='101', namespace=name_space)
    #         print(g.car_ip, g.car_port, msg)
    #     except Exception:
    #         return jsonify({"status": "fail", "msg": "socket error"}),501
    return jsonify({"status": "success"})
    # else:
    #     return jsonify({"status": "fail", "msg": 'Car`s ip or port is error.'})


@car.route("/gear", methods=['POST'])
@token_auth.login_required
def gear():
    msg = None
    isfast = request.form.get("fast")
    if isfast:
        msg = 'fast'
    else:
        msg = 'slow'

    if g.car_ip and g.car_port:
        try:
            # utils.send(g.car_ip, g.car_port, msg)
            emit('my_response', {'data': msg}, room='101', namespace=name_space)
            print(g.car_ip, g.car_port, msg)
        except Exception:
            return jsonify({"status": "fail", "msg": "socket error"}),501
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail", "msg": 'Car`s ip or port is error.'})


@car.route('/lock', methods=["POST"])
@token_auth.login_required
def lock():
    msg = None
    isopen = request.form.get('open')
    if isopen:
        msg = 'unlock'
    else:
        msg = 'lock'
    if g.car_ip and g.car_port:
        try:
            # utils.send(g.car_ip, g.car_port, msg)
            emit('my_response', {'data': msg}, room='101', namespace=name_space)
            print(g.car_ip, g.car_port, msg)
        except Exception:
            return jsonify({"status": "fail", "msg": "socket error"}),501
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail", "msg": 'Car`s ip or port is error.'})


from flask_socketio import join_room, leave_room
name_space = '/car'  # 命名空间:

id_sid_dict = {}        #小车id和小车sid字典-->{id : sid}
car_room_dict = {}      #小车id和所处room字典-->{id : room_number}
# {'wangwu':''123, 'lisi':'234}

@car.route('/run', methods=['POST', 'GET'])
def control():
    data = request.args.get('message')
    room_name = request.args.get('send_room')
    print(data, room_name)
    emit('my_response', {'data': data}, room=room_name, namespace=name_space)
    return jsonify({'status':'success', 'message':'okk'})


@car.route('/join/', methods=['GET'])
def join():
    car_id = request.args.get('car_id')
    room_number = request.args.get('room_number')
    if car_id == "":
        return jsonify({'message':'请输入小车号'})
    elif room_number == "":
        return jsonify({'message':'请输入加入队列号'})
    elif car_id not in id_sid_dict:
        return jsonify({'message':'该小车不存在，请重新输入'})
    elif car_id in car_room_dict:
        return jsonify({'message':'该小车已加入一个队列达到上限，请重新输入'})
    else:
        car_sid = id_sid_dict[car_id]
        join_room(room_number, car_sid, name_space)     #加入房间
        car_room_dict[car_id] = room_number             #更新字典
        return jsonify({'message':'小车成功加入队列'})

@car.route('/leave/', methods=['GET'])
def leave():
    car_id = request.args.get('car_id')
    if car_id == '':
        return jsonify({'message':'请输入小车号'})
    elif car_id not in id_sid_dict:
        return jsonify({'message':'小车不存在，请重新输入'})
    elif car_id not in car_room_dict:
        return jsonify({'message':'该小车还未加入任何队列，请重新输入'})
    else:
        sid = id_sid_dict[car_id]
        room_number = car_room_dict[car_id]
        leave_room(room_number, sid, name_space)        #离开房间
        del car_room_dict[car_id]                       #更新字典
        return jsonify({'message':'小车成功退出队列'})

@car.route('/show/', methods=['GET'])
def show():
    print(car_room_dict)
    return jsonify(car_room_dict)

@socketio.on('get_car', namespace=name_space)
def get_id(message):
    id = message['data']
    sid = request.sid
    if id in id_sid_dict:
        pass
    else:
        id_sid_dict[id] = sid       #将新的小车加入字典
    emit('my_response', 'car id is: %s' % id)

@socketio.on('connect', namespace=name_space)
def car_connect():
    # 建立连接 sid:连接对象ID
    print('1 Client connected==> ', request.sid)
    emit('my_response', '%s connect successful!' % request.sid)


@socketio.on('disconnect', namespace=name_space)
def car_disconnect():
    # 连接对象关闭 删除对象ID
    sid = request.sid
    new_dict = {v: k for k, v in id_sid_dict.items()}
    id = new_dict[sid]
    del id_sid_dict[id]             #将小车从字典删除
    del new_dict
    print('0 Client disconnected==> ', request.sid)
