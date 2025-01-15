import socket

def echo_client():
    # Menu of approved queries
    query_menu = {
        "1": "What is the average moisture inside my kitchen fridge in the past three hours?",
        "2": "What is the average water consumption per cycle in my smart dishwasher?",
        "3": "Which device consumed more electricity among my three IoT devices (two refrigerators and a dishwasher)?"
    }

    try:
        server_ip = input("Enter the server IP address: ")
        server_port = int(input("Enter the server port number: "))

        # IPv4 TCP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to the server
        client_socket.connect((server_ip, server_port))
        print(f"Connected to server at {server_ip}:{server_port}")

        while True:
            # Display the menu
            print("\nSelect a query:")
            for key, query in query_menu.items():
                print(f"{key}. {query}")
            print("Enter 'exit' to quit.")

            user_input = input("Enter your choice (1/2/3): ").strip()

            if user_input.lower() == 'exit':
                print("Exiting...")
                break

            if user_input in query_menu:
                # Send the numeric command to the server
                client_socket.sendall(user_input.encode())

                # Receive the reply from the server
                reply = client_socket.recv(1024)
                print(f"\nServer reply: {reply.decode()}")

            else:
                # Handle invalid input
                print("Invalid input. Please enter 1, 2, 3, or 'exit'.")

    # Handldle value and conections errors
    except ValueError:
        print("Error: Invalid input.")
    except ConnectionError:
        print("Error: Unable to connect to the server.")
        
    finally:
        client_socket.close()
        print("Connection closed.")


if __name__ == "__main__":
    echo_client()
