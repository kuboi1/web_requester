# Web Requester

## Usage

* Sends requests to specified endpoints

### Requests
* Requests are specified in the **requests/** directory
* Requests are seperated into **namespaces**
* Each namespace has it's own json config file in format *{namespace}.json*
* Example of such file is included in the repository (*requests/namespace.json.example*)
* Each request has it's own name
* The *"common"* values are sent with each request

### Responses
* Requester currently supports *.json* and *.pdf* responses
* Responses are saved into the **responses/*{namespace}*** directory in *{request_name}\_{datetime}.{ext}* format

### Settings
* Settings are specified in a **settings.json** file
* Example of such file is included in the repository (*settings.json.example*)
* There are 2 settings you can specify:
    * *mode* [required] - Specifies the mode with which the app should start (PROD|DEV|LOCAL for example but you can add as many as you want)
    * *namespace* [optional] - Specifies the namespace which the app should load on start (if not present, you will be promted to pick one of the available namespaces)
    * *contentOnly* [optional|default: false] - Specifies if the status, reason and headers of the response should be saved or just the body content (Works for *.json* responses only)
    * *liveReload* [optional|default: false] - Specifies if the requests should be reloaded on each request sent. This allows for editing the requests in the json file without restarting the program (might cause some slight performance issues with large json files)

## Dependencies
* [Python 3.10+](https://www.python.org/downloads/)
* **requests** Python package (`pip install requests`)