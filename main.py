import json
import os
import sys
import traceback
import urllib.parse

sys.path.append(os.path.dirname(__file__))
import easywebdav
# easywebdav = __import__('stellar-webdav.easywebdav')
import StellarPlayer


class WebdavPlugin(StellarPlayer.IStellarPlayerPlugin):
    def __init__(self, player: StellarPlayer.IStellarPlayer):
        super().__init__(player)
        self.playurl = []
        self.url = ''
        self.webdav = None
        self.path = '/'
        self.dir = None
        self.username = ''
        self.password = ''
        self.host = ''
        self.port = ''
        self.ssl = False
        self.verify = False
        self.protocol = 'http'

    def isdir(self, item: easywebdav.File):
        if item.contenttype == 'httpd/unix-directory':
            return True
        # 类型为空，并且大小为0
        if not item.contenttype and item.size == 0:
            return True
        return False

    def ls(self):
        if not self.path.endswith('/'):
            self.path = self.path + '/'
        self.dir = self.webdav.ls(self.path)[1:]
        print(self.dir)
        # 文件夹类型排在前面
        self.dir.sort(key=lambda item: 0 if self.isdir(item) else 1)
        list_val = []
        for i in self.dir:
            path = i.name
            if self.isdir(i) and not path.endswith('/'):
                path = path + '/'
            path = path.replace(self.path, '', 1)
            list_val.append({'title': urllib.parse.unquote(path)})
        return list_val

    def update_list_view(self):
        self.player.loadingAnimation('main')
        list_val = self.ls()
        self.player.loadingAnimation('main', stop=True)
        self.player.updateControlValue('main', 'path', urllib.parse.unquote(self.path))
        self.player.updateControlValue('main', 'list', list_val)

    def show(self):
        if not self.webdav:
            self.load_config()
            controls = [
                {'type': 'space', 'height': 10},
                {'type': 'edit', 'name': '主机名', 'height': 30, 'value': self.host},
                {'type': 'space', 'height': 10},
                {
                    'group': [
                        {'type': 'edit', 'name': '端口', 'height': 30, 'width': 0.4, 'value': self.port},
                        {'type': 'check', 'name': 'SSL', 'height': 30, 'width': 0.1, ':value': 'ssl'},
                        {'type': 'check', 'name': '验证SSL证书', 'height': 30, 'width': 0.2, ':value': 'verify'},
                    ],
                    'height': 30
                },
                {'type': 'space', 'height': 10},
                {'type': 'edit', 'name': '用户名', 'height': 30, 'value': self.username},
                {'type': 'space', 'height': 10},
                {'type': 'edit', 'name': '密码', 'height': 30, 'value': self.password},
                {'type': 'space', 'height': 10},
                {'type': 'button', 'name': '连接', '@click': 'on_connect_webdav', 'height': 30}
            ]

            self.doModal('login', 600, 400, '', controls)

        else:
            list_val = self.ls()
            list_layout = {'type': 'link', 'name': 'title', '@click': 'on_click_item'}
            controls = [
                {
                    'group':
                        [
                            {'type': 'link', 'name': '返回', 'width': 30, '@click': 'on_click_back'},
                            {'type': 'label', 'name': 'path', 'value': self.path},
                        ],
                    'height': 30
                },
                {'type': 'list', 'name': 'list', 'itemlayout': {'group': list_layout}, 'value': list_val,
                 'separator': True, 'itemheight': 40}
            ]
            self.doModal('main', 800, 600, '', controls)

    def load_config(self):
        try:
            f = open('config.json', 'r')
            config = json.load(f)
            self.host = config.get('host', '')
            self.port = config.get('port', '')
            self.username = config.get('username', '')
            self.password = config.get('password', '')
            self.ssl = config.get('ssl', False)
            self.verify = config.get('verify', False)
            f.close()
        except:
            traceback.print_exc()

    def save_config(self):
        try:
            f = open('config.json', 'w')
            json.dump({'host': self.host, 'port': self.port, 'username': self.username, 'password': self.password,
                       'ssl': self.ssl, 'verify': self.verify}, f)
            f.close()
        except:
            traceback.print_exc()

    def on_connect_webdav(self, *arg):
        self.host = self.player.getControlValue('login', '主机名')
        self.port = self.player.getControlValue('login', '端口')
        self.username = self.player.getControlValue('login', '用户名')
        self.password = self.player.getControlValue('login', '密码')
        self.ssl = self.player.getControlValue('login', 'SSL')
        self.protocol = 'https' if self.ssl else 'http'
        self.verify = self.player.getControlValue('login', '验证SSL证书')
        self.save_config()
        self.player.loadingAnimation('login')
        try:
            self.webdav = easywebdav.connect(self.host, port=int(self.port), username=self.username,
                                             password=self.password, protocol=self.protocol,
                                             verify_ssl=self.verify)
            self.webdav.ls()
            self.player.closeModal('login', True)
            self.show()
        except Exception as e:
            print(e)
            self.player.loadingAnimation('login', stop=True)
            self.player.toast('login', '连接失败\r\n' + str(e))
            self.webdav = None

    def on_click_item(self, page, control, idx, *arg):
        file = self.dir[idx]
        if self.isdir(file):
            self.path = file.name
            self.update_list_view()
        else:
            self.player.play(f'{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}' + file.name)

    def on_click_back(self, *arg):
        if self.path != '/':
            temp = self.path.split('/')
            paths = []
            for i in temp:
                if i:
                    paths.append(i)
            self.path = '/' + '/'.join(paths[:-1])
            self.update_list_view()


def newPlugin(player: StellarPlayer.IStellarPlayer, *arg):
    plugin = WebdavPlugin(player)
    return plugin


def destroyPlugin(plugin: StellarPlayer.IStellarPlayerPlugin):
    plugin.stop()
