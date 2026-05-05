import requests

url = "https://r.jina.ai/https://brahmai.in"
headers = {
    "Authorization": "Bearer jina_6a3541dd80e64ce69aa9bd0b68a1a366te1PYGm1XGr2UQpf9fsemguF36wB"
}

response = requests.get(url, headers=headers)

print(response.text)