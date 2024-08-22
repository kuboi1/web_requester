import requests
import time
import json
import os
from requests import Response
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError
from datetime import datetime


COLOR_OK = '\033[32m'       # Green
COLOR_ERR = '\033[31m'      # Red
COLOR_WAR = '\033[33m'      # Yellow
COLOR_MAG = '\033[95m'      # Magenta
COLOR_CYA = '\033[96m'     # Cyan
COLOR_DEFAULT = '\033[0m'   # White (reset)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
REQUESTS_PATH = os.path.join(BASE_PATH, 'requests')
RESPONSES_PATH = os.path.join(BASE_PATH, 'responses')


class Requester:
    namespace: str
    mode: str
    url: str
    settings: dict
    requests: dict
    common: dict

    def __init__(self, settings: dict) -> None:
        self._print_intro()

        self.settings = settings

        namespaces = self._get_namespaces()

        if len(namespaces) == 0:
            print(f'{COLOR_ERR}No valid request json files found at \'{REQUESTS_PATH}\'{COLOR_DEFAULT}')
            exit()
        
        # Pick from available namespaces if namespace not specified in settings
        self.namespace = settings['namespace'] if 'namespace' in settings else self._pick_namespace(namespaces)

        # Validate namespace
        if self.namespace not in self._get_namespaces().values():
            print(f'{COLOR_ERR}Invalid namespace \'{self.namespace}\'{COLOR_DEFAULT}')
            exit()

        self._load_requests()
    
    def _get_namespaces(self) -> dict:
        namespaces = {}
        for i, file in enumerate(os.listdir(REQUESTS_PATH)):
            if file.endswith('example'):
                continue
            namespaces[i - 1] = file.split(".")[0]
        
        return namespaces
    
    def _pick_namespace(self, namespaces: dict) -> str:
        print('Pick a namespace:')
        print()

        for i in namespaces:
            print(f' > {i}\t{COLOR_CYA}{namespaces[i]}{COLOR_DEFAULT}')
        
        self._print_quit_option()
        
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

            print()

            return namespaces[namespace_num]


    def _load_requests(self) -> dict:
        # Load namespace requests data
        with open(os.path.join(REQUESTS_PATH, f'{self.namespace}.json'), 'r') as f:
            data = json.load(f)
        
        mode = self.settings['mode']
        
        if mode not in data['url']:
            print(f'{COLOR_ERR}Missing url for mode \'{mode}\' in namespace \'{self.namespace}\'{COLOR_DEFAULT}')
            exit()
        
        self.mode = mode
        self.url = data['url'][mode]
        self.requests = {key: data['requests'][key] for key in data['requests'] if 'mode' not in data['requests'][key] or data['requests'][key]['mode'] == mode}
        self.common = data['common'] if 'common' in data else {}
    
    def _send_request(self, request_name: str) -> Response:
        # Reload requests if liveReload is set to true
        if 'liveReload' in self.settings and self.settings['liveReload']:
            self._load_requests()

        request = self.requests[request_name]

        # Add common request values
        request = self._add_common(request)

        target_link = f'{self.url}/{request["endpoint"]}'
        method = request['method']

        headers = request['headers'] if 'headers' in request else None
        id = request['id'] if 'id' in request else None
        params = request['parameters'] if 'parameters' in request else None
        body = request['body'] if 'body' in request else None
        basicAuth = request['basicAuth'] if 'basicAuth' in request else None

        # Send the request
        target_link = f'{target_link}/{id}' if id is not None else target_link

        url_params = '?' + '&'.join([f'{key}={params[key]}' for key in params]) if params != None else ''

        print()
        print(f'Sending {COLOR_MAG}{method}{COLOR_DEFAULT} {COLOR_CYA}{request_name}{COLOR_DEFAULT} request to: {target_link}{url_params}...')

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

        return response

    def _save_response(self, request_name: str, response: Response) -> str:
        content_type = response.headers['Content-Type']
        datetime_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        file_name = f'{request_name}_{datetime_str}'

        # Create a response directory for the namespace if not exist
        dir_path = (os.path.join(RESPONSES_PATH, self.namespace))
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

        match content_type:
            case 'application/pdf':
                file_path = os.path.join(dir_path, f'{file_name}.pdf')
                with open(file_path, 'wb') as response_f:
                    response_f.write(response.content)
            case _:
                file_path = os.path.join(dir_path, f'{file_name}.json')
                response_data = self._create_json_response_data(response)
                with open(file_path, 'w') as response_f:
                    json.dump(response_data, response_f)
        
        return file_path
    
    def _create_json_response_data(self, response: Response) -> dict:
        try:
            response_content = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f'{COLOR_WAR}Failed to json decode response content - using raw content instead{COLOR_DEFAULT}')
            response_content = response.text

        if 'contentOnly' in self.settings and self.settings['contentOnly']:
            return response_content
        
        return {
            'status': response.status_code,
            'reason': response.reason,
            'headers': dict(response.headers),
            'content': response_content
        }

    def _add_common(self, request: dict) -> dict:
        for key in self.common:
            if key not in request:
                request[key] = self.common[key]
                continue

            for subkey in self.common[key]:
                if subkey not in request[key]:
                    request[key][subkey] = self.common[key][subkey]
        
        return request

    def _print_intro(self) -> None:
        print('-------------------')
        print('|  WEB REQUESTER  |')
        print('-------------------')
        print()
    
    def _print_quit_option(self) -> None:
        print()
        print(f' > q\t{COLOR_MAG}QUIT{COLOR_DEFAULT}')
        print()

    def print_options(self) -> None:
        print(f'Requests for {COLOR_CYA}{self.namespace}{COLOR_DEFAULT} in {COLOR_MAG}{self.mode}{COLOR_DEFAULT} mode:')
        print()
        for i, name in enumerate(self.requests.keys()):
            method = self.requests[name]['method']
            endpoint = self.requests[name]['endpoint']
            id = self.requests[name]['id'] if 'id' in self.requests[name] else None

            option = f'{i}\t{COLOR_MAG}{method}{COLOR_DEFAULT} {COLOR_CYA}{name}{COLOR_DEFAULT}'
            url = f'{self.url}/{endpoint}{f"/{id}" if id is not None else ""}'

            print(f' > {option} => {url}')
        
        self._print_quit_option()

    def request(self, number: str) -> None:
        request_name = list(self.requests.keys())[number]

        response = self._send_request(request_name)

        file_path = self._save_response(request_name, response)
        
        status = response.status_code
        reason = response.reason
        elapsed_ms = response.elapsed.total_seconds() * 1000

        status_color = COLOR_OK if response.ok else COLOR_ERR
        ms_color = COLOR_OK

        if elapsed_ms >= 20000:
            ms_color = COLOR_ERR
        elif elapsed_ms >= 5000:
            ms_color = COLOR_WAR

        print(f'Response returned with {status_color}{status} ({reason}) {COLOR_DEFAULT}in {ms_color}{elapsed_ms:.1f} ms{COLOR_DEFAULT}')
        print(f'Response file: {file_path}')
        print()


def load_settings() -> dict:
    with open('settings.json', 'r', encoding='utf-8') as requests_f:
        return json.load(requests_f)


def main() -> None:
    settings = load_settings()

    requester = Requester(settings)

    while True:
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

