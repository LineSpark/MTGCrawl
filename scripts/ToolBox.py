from urllib.parse import urlparse
import datetime, time
import os
import json
import re
import zlib
from datetime import timedelta, datetime
from urllib.parse import urlsplit
from random import choice
import requests
import logging

def print_obj_props(obj):
    # print("Object details for {}".format(obj.__name__))
    for key, value in obj.__dict__.items():
        print("\t{}: {}".format(key, value))
    print()


def print_obj_methods(obj):
    for m in vars(obj):
        print("\t{}".format(m))


class Throttle:
    """Add a delay to downloads from pages on the same domain."""

    def __init__(self, delay):
        self.delay = delay
        self.domains = {}

    def wait(self, url):
        domain = urlparse(url).netloc
        accessed = self.domains.get(domain)

        if self.delay > 0 and accessed:
            sleep_secs = self.delay - (datetime.now() - accessed).total_seconds()
            if sleep_secs > 0:
                time.sleep(sleep_secs)
        self.domains[domain] = datetime.now()


# def download(url, num_retries=2, user_agent="pdrage", proxies=None):
#     print("Downloading URL: {}".format(url))
#     headers = {"user-agent": user_agent}
#     try:
#         resp = requests.get(url, headers=headers, proxies=proxies)
#         resp.raise_for_status()
#         resp = resp.text
#     except requests.HTTPError as error:
#         print("HTTPError with reason code {}: {}".
#               format(error.response.status_code, error.response.reason))
#         resp = None
#         if 500 <= error.response.status_code < 600 and num_retries > 0:
#             print("Attempting retry (remaining = {})".format(num_retries))
#             return download(url, num_retries-1)
#     return resp





class Downloader:
    """ Downloader class to use cache and requests for downloading pages.
        For contructor, pass:
            delay (int): # of secs delay between requests (default: 5)
            user_agent (str): user agent string (default: 'wswp')
            proxies (list[dict]): list of possible proxies, each
                must be a dict with http / https keys and proxy values
            cache (dict or dict-like obj): keys: urls, values: dicts with keys (html, code)
            timeout (float/int): number of seconds to wait until timeout
    """

    def __init__(self, delay=2, user_agent='wswp', proxies=None, cache={},
                 timeout=60):
        self.throttle = Throttle(delay)
        self.user_agent = user_agent
        self.proxies = proxies
        self.cache = cache
        self.num_retries = None  # we will set this per request
        self.timeout = timeout

    def __call__(self, url, num_retries=2):
        """ Call the downloader class, which will return HTML from cache
            or download it
            args:
                url (str): url to download
            kwargs:
                num_retries (int): # times to retry if 5xx code (default: 2)
        """
        self.num_retries = num_retries
        try:
            result = self.cache[url]
            logging.info('Loaded from cache:', url)
        except KeyError:
            result = None
        if result and self.num_retries and 500 <= result['code'] < 600:
            # server error so ignore result from cache
            # and re-download
            result = None
        if result is None:
            # result was not loaded from cache, need to download
            self.throttle.wait(url)
            proxies = choice(self.proxies) if self.proxies else None
            headers = {'User-Agent': choice(self.user_agent)}
            result = self.download(url, headers, proxies)
            self.cache[url] = result
        return result['html']

    def download(self, url, headers, proxies):
        """ Download a and return the page content
            args:
                url (str): URL
                headers (dict): dict of headers (like user_agent)
                proxies (dict): proxy dict w/ keys 'http'/'https', values
                    are strs (i.e. 'http(s)://IP') (default: None)
        """
        logging.info('Downloading:', url)
        try:
            resp = requests.get(url, headers=headers, proxies=proxies,
                                timeout=self.timeout)
            html = resp.text
            if resp.status_code >= 400:
                logging.error('Download error:', resp.text)
                html = None
                if self.num_retries and 500 <= resp.status_code < 600:
                    # recursively retry 5xx HTTP errors
                    self.num_retries -= 1
                    return self.download(url, headers, proxies)
        except requests.exceptions.RequestException as e:
            logging.error('Download error:', e)
            return {'html': None, 'code': 500}
        return {'html': html, 'code': resp.status_code}


class DiskCache:
    """ DiskCache helps store urls and their responses to disk
        Intialization components:
            cache_dir (str): abs file path or relative file path
                for cache directory (default: ../data/cache)
            max_len (int): maximum filename length (default: 255)
            compress (bool): use zlib compression (default: True)
            encoding (str): character encoding for compression (default: utf-8)
            expires (datetime.timedelta): timedelta when content will expire
                (default: 30 days ago)
    """

    def __init__(self, cache_dir='../data/cache', max_len=255, compress=True,
                 encoding='utf-8', expires=timedelta(days=30)):
        self.cache_dir = cache_dir
        self.max_len = max_len
        self.compress = compress
        self.encoding = encoding
        self.expires = expires

    def url_to_path(self, url):
        """ Return file system path string for given URL """
        components = urlsplit(url)
        # append index.html to empty paths
        path = components.path
        if not path:
            path = '/index.html'
        elif path.endswith('/'):
            path += 'index.html'
        filename = components.netloc + path + components.query
        # replace invalid characters
        filename = re.sub(r'[^/0-9a-zA-Z\-.,;_ ]', '_', filename)
        # restrict maximum number of characters
        filename = '/'.join(seg[:self.max_len] for seg in filename.split('/'))
        return os.path.join(self.cache_dir, filename)

    def __getitem__(self, url):
        """Load data from disk for given URL"""
        path = self.url_to_path(url)
        if os.path.exists(path):
            mode = ('rb' if self.compress else 'r')
            with open(path, mode) as fp:
                if self.compress:
                    data = zlib.decompress(fp.read()).decode(self.encoding)
                    data = json.loads(data)
                else:
                    data = json.load(fp)
            exp_date = data.get('expires')
            if exp_date and datetime.strptime(exp_date,
                                              '%Y-%m-%dT%H:%M:%S') <= datetime.utcnow():
                logging.info('Cache expired!', exp_date)
                raise KeyError(url + ' has expired.')
            return data
        else:
            # URL has not yet been cached
            raise KeyError(url + ' does not exist')

    def __setitem__(self, url, result):
        """Save data to disk for given url"""
        path = self.url_to_path(url)
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        mode = ('wb' if self.compress else 'w')
        # Note: the timespec command requires Py3.6+ (if using 3.X you can
        # export using isoformat() and import with '%Y-%m-%dT%H:%M:%S.%f'
        result['expires'] = (datetime.utcnow() + self.expires).isoformat(
            timespec='seconds')
        with open(path, mode) as fp:
            if self.compress:
                data = bytes(json.dumps(result), self.encoding)
                fp.write(zlib.compress(data))
            else:
                json.dump(result, fp)


if __name__ == "__main__":
    pass
