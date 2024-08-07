import requests
import time
import json
import os
from requests import Response
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError
from datetime import datetime

MODE_PRODUCTION = 'PROD'
MODE_DEV = 'DEV'
MODE_LOCAL = 'LOCAL'

COLOR_OK = '\033[32m'       # Green
COLOR_ERR = '\033[31m'      # Red
COLOR_WAR = '\033[33m'      # Yellow
COLOR_DEFAULT = '\033[0m'   # White (reset)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
REQUESTS_PATH = os.path.join(BASE_PATH, 'requests')


class Requester:
    namespace: str
    mode: str
    url: str
    requests: dict
    request_time: int

    def __init__(self, settings: dict) -> None:
        self._print_intro()

        namespaces = self._get_namespaces()

        if len(namespaces) == 0:
            print(f'{COLOR_ERR}No valid request json files found at \'{REQUESTS_PATH}\'{COLOR_DEFAULT}')
            exit()
        
        # Pick from available namespaces if namespace not specified in settings
        self.namespace = settings['namespace'] if 'namespace' in settings else self._pick_namespace(namespaces)

        self._load_requests(settings['mode'])
    
    def _get_namespaces(self) -> dict:
        namespaces = {}
        for i, file in enumerate(os.listdir(REQUESTS_PATH)):
            if file.endswith('example'):
                continue
            namespaces[i - 1] = file.split(".")[0]
        
        return namespaces
    
    def _pick_namespace(self, namespaces: dict) -> str:
        for i in namespaces:
            print(f' > {i}: {namespaces[i]}')
        
        print()
        print(' > q: QUIT')
        print()
        
        while True:
            namespace_num = input('> Namespace number: ')

            if namespace_num == 'q':
                exit()

            if not namespace_num.isnumeric():
                print(f'{COLOR_WAR}Not a number{COLOR_DEFAULT}')
                continue

            namespace_num = int(namespace_num)

            if namespace_num not in namespaces:
                print(f'{COLOR_WAR}Invalid namespace number{COLOR_DEFAULT}')
                continue

            return namespaces[namespace_num]

    def _load_requests(self, mode: str) -> dict:
        if self.namespace not in self._get_namespaces().values():
            print(f'{COLOR_ERR}Invalid namespace \'{self.namespace}\'{COLOR_DEFAULT}')
            exit()
        
        if mode not in [MODE_PRODUCTION, MODE_DEV, MODE_LOCAL]:
            print(f'{COLOR_ERR}Invalid mode \'{mode}\'{COLOR_DEFAULT}')
            exit()
        
        with open(os.path.join(REQUESTS_PATH, f'{self.namespace}.json'), 'r') as f:
            data = json.load(f)
        
        if mode not in data['url']:
            print(f'{COLOR_ERR}Missing url for mode \'{mode}\' in namespace \'{self.namespace}\'{COLOR_DEFAULT}')
            exit()
        
        self.mode = mode
        self.url = data['url'][mode]
        self.requests = data['requests']
    
    def _send_request(self, request_name: str) -> Response:
        request = self.requests[request_name]

        target_link = f'{self.url}/{request["endpoint"]}'
        method = request['method']
        headers = request['headers']

        id = request['id'] if 'id' in request else None
        params = request['parameters'] if 'parameters' in request else None
        body = request['body'] if 'body' in request else None
        basicAuth = request['basicAuth'] if 'basicAuth' in request else None

        #Send the request
        target_link = f'{target_link}/{id}' if id is not None else target_link

        url_params = '?' + '&'.join([f'{key}={params[key]}' for key in params]) if params != None else ''

        print()
        print(f'Sending {method} request {request_name} to: {target_link}{url_params}...')

        start_time = time.time()

        match method:
            case 'GET':
                response = requests.get(
                    target_link, 
                    params=params,
                    headers=headers,
                    auth=HTTPBasicAuth(basicAuth['username'], basicAuth['password']) if basicAuth is not None else None
                )
            case 'POST':
                response = requests.post(
                    target_link, 
                    params=params, 
                    headers=headers,
                    json=body, 
                    auth=HTTPBasicAuth(basicAuth['username'], basicAuth['password']) if basicAuth is not None else None
                )
            case 'PUT':
                response = requests.put(
                    target_link, 
                    params=params, 
                    headers=headers,
                    json=body, 
                    auth=HTTPBasicAuth(basicAuth['username'], basicAuth['password']) if basicAuth is not None else None
                )
            case _:
                print(f'{COLOR_ERR}Unsupported method \'{method}\'{COLOR_DEFAULT}')
                exit()

        end_time = time.time()

        self.request_time = (int) ((end_time - start_time) * 1000)

        return response

    def _save_response(self, request_name: str, response: Response) -> None:
        content_type = response.headers['Content-Type']
        datetime_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        match content_type:
            case 'application/pdf':
                ext = 'pdf'
            case _:
                ext = 'json'

        with open(f'responses/{datetime_str}_{self.namespace}_{request_name}.{ext}', 'wb') as response_f:
            response_f.write(response.content)

    def _print_intro(self) -> None:
        print('---------')
        print('REQUESTER')
        print('---------')
        print()

    def print_options(self) -> None:
        print(f'Requests for {self.namespace} in {self.mode} mode:')
        for i, name in enumerate(self.requests.keys()):
            print(f' > {i} {name}: {self.requests[name]["method"]} => {self.url}/{self.requests[name]["endpoint"]}')
        print()
        print(' > q: QUIT')
        print()

    def request(self, number: str) -> None:
        request_name = list(self.requests.keys())[number]

        response = self._send_request(request_name)

        self._save_response(request_name, response)
        
        status = response.status_code
        reason = response.reason

        status_color = COLOR_OK if status == 200 else COLOR_ERR
        ms_color = COLOR_OK

        if self.request_time >= 20000:
            ms_color = COLOR_ERR
        elif self.request_time >= 5000:
            ms_color = COLOR_WAR

        print(f'Response returned with {status_color}{status} ({reason}) {COLOR_DEFAULT}in {ms_color}{self.request_time} ms{COLOR_DEFAULT}')


def load_settings() -> dict:
    with open('settings.json', 'r', encoding='utf-8') as requests_f:
        return json.load(requests_f)


def main() -> None:
    settings = load_settings()

    requester = Requester(settings)

    while True:
        print()
        requester.print_options()

        request_number = input('> Request number: ')

        if request_number == 'q':
            break

        if not request_number.isnumeric():
            print(f'{COLOR_WAR}Not a number{COLOR_DEFAULT}')
            continue
        
        request_number = int(request_number)

        if request_number < 0 or request_number >= len(requester.requests):
            print(f'{COLOR_WAR}Invalid request number{COLOR_DEFAULT}')
            continue

        try:
            requester.request(request_number)
        except ConnectionError as err:
            print()
            print(f'{COLOR_ERR}REQUEST FAILED WITH A CONNECTION ERROR:{COLOR_DEFAULT}')
            print(err)


if __name__ == '__main__':
    main()

