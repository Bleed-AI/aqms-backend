import json
import time
from os.path import exists
import http.client
from urllib.parse import urlparse
import chalk
# chalk colors 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
from fastapi.exceptions import HTTPException

from app.utils import Singleton
from app.config import AppConfig, ICApiUrls
from app.utils import Log as log

config = AppConfig()


class PeplinkCore(metaclass=Singleton):
    def __init__(self):
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.token_expires_in: float = 0
        self.token_obtained_at: float = 0

    # generic method for fetching data from Peplink API

    def fetch_api_data(self, url, **kwargs):
        try:
            if self.is_token_expired():
                print("Token is expired. Trying to get new one.")
                self.try_issuing_token()
            headers = {
                "Authorization": "Bearer {}".format(self.access_token),
                "Content-Type": "application/json"
            }
            final_url = "{base}{passed_url}".format(
                base=ICApiUrls.base_url, passed_url=url)
            for k, v in kwargs.items():
                if k == "limit":
                    final_url = final_url + "&limit={}".format(v)
                if k == "page":
                    final_url = final_url + "&page={}".format(v)
                if k == "start":
                    final_url = final_url + "&start={}".format(v)
                if k == "end":
                    final_url = final_url + "&end={}".format(v)
            print(final_url)
            url_components = urlparse(final_url)
            conn = None
            if url_components.scheme == "https":
                conn = http.client.HTTPSConnection(url_components.netloc)
            else:
                conn = http.client.HTTPConnection(url_components.netloc)
            path = "{}?{}".format(url_components.path, url_components.query)
            payload = ''
            conn.request("GET", path, payload, headers)
            res = conn.getresponse()
            print("res.status {}".format(res.status))
            if res.status == 200:
                data = res.read().decode("utf-8")
                json_data = json.loads(data)
                return json_data
            elif res.status == 401:
                print("Unauthorized. Going to get new token.")
                self.try_issuing_token()
                return self.fetch_api_data(url, **kwargs)
            else:
                return None
        except Exception as e:
            print(chalk.red("Exception in fetch_api_data: {}".format(e)))
            log.error("Exception in fetch_api_data: {}".format(e))
            raise HTTPException(
                500, detail="Error in fetching resource from InControl 2 API. {}".format(e))

    def post_api_data(self, url, data, content_type="application/json"):
        try:
            if self.is_token_expired():
                print("Token is expired. Trying to get new one.")
                self.try_issuing_token()
            headers = {
                "Authorization": "Bearer {}".format(self.access_token),
                "Content-Type": content_type,
            }
            final_url = "{base}{passed_url}".format(
                base=ICApiUrls.base_url, passed_url=url)
            print(final_url)
            url_components = urlparse(final_url)
            conn = None
            if url_components.scheme == "https":
                conn = http.client.HTTPSConnection(url_components.netloc)
            else:
                conn = http.client.HTTPConnection(url_components.netloc)
            path = "{}?{}".format(url_components.path, url_components.query)
            data = json.dumps(data)
            conn.request("POST", path, data, headers)
            res = conn.getresponse()
            print("res.status {}".format(res.status))
            if res.status == 200:
                data = res.read().decode("utf-8")
                json_data = json.loads(data)
                return json_data
            elif res.status == 401:
                self.try_issuing_token()
                return self.post_api_data(url, data)
            else:
                return None
        except Exception as e:
            print(chalk.red("Exception in posting resource: {}".format(e)))
            log.error("Exception in post_api_data: {}".format(e))
            raise HTTPException(
                500, detail="Error in posting resource at InControl 2 API. {}".format(e))

    def put_api_data(self, url, data):
        try:
            if self.is_token_expired():
                print("Token is expired. Trying to get new one.")
                self.try_issuing_token()
            headers = {
                "Authorization": "Bearer {}".format(self.access_token),
                "Content-Type": "application/json"
            }
            final_url = "{base}{passed_url}".format(
                base=ICApiUrls.base_url, passed_url=url)
            print(final_url)
            url_components = urlparse(final_url)
            conn = None
            if url_components.scheme == "https":
                conn = http.client.HTTPSConnection(url_components.netloc)
            else:
                conn = http.client.HTTPConnection(url_components.netloc)
            path = "{}?{}".format(url_components.path, url_components.query)
            data = json.dumps(data)
            conn.request("PUT", path, data, headers)
            res = conn.getresponse()
            print("res.status {}".format(res.status))
            if res.status == 200:
                data = res.read().decode("utf-8")
                json_data = json.loads(data)
                return json_data
            elif res.status == 401:
                self.try_issuing_token()
                return self.put_api_data(url, data)
            else:
                return None
        except Exception as e:
            print(chalk.red("Exception in updating resource: {}".format(e)))
            log.error("Exception in put_api_data: {}".format(e))
            raise HTTPException(
                500, detail="Error in updating resource at InControl 2 API. {}".format(e))

    def delete_api_data(self, url, data):
        try:
            if self.is_token_expired():
                print("Token is expired. Trying to get new one.")
                self.try_issuing_token()
            headers = {
                "Authorization": "Bearer {}".format(self.access_token),
                "Content-Type": "application/json"
            }
            final_url = "{base}{passed_url}".format(
                base=ICApiUrls.base_url, passed_url=url)
            print(final_url)
            url_components = urlparse(final_url)
            conn = None
            if url_components.scheme == "https":
                conn = http.client.HTTPSConnection(url_components.netloc)
            else:
                conn = http.client.HTTPConnection(url_components.netloc)
            path = "{}?{}".format(url_components.path, url_components.query)
            data = json.dumps(data)
            conn.request("DELETE", path, data, headers)
            res = conn.getresponse()
            print("res.status {}".format(res.status))
            if res.status == 200:
                data = res.read().decode("utf-8")
                json_data = json.loads(data)
                return json_data
            elif res.status == 401:
                self.try_issuing_token()
                return self.delete_api_data(url, data)
            else:
                return None
        except Exception as e:
            print(chalk.red("Exception in updating resource: {}".format(e)))
            log.error("Exception in delete_api_data: {}".format(e))
            raise HTTPException(
                500, detail="Error in updating resource at InControl 2 API. {}".format(e))

    def is_token_expired(self):
        try:
            now = time.time()
            if self.token_obtained_at + self.token_expires_in > now:
                return False  # token is valid
            else:
                return True  # token is expired
        except Exception as e:
            print(chalk.red("Exception in updating resource: {}".format(e)))
            log.error("Exception in is_token_expired: {}".format(e))
            raise HTTPException(
                500, detail="Error in updating resource at InControl 2 API. {}".format(e))

    # get token from peplink API
    def get_token(self, **kwargs):
        try:
            headers = {
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            url = "{base}{token_url}".format(
                base=ICApiUrls.base_url, token_url=ICApiUrls.get_token)
            url_components = urlparse(url)
            conn = None
            if url_components.scheme == "https":
                conn = http.client.HTTPSConnection(url_components.netloc)
            else:
                conn = http.client.HTTPConnection(url_components.netloc)
            payload = "client_id={client_id}&grant_type=client_credentials&client_secret={client_secret}".format(
                client_id=config.ic_api_client_id, client_secret=config.ic_api_client_secret)
            conn.request("POST", url_components.path, payload, headers)
            response = conn.getresponse()
            if response.status == 200:
                result = response.read().decode("utf-8")
                json_data = json.loads(result)
                if type(json_data) is dict and "access_token" in json_data:
                    self.access_token = json_data["access_token"]
                    self.refresh_token = json_data["refresh_token"]
                    self.token_expires_in = float(json_data["expires_in"])
                    self.token_obtained_at = float(time.time())
                    print(self.access_token)
                    return True
                else:
                    return False
            else:
                return False
        except Exception as e:
            print(chalk.red("Exception in updating resource: {}".format(e)))
            log.error("Exception in get_token: {}".format(e))
            raise HTTPException(
                500, detail="Error in updating resource at InControl 2 API. {}".format(e))

    def try_issuing_token(self):
        try_count = 1
        while self.get_token() == False:
            try_count += 1
            if try_count > 5:
                raise HTTPException(
                    401, detail="Unable to get token from InControl 2 API")
        return True

    def raise_and_print_error(self, msg):
        print(chalk.red(msg))
        raise HTTPException(500, detail=msg)
