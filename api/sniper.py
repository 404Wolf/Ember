from time import time, sleep  # to get current UNIX timestamp
import json
from urllib import response  # json parsing
import requests  # for web requests
from msauth import login  # microsoft auth
import socket  # for socket web requests
import ssl  # for socket web requests
from threading import Thread  # for multithreading
import random  # for sleep variation

"""
Important Note!

This is the sniper file! It will not work alone.
This file only works when automatically sent to VPSes with the main script.
"""

setup = json.load(open("setup.json"))
config = json.load(open("config.json"))

apiUrl = "http://" + config["api"]["ip"] + ":" + str(config["api"]["port"])
apiAuth = (config["api"]["login"]["username"], config["api"]["login"]["password"])

# function for sending messages to the status chat
def send(message):
    """
    Logging delays used to the vps status chat
    """

    print(message)

    requests.post(
        url=apiUrl + "/discord/send",
        auth=apiAuth,
        headers={
            "message": message,
            "webhook": config["sniper"]["vpsStatusWebhook"],
            "vps": str(setup["vpsNum"]),
        },
    )


def success(bearer):
    """
    Send webhooks, and status info, for successful snipes
    """

    # send that the name was sniped to chat, before generating nice embeds
    send(
        f"[<3] Successfully sniped {setup['target']} onto \\*\\*\\*"
        + bearer[1][2:]
        + "!"
    )

    # change the account's skin to the ember skin
    skin = requests.post(
        "https://api.minecraftservices.com/minecraft/profile/skins",
        headers={
            "Authorization": f"Bearer " + bearer[0],
            "Content-Type": "application/json",
        },
        json={"url": config["sniper"]["skinTextureUrl"], "variant": "slim"},
    )

    # attempt to change skin of winning account
    if skin.status_code == 200:  # 200 = success
        send(f"[<3] Skin successfully changed.")
    else:  # otherwise, the skin failed to hange
        send(f"[!] Skin failed to change.")

    # attempt to use jam's api to get searches, or set to NONE if the api doesn't respond
    try:
        resp = requests.get(
            apiUrl + "/namemc/" + target,
            auth=apiAuth,
            timeout=10,
        )
        searches = str(resp.json()["searches"])
        send(f"[<3] Searches for {setup['target']}: {searches}")
    except:
        searches = None
        send("[!] Failed to fetch searches!")

    # create embed for successful snipe log webhook
    successJson = {
        "content": None,
        "embeds": [
            {
                "title": "Ember Logs :fire:",
                "color": 15157547,  # nice orange color
                "fields": [
                    {"name": "Target", "value": setup["target"], "inline": True},
                    {
                        "name": "VPS",
                        "value": f"VPS#**{setup['vpsNum']}**",  # vps that won the snipe
                        "inline": True,
                    },
                    {
                        "name": "Account",
                        "value": "\\*\\*\\*"
                        + bearer[1][2:],  # email snipe was won onto
                        "inline": True,
                    },
                    {
                        "name": "Type",
                        "value": "Giftcard",  # this sniper is for giftcards only
                        "inline": True,
                    },
                    {
                        "name": "Searches",
                        "value": str(searches).replace("None", "error"),
                        "inline": True,
                    },
                    {
                        "name": "Offset",
                        "value": str(
                            round(setup["offsets"][setup["vpsNum"] - 1], 3)
                        ),  # offsets used on this vps
                        "inline": True,
                    },
                ],
                "thumbnail": {
                    "url": config["general"]["emberThumbnail"]
                },  # ember logo for the thumbnail
            }
        ],
    }

    # post the webhook with the delay log embed
    requests.post(url=config["sniper"]["successSnipeLogWebhook"], json=successJson)
    send("[<3] Log embed sent!")

    # make an announcement to the public server saying that the snipe was won
    announcement = {
        "content": None,
        "embeds": [
            {
                "title": "**Ember** Snipe!",
                "description": f"**[Ember](https://solo.to/ember)** just discovered [{setup['target']}](https://namemc.com/search?q={setup['target']}) flavoured chocolate, with **{searches}** searches!".replace(
                    ", with **None** searches", ""
                ),  # modify if unable to fetch searches
                "color": 15157547,
                "footer": {"text": "-Ember Sniper"},
                "thumbnail": {"url": config["general"]["emberThumbnail"]},
            }
        ],
    }

    # POST the webhook to the respective discord chat
    requests.post(url=config["sniper"]["successSnipeWebhook"], json=announcement)
    send("[<3] Webhook sent successfully!")


def delayLogs(requestsOutput):
    """
    Function to log delays via discord webhook.
    Takes the sorted delay string as an input, and POSTs to discord an organized embed.
    """
    delayLog = {
        "content": None,
        "embeds": [
            {
                "title": f"Delay Logs - {setup['target']}",  # title says "Delay Logs - <target>"
                "description": f"```swift\n{requestsOutput}\n```",
                "color": 000000,  # black
                "fields": [
                    {
                        "name": "Target:",
                        "value": str(setup["target"]),
                        "inline": True,
                    },  # target
                    {
                        "name": "Offset:",
                        "value": str(
                            round(setup["offsets"][setup["vpsNum"] - 1], 3)
                        ),  # offsets used on this vps
                        "inline": True,
                    },
                    {
                        "name": "VPS:",
                        "value": str(setup["vpsNum"]),  # this vps's number
                        "inline": True,
                    },
                ],
                "thumbnail": {
                    "url": config["general"]["emberThumbnail"]
                },  # ember's logo as thumbnail
            }
        ],
    }

    requests.post(
        url=apiUrl + "/discord/send",
        auth=apiAuth,
        headers={
            "message": json.dumps(delayLog),
            "webhook": config["sniper"]["delayLogWebhook"],
            "vps": str(setup["vpsNum"]),
        },
    )


# gather bearers
bearers = []
for account in setup["accounts"]:
    try:
        bearers.append(
            (
                login(account["email"], account["password"])["access_token"],
                account["email"],
            )
        )
        send(f"Successfully logged into **\*\*\*" + account["email"][2:] + "**")
        if account != setup["accounts"][-1]:
            sleep(23)
    except:
        send(f"Unable to login to **\*\*\*" + account["email"][2:] + "**")

# Pre-setting important global variables
requestsOutput = ""  # string with request output
sendsReqs = []  # array of snipe send requests
receivesReqs = []  # array of snipe receive requests
times = {
    "target": setup["target"],
    "vpsNum": setup["vpsNum"],
    "sends": [],
    "receives": [],
}  # dict to send back to api to log times

# Begin sniping...
def snipe():
    global sendsReqs
    global receivesReqs

    randomSleeps = [random.uniform(0.0002, 0.0009) for i in range(30)]

    # sockets die shortly after being created, so begin the snipe setup 9 seconds early
    sleep((setup["droptime"] - time()) - 7)

    # credit to cryst6l#1337 for help with socket requests
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(
            ("api.minecraftservices.com", 443)
        )  # make a connection to minecraft servers
        context = ssl.create_default_context()  # create a secure tunnel for requests

        # make connection with the endpoint
        with context.wrap_socket(s, server_hostname="api.minecraftservices.com") as ss:

            sleep(
                setup["droptime"]
                - time()
                - (setup["offsets"][setup["vpsNum"] - 1] / 1000)
            )  # wait it out

            # send requests
            for counter, bearer in enumerate(bearers, start=1):
                snipeInfo = bytes(
                    "\r\n".join(
                        [
                            "POST /minecraft/profile HTTP/1.1",
                            "Host: api.minecraftservices.com",
                            "Content-Type: application/json",
                            f"Authorization: Bearer {bearer[0]}",
                            "Content-Length: %d"
                            % len('{"profileName": "%s"}' % target),
                            "",
                            '{"profileName": "%s"}' % target,
                        ]
                    ),
                    "utf-8",
                )  # data for POST request to set profile

                # make the name change requests (equal to the number of requests in request_count)
                ss.send(snipeInfo)
                sendsReqs.append((time(), counter))  # log send time

                # add randomness
                sleep(randomSleeps[counter])

            # receive requests
            for counter, bearer in enumerate(bearers, start=1):
                # check the responses one by one
                data = ss.recv(1000).decode("utf-8")[9:12]  # get request status code
                receivesReqs.append(
                    (time(), counter, int(data), bearer)
                )  # add request response to receivesReqs array


# set up multithreading
target = setup["target"]
threads = [Thread(target=snipe) for thread in range(config["sniper"]["requestsPerBearer"])]
[thread.start() for thread in threads]

# wait for snipes to go down
sleep(setup["droptime"] - time())
print("Snipes went down!")
[thread.join() for thread in threads]

sleep(len(threads) * 0.5)  # ensure threads have closed fully

# create an organized string with the all the logged requests
for sendReq in sendsReqs:
    requestsOutput += (
        "."
        + str("{:.7f}".format(sendReq[0])).split(".")[1]
        + " [S"
        + str(sendReq[1])
        + "] /////\n"
    )
    times["sends"].append(
        {
            "time": float(sendReq[0]),
            "bearer": int(sendReq[1]),
            "offset": (setup["offsets"][setup["vpsNum"] - 1]),
        }
    )
for receiveReq in receivesReqs:
    requestsOutput += (
        "."
        + str("{:.7f}".format(receiveReq[0])).split(".")[1]
        + " [R"
        + str(receiveReq[1])
        + "] //"
        + str(receiveReq[2])
        + "\n"
    )
    times["receives"].append(
        {
            "time": float(receiveReq[0]),
            "bearer": int(receiveReq[1]),
            "code": int(receiveReq[2]),
            "offset": (setup["offsets"][setup["vpsNum"] - 1]),
        }
    )

requestsOutput = requestsOutput[:-1]  # trim whitespace off end

# response codes for snipe
responseCodes = tuple(
    map(lambda x: x[2], receivesReqs)
)  # create tuple of request response codes

# scan for specific codes, and log accordingly
if 200 in responseCodes:  # won the snipe
    success(receivesReqs[responseCodes.index(200)][3])
if 401 in responseCodes:  # bearer invalid
    send("[!] Unauthorized error(s)!")
if 500 in responseCodes:
    send("[!] Internal Server Error(s)!")
if 504 in responseCodes:
    send("[!] API timeout error(s)!")
# other vpses are posting delay webhooks too, so wait until it's the current VPS's turn to send
sleep(abs((setup["vpsNum"] - 1) * 0.6))  # wait out the gap
delayLogs(requestsOutput)  # log the delays

# finished!
print("Sniper has finished sniping. Wrapping up...")

# send send times and receive times to logging endpoint
requests.put(apiUrl + "/logging/times", auth=apiAuth, json=times)
