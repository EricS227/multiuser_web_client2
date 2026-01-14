"""
Test the API endpoints to see what data is being returned
"""
import requests

# First login to get token (OAuth2PasswordRequestForm format)
login_data = {
    "username": "admin@test.com",
    "password": "admin123"
}

response = requests.post("http://localhost:8000/login", data=login_data)
print("Login status:", response.status_code)

if response.status_code == 200:
    token_data = response.json()
    token = token_data.get("access_token")
    print("Token obtained:", token[:50] + "...")

    # Test conversations endpoint
    headers = {"Authorization": f"Bearer {token}"}

    print("\n" + "="*60)
    print("TESTING /conversations ENDPOINT")
    print("="*60)
    conv_response = requests.get("http://localhost:8000/conversations", headers=headers)
    print("Status:", conv_response.status_code)
    if conv_response.status_code == 200:
        conversations = conv_response.json()
        print(f"Found {len(conversations)} conversations:")
        for conv in conversations:
            print(f"  ID: {conv['id']}, Number: {conv.get('customer_number')}, Name: {conv.get('name')}, Status: {conv.get('status')}")
    else:
        print("Error:", conv_response.text)

    print("\n" + "="*60)
    print("TESTING /my-conversations ENDPOINT")
    print("="*60)
    my_conv_response = requests.get("http://localhost:8000/my-conversations", headers=headers)
    print("Status:", my_conv_response.status_code)
    if my_conv_response.status_code == 200:
        my_conversations = my_conv_response.json()
        print(f"Found {len(my_conversations)} my conversations:")
        for conv in my_conversations:
            print(f"  ID: {conv['id']}, Number: {conv.get('customer_number')}, Name: {conv.get('name')}, Status: {conv.get('status')}, Assigned: {conv.get('assigned_to')}")
    else:
        print("Error:", my_conv_response.text)

    # Test messages for conversation 4
    print("\n" + "="*60)
    print("TESTING MESSAGES FOR CONVERSATION 4")
    print("="*60)
    msg_response = requests.get("http://localhost:8000/conversations/4/messages", headers=headers)
    print("Status:", msg_response.status_code)
    if msg_response.status_code == 200:
        messages = msg_response.json()
        print(f"Found {len(messages)} messages:")
        for msg in messages:
            print(f"  ID: {msg['id']}, Sender: {msg.get('sender')}, Type: {msg.get('message_type')}, Content: {msg.get('content')[:50]}...")
    else:
        print("Error:", msg_response.text)
else:
    print("Login failed:", response.text)
