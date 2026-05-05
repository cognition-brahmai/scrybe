import requests

url = "http://127.0.0.1:8420/v1/parse/markdown?url=https://brahmai.in"
response = requests.get(url)
print(response.text)