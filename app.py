# -*- coding: utf-8 -*-

import os
import re
import json

from flask import Flask, request, render_template, url_for, make_response

from uploader import Uploader

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload/', methods=['GET', 'POST', 'OPTIONS'])
def upload():
    """UEditor文件上传接口

    config 配置文件
    result 返回结果
    """
    mimetype = 'application/json'
    result = {}
    action = request.args.get('action')

    # 解析JSON格式的配置文件
    with open(os.path.join(app.static_folder, 'ueditor', 'php',
                           'config.json')) as fp:
        try:
            # 删除 `/**/` 之间的注释
            CONFIG = json.loads(re.sub(r'\/\*.*\*\/', '', fp.read()))
        except:
            CONFIG = {}

    if action == 'config':
        # 初始化时，返回配置文件给客户端
        result = CONFIG

    elif action in ('uploadimage', 'uploadfile', 'uploadvideo'):
        # 图片、文件、视频上传
        if action == 'uploadimage':
            fieldName = CONFIG.get('imageFieldName')
            config = {
                "pathFormat": CONFIG['imagePathFormat'],
                "maxSize": CONFIG['imageMaxSize'],
                "allowFiles": CONFIG['imageAllowFiles']
            }
        elif action == 'uploadvideo':
            fieldName = CONFIG.get('videoFieldName')
            config = {
                "pathFormat": CONFIG['videoPathFormat'],
                "maxSize": CONFIG['videoMaxSize'],
                "allowFiles": CONFIG['videoAllowFiles']
            }
        else:
            fieldName = CONFIG.get('fileFieldName')
            config = {
                "pathFormat": CONFIG['filePathFormat'],
                "maxSize": CONFIG['fileMaxSize'],
                "allowFiles": CONFIG['fileAllowFiles']
            }

        if fieldName in request.files:
            field = request.files[fieldName]
            uploader = Uploader(field, config, app.static_folder)
            result = uploader.getFileInfo()
        else:
            result['state'] = '上传接口出错'

    elif action in ('uploadscrawl'):
        # 涂鸦上传
        fieldName = CONFIG.get('scrawlFieldName')
        config = {
            "pathFormat": CONFIG.get('scrawlPathFormat'),
            "maxSize": CONFIG.get('scrawlMaxSize'),
            "allowFiles": CONFIG.get('scrawlAllowFiles'),
            "oriName": "scrawl.png"
        }
        if fieldName in request.form:
            field = request.form[fieldName]
            uploader = Uploader(field, config, app.static_folder, 'base64')
            result = uploader.getFileInfo()
        else:
            result['state'] = '上传接口出错'

    elif action in ('catchimage'):
        config = {
            "pathFormat": CONFIG['catcherPathFormat'],
            "maxSize": CONFIG['catcherMaxSize'],
            "allowFiles": CONFIG['catcherAllowFiles'],
            "oriName": "remote.png"
        }
        fieldName = CONFIG['catcherFieldName']

        if fieldName in request.form:
            # 这里比较奇怪，远程抓图提交的表单名称不是这个
            source = []
        elif '%s[]' % fieldName in request.form:
            # 而是这个
            source = request.form.getlist('%s[]' % fieldName)

        _list = []
        for imgurl in source:
            uploader = Uploader(imgurl, config, app.static_folder, 'remote')
            info = uploader.getFileInfo()
            _list.append({
                'state': info['state'],
                'url': info['url'],
                'original': info['original'],
                'source': imgurl,
            })

        result['state'] = 'SUCCESS' if len(_list) > 0 else 'ERROR'
        result['list'] = _list
    elif action in ('listimage', 'listfile'):
        allowFiles = []
        listSize = 20
        path = ""
        if (action == 'listfile'):
            allowFiles = CONFIG['fileManagerAllowFiles']
            listSize = CONFIG['fileManagerListSize']
            path = CONFIG['fileManagerListPath']
        else:
            allowFiles = CONFIG['imageManagerAllowFiles']
            listSize = CONFIG['imageManagerListSize']
            path = CONFIG['imageManagerListPath']

        size = int(request.args.get('size', listSize))
        start = int(request.args.get('start', 0))
        end = start + size
        path = app.static_folder + path
        files = getfiles(app.root_path, path, allowFiles, [])
        lens = len(files)
        # 倒序
        # files.reverse()
        i = min(end, lens) - 1
        list = []
        for index in range(len(files)):
            if (i < lens and i >= 0 and i >= start):
                list.append(files[i])
                i = i - 1
        files = []
        # min = min(end, lens)
        # list = files[:min(end, lens)]
        result["state"] = "SUCCESS"
        result["list"] = list
        result["start"] = start
        result["total"] = lens
    else:
        result['state'] = '请求地址出错'

    result = json.dumps(result)

    if 'callback' in request.args:
        callback = request.args.get('callback')
        if re.match(r'^[\w_]+$', callback):
            result = '%s(%s)' % (callback, result)
            mimetype = 'application/javascript'
        else:
            result = json.dumps({'state': 'callback参数不合法'})

    res = make_response(result)
    res.mimetype = mimetype
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Headers'] = 'X-Requested-With,X_Requested_With'
    return res


def getfiles(root_path, path, allowFiles, files):
    if (os.path.exists(path)):
        fs = os.listdir(path)
        for f1 in fs:
            tmp_path = os.path.join(path, f1)
            if not os.path.isdir(tmp_path):
                fx = os.path.splitext(tmp_path)[1]
                if (fx in allowFiles):
                    file = {'url': (tmp_path.replace(root_path, '')).replace("\\", "/"),
                            'mtime': os.path.getmtime(tmp_path)}
                    files.append(file)
            else:
                getfiles(root_path, tmp_path, allowFiles, files)
        return files
    else:
        return []


if __name__ == '__main__':
    app.run(debug=True)


