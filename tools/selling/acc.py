#load in the template file
with open("template.txt") as input_file:
    output = input_file.read()

#prompt a user for a field
def prompt(msg):
    global output
    print("Enter the \""+msg+"\"")
    answer = input("> ")
    output = output.replace("{"+msg+"}",answer)
    print()
    return answer

# #all the different fields
items = ["name","email","password","ip","dob","gamertag","tid","recovery","created at"]

#get the ign seperatly, so that we have it to name the file with
ign = prompt("ign")
for item in items:
    prompt(item)

#output to a new file named after the ign
with open(ign+".txt","w") as output_file:
    output_file.write(output)

print("Finished.")