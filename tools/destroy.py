import requests
from threading import Thread

bearer = "HR6BZZWSM3AILUW6WQPIWEYZZ5622ECEJMOQ"


def filterNull(json):
    """Remove null dict entries."""
    for key, value in tuple(json.items()):
        if value is None:
            del json[key]
    return json


def listInstances(bearer, tag=None, label=None, main_ip=None) -> dict:
    """
    List vpses on user's vultr account.

    Args:
        tag: filter results by tag
        label: filter results by label
        main_ip: filter results by main_ip
    """
    json = filterNull({"tag": tag, "label": label, "main_ip": main_ip})

    headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"}

    req = requests.get(
        "https://api.vultr.com/v2/instances", headers=headers, params=json
    )
    req = req.json()
    if len(req["instances"]) == 0:
        return None
    try:
        return req["instances"]
    except KeyError:
        return req.status_code


instances = listInstances(bearer, tag="Sniper34382")
for instance in instances:
    def delete(instance):
        req = requests.delete(
            "https://api.vultr.com/v2/instances/" + instance["id"],
            headers={
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/json",
            },
        )
        print(req.status_code)
    Thread(target=delete, args=(instance,)).start()
