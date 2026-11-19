"""通用看板快照。默认用离线样例，不持有平台身份或远端目标。"""
import copy
import time
from datetime import datetime
from desk import indexdb
from desk.paths import DATA, ROOT, load_json

CACHE = DATA / 'fusion/board.local.json'
STALE_SECONDS = 1800


def validate(board):
    if not isinstance(board, dict) or not all(isinstance(board.get(k), list) for k in ('cards','projects','today')):
        raise ValueError('看板快照格式不完整')
    if not board.get('day') or not isinstance(board.get('v'), (int,float)):
        raise ValueError('看板缺少日期或版本')
    fields = ('id','no','title','state','why','open','who','people','text','updatedAt',
              'createdAt','closedAt','today','todoNext','project','sessions','whoId','originUrl')
    clean = {k:copy.deepcopy(board.get(k)) for k in ('v','at','day','projects','today')}
    clean['cards'] = []
    for c in board['cards']:
        if not isinstance(c,dict) or not c.get('id') or c.get('state') not in ('ai','wait','me','stuck','done','unknown'):
            raise ValueError('事项快照格式不兼容')
        c = {k:c.get(k) for k in fields}
        # 只有同源索引链接或明确HTTP(S)入口可打开，不接收脚本URL。
        url=str(c.get('originUrl') or '')
        if url and not (url.startswith(('http://','https://')) or (url.startswith('/') and not url.startswith('//'))):c['originUrl']=''
        if not c.get('open'):c['text']='';c['todoNext']=''
        clean['cards'].append(c)
    return clean


def state():
    demo = indexdb.config().get('demo',True)
    saved = load_json(ROOT/'samples/fusion-board.json' if demo else CACHE,{})
    board = copy.deepcopy(saved.get('board'))
    checked = saved.get('checkedAt')
    error = ''
    if demo and board:
        # 样例时间在读取时生成，不声称曾核对真实云端。
        checked = int(time.time()*1000)
        board['day'] = datetime.now().date().isoformat()
        for c in board['cards']:
            c.update(updatedAt=checked,createdAt=checked,closedAt=checked if c['state']=='done' else 0)
    try:board=validate(board) if board else None
    except ValueError as e:board=None;error=str(e)
    age = max(0,int(time.time()-checked/1000)) if checked else None
    return {'ok':board is not None,'board':board,'fetchedAt':saved.get('fetchedAt',checked),'checkedAt':checked,
            'ageSeconds':age,'dataAgeSeconds':age,'stale':age is None or age>STALE_SECONDS,
            'error':error,'refreshing':False,'canRefresh':False,'demo':demo,
            'space':'离线样例空间' if demo else saved.get('space','本机快照'),
            'spaceNodeId':saved.get('spaceNodeId',''),
            'transport':'offline-sample' if demo else 'local-snapshot','lastRefresh':None,'memberUrl':'/library.html'}


def refresh():
    # 仅重读已存在文件；不猜测远端账号、不调用平台CLI。
    return state()
