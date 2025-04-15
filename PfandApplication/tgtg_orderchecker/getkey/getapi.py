from tgtg import TgtgClient

client = TgtgClient(email="your email here")
creds = client.get_credentials()

print(creds)
