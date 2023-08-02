# Simple script for reformatting a bitwarden export json, into the format:
# email:password
# email:password (ext. In an accounts.txt file)

import json  # import json module for loading in jsons as dicts

with open("bitwarden.json") as bitwarden_import:  # open the bitwarden-formatted json
    bitwarden_json = json.loads(bitwarden_import.read())  # load it in

output_txt = ""  # the output string to write to accounts.txt

# for each item in the bitwarden dict
for item in bitwarden_json["items"]:

    # if the item isn't in a folder, it's an account
    if item["folderId"] == None:
        try:
            # add a line to the output_string with username:password
            # pulled from the bitwarden dict
            output_txt += item["name"] + ":" + item["login"]["password"] + "\n"
        except:
            # if the formatting is goffed, just pass
            pass

# write the output string to the accounts.txt
with open("accounts.txt", "w") as output_file:
    output_file.write(output_txt[:-1])  # cut off the very last/excess "\n"
