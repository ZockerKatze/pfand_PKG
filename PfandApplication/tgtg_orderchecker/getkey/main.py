import json

from tgtg import TgtgClient


def get_tgtg_credentials():
    email = input("Enter your TGTG account email: ")

    try:
        client = TgtgClient(email=email)
        credentials = client.get_credentials()

        # Save credentials to a JSON file
        with open("tgtg_credentials.json", "w") as json_file:
            json.dump(credentials, json_file, indent=4)

        # Print credentials in a readable format
        print("\nYour TGTG API Credentials:")
        print(json.dumps(credentials, indent=4))

        print("\nCredentials have been saved to 'tgtg_credentials.json'.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    get_tgtg_credentials()
