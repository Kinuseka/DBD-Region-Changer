import pip_system_certs.wrapt_requests
from bs4 import BeautifulSoup, ResultSet, Tag, NavigableString
from typing import Union, Iterable, Callable, List
from fake_useragent import FakeUserAgent, FakeUserAgentError
from functools import lru_cache, wraps
from time import monotonic_ns
from frozendict import frozendict
from pythonping import ping
from loguru import logger
import concurrent.futures
import constants as cnts
import requests
import socket
import io

#Bind to logger
log = logger.bind(name="DBDRegion-Debug")

def freezeargs(func):
    wraps(func)
    def wrapped(*args, **kwargs):
        args = (frozendict(arg) if isinstance(arg, dict) else arg for arg in args)
        kwargs = {k: frozendict(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
        return func(*args, **kwargs)
    return wrapped

#From gist: https://gist.github.com/Morreski/c1d08a3afa4040815eafd3891e16b945
def cached(
    _func=None, *, seconds: int = 600, maxsize: int = 128, typed: bool = False
):
    """An implementation of lru_cache that memoizes a response as long as it is code 200

    Parameters:
    seconds (int): Timeout in seconds to clear the WHOLE cache, default = 10 minutes
    maxsize (int): Maximum Size of the Cache
    typed (bool): Same value of different type will be a different entry

    """

    def wrapper_cache(f):
        f = lru_cache(maxsize=maxsize, typed=typed)(f)
        f.delta = seconds * 10 ** 9
        f.expiration = monotonic_ns() + f.delta
        @freezeargs
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            resp = f(*args, **kwargs)
            if monotonic_ns() >= f.expiration:
                f.cache_clear()
                f.expiration = monotonic_ns() + f.delta
            if resp.status_code != 200:
                f.cache_clear()
                f.expiration = 0
            return resp
        wrapped_f.cache_info = f.cache_info
        wrapped_f.cache_clear = f.cache_clear
        return wrapped_f

    # To allow decorator to be used without arguments
    if _func is None:
        return wrapper_cache
    else:
        return wrapper_cache(_func)

class HostHub:
    def __init__(self) -> None:
        self.location = cnts.HOST_DIR

    def _content_host(self):
        contents = []
        with open(self.location, "r") as file:
            for line in file.readlines():
                chose = line.strip().split()
                if chose and not line.startswith('#'):
                    if len(chose) >= 2:
                        contents.append([chose[0], chose[1]])
                    else:
                        contents.append(chose)
        return contents
    
    def hosts(self, callback: Callable=None) -> List[List]:
        """
        callback: Passes a hostname and determine the outcome
        """
        if not callback:
            callback = lambda i: True
        hosts = self._content_host()
        filtered = []
        for host in hosts:
            try:
                if callback(host[1]):
                    filtered.append(host)
            except IndexError:
                pass
        return filtered
    
    def save(self, ip, hostname):
        entry = f"{ip} {hostname}"
        with open(self.location, 'r') as f:
            lines = f.readlines()
            if lines and lines[-1].strip():
                # Last line is not empty, add a newline before appending the entry
                entry = "\n" + entry
        with open(self.location, 'a') as f:
            f.write(entry)
        
    def remove(self, hostname):
        with open(self.location, "r+") as f:
            d = f.readlines()
            f.seek(0)
            for i in d:
                try:
                    if i.strip().split()[1:][0] != hostname:
                        f.write(i)
                except IndexError:
                    f.write(i)
            f.truncate()

    def open_host(self):
        self.filehost = open(self.location)

class GameliftList:
    def __init__(self, endpoint = cnts.GAME_LIFT_ENDPOINT) -> None:
        self.endpoint = endpoint

    def load(self):
        "Loads the data, required to call this method first"
        try:
            user_agent = FakeUserAgent().random
            log.debug(f'Using user agent: {user_agent}')
            res = requests.get(self.endpoint,
                               headers={
                                   'User-Agent': user_agent
                               })
            self.soup = BeautifulSoup(res.content, "html.parser")
        except requests.exceptions.RequestException as e:
            log.exception('An error has occured while loading gamelift')
            self.results = BeautifulSoup("<html></html><>", "html.parser")
            return False
        except FakeUserAgentError as e:
            log.error(f'Failed to generate user-agent due to: {e}')
            raise e
        table = self.soup.find('div', {'class': 'table-contents'})
        self.results: ResultSet[Union[Tag, NavigableString]] = table.find_all('tr')
        return True

    def sort_data(self):
        indexed_data = []
        for result in self.results:
            template_data = {
                "server_name": None,
                "server_endpoint": None
            }
            tabindex = result.find_all("td")
            if not tabindex:
                continue
            template_data["server_pretty"] = tabindex[0].text.strip()
            template_data["server_name"] = tabindex[1].text.strip()
            template_data["server_endpoint"] = tabindex[2].text.strip()
            indexed_data.append(template_data)
        return indexed_data

    def get_ip(self, data):
        server = data["server_endpoint"]
        return dns_over_https(server)
    
    def get_host(self, ip):
        name, alias, addr = socket.gethostbyaddr(ip)
    
    def is_aws_host(self, host: str):
        data = self.sort_data()
        for each in data:
            if host == each['server_endpoint']:
                return True 
        else:
            return False

    def get_data_fromhost(self, hostname: str):
        return [d for d in self.sort_data() if d.get("server_endpoint") == hostname][0]

    def get_data_fromservername(self, server_name: str):
        return [d for d in self.sort_data() if d.get("server_name") == server_name][0]

    def remove_server_bydata(self, server_data: dict):
        return [d for d in self.sort_data() if not all(d.get(key) == value for key, value in server_data.items())]

    def remove_old_host(self, host: HostHub):
        for data in self.sort_data():
            host.remove(data['server_endpoint'])
    
    def modify_host(self, host: HostHub, server_name: str = None, server_host: str =None):
        self.remove_old_host(host)
        if server_name:
            server_selected = self.get_data_fromservername(server_name)
        elif server_host:
            server_selected = self.get_data_fromhost(server_host)
        filtered_dicts = self.remove_server_bydata(server_selected)
        server_selected_ip = self.get_ip(server_selected)
        host.save(server_selected_ip, server_selected['server_endpoint'])
        for data in filtered_dicts:
            host.save(server_selected_ip, data['server_endpoint'])

    def current_host(self, host: HostHub):
        hosts = host.hosts(callback=self.is_aws_host)
        if hosts:
            current_host = hosts[0]
            server_data = self.get_data_fromhost(current_host[1])
        else:
            server_data = {
                "server_pretty": "No host",
                "server_name": "None",
                "server_endpoint": None
            }
        return server_data

def pinger(IP):
    if not IP:
        return False
    response = ping(IP, count=10)
    return response

def create_thread_pools(datas, func):
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(func, data) for data in datas]
    except RuntimeError:
        return []
    return futures

def handle_ping(IPs):
    futures = create_thread_pools(IPs, pinger)
    results = []
    for num, f in enumerate(futures):
        try:
            results.append(f.result())
        except Exception as e:
            log.exception(f'Issue occured while pinging IP: {IPs[num]}')
            results.append(False)
    return results

@cached(seconds=600)
def request_cached(*args, **kwargs):
    log.debug(f"Requesting at {args}")
    resp = requests.get(*args, **kwargs)
    log.debug(f"We requested at {args} and responded: {resp}")
    return resp

def dns_over_https(hostname, ip_only=True):
    for dns in cnts.DNS:
        json = {"name": hostname, "type": "A", "ct": "application/dns-json"}
        headers = {"accept": "application/dns-json"}
        try:
            response = request_cached(dns['url'], headers=headers, params=json, timeout=3)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            log.exception(f"Failed to resolve dns with: {dns['name']}")
        data = response.json()
        if ip_only:
            return data['Answer'][0]['data']
        return data
    return None

import pyuac
if __name__ == "__main__":
    if not pyuac.isUserAdmin():
        print("Re-launching as admin!")
        pyuac.runAsAdmin()
    else:
        try:
            gamelift = GameliftList()
            hub = HostHub()
            gamelift.load()
            gameservers = gamelift.sort_data()
            hosts = hub.hosts(callback=gamelift.is_aws_host)
            gamelift.modify_host("us-east-1", hub)
            gamelift.current_host(hub)
        except Exception as e:
            print(e)
        finally:
            input("Press enter to close the window. >")

    