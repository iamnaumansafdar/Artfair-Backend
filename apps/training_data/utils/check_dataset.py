import requests, environ
env = environ.Env(overwrite=True)
root_path = environ.Path(__file__) - 2
env.read_env(str(root_path.path(".env")))

def check_dataset_existence(dataset_name, hf_token):
    headers = {"Authorization": f"Bearer {hf_token}"}
    dataset_name = f"{env("HF_DATASET_NAME")}/{dataset_name}"
    API_URL = f"https://datasets-server.huggingface.co/is-valid?dataset={dataset_name}"
    response = requests.get(API_URL, headers=headers)
    data =  response.json()
    if data.get("preview") and data.get("viewer"):
        return True 
    else:
        return False