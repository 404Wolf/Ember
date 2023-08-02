from msauth import login
from time import sleep
import json


with open("accounts.txt") as accounts:
    accounts = accounts.read().split("\n")
    for email, password in map(lambda account: account.split(":"), accounts):
        try:
            loggedIn = login(email, password)
        except:
            continue
        print(loggedIn)
        with open("output.txt", "a") as output:
            output.write(json.dumps(loggedIn, indent=3) + "," + "\n")
        sleep(21)
