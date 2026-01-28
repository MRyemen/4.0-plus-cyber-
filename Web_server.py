""""

Author:Dvir Zilber

Program name:Web_server.py

Description: A server that recives a client, recives an html request and sends back the correct file in the web root based on the command

"""


import socket
import os
import logging

# Constants
QUEUE_SIZE = 5
IP = '0.0.0.0'
PORT = 80
SOCKET_TIMEOUT = 2
WEB_ROOT = r'C:\cyber\cyberDemo\webroot\webroot'

# Mappings for Content-Type headers [cite: 17]
CONTENT_TYPES = {
    'html': 'text/html; charset=utf-8',
    'jpg': 'image/jpeg',
    'css': 'text/css',
    'js': 'text/javascript; charset=UTF-8',
    'txt': 'text/plain',
    'ico': 'image/x-icon',
    'gif': 'image/jpeg',
    'png': 'image/png'
}


def handle_calculate_next(client_socket, query_string):
    # we expect query_string to be like "num=(integer) "
    # we onky care about the value after the '='
    if 'num=' in query_string:
        # split by '=' and take the second part
        num_val = query_string.split('=')[1]

        # check if it's actually a number
        if num_val.isdigit():
            # calculate the next one
            next_num = str(int(num_val) + 1)

            # build the response
            header = "HTTP/1.1 200 OK\r\n"
            header += "Content-Type: text/plain\r\n"
            header += "Content-Length: " + str(len(next_num)) + "\r\n"
            header += "\r\n"

            client_socket.send(header.encode() + next_num.encode())
            logging.info("Sent next number: " + next_num)
        else:
            # it was "num=abc" or something else invalid
            client_socket.send("HTTP/1.1 400 BAD REQUEST\r\n\r\n".encode())
    else:
        # "num=" was not even in the string
        client_socket.send("HTTP/1.1 400 BAD REQUEST\r\n\r\n".encode())




def handle_calculate_area(client_socket, query_string):
    # we expect query_string like "height=3&width=4"
    h_val = None
    w_val = None

    # split by & to get the two separate parts
    parts = query_string.split('&')
    for p in parts:
        if 'height=' in p:
            h_val = p.split('=',1)[1]
        elif 'width=' in p:
            w_val = p.split('=',1)[1]

    # check if both were found and both are numbers
    if h_val != None  and w_val != None and h_val.isdigit() and w_val.isdigit():
        try:
            # calculate triangle area: (height * width) / 2
            # result must be a float (like 6.0) according to instructions
            area = (int(h_val) * int(w_val)) / 2.0
            result_str = str(area)

            # create the response
            header = "HTTP/1.1 200 OK\r\n"
            header += "Content-Type: text/plain\r\n"
            header += "Content-Length: " + str(len(result_str)) + "\r\n"
            header += "\r\n"

            client_socket.send(header.encode() + result_str.encode())
            logging.info("Area calculated: " + result_str)
        except:
            client_socket.send("HTTP/1.1 400 BAD REQUEST\r\n\r\n".encode())
            logging.error("there has accoured a problem with (send)")
    else:
        # if height or width are missing or not numbers, send 400
        client_socket.send("HTTP/1.1 400 BAD REQUEST\r\n\r\n".encode())
        logging.error("Area calculation failed: invalid parameters")




def handle_upload(client_socket, request_text, body_data, resource):
    # 1. Break the resource to find the filename
    filename = "unknown.bin"
    if '?' in resource:
        # Get everything after the '?'
        query_string = resource.split('?')[1]

        # Look for file-name= inside that query string
        if 'file-name=' in query_string:
            # Split and take the part after '=', then stop if there's an '&'
            filename = query_string.split('file-name=')[1].split('&')[0]

    # 2. Find Content-Length in the headers
    content_length = 0
    lines = request_text.split('\r\n')
    for line in lines:
        if 'Content-Length:' in line:
            content_length = int(line.split(':')[1].strip())
            break

    # 3. Ensure the whole body is read from the socket
    if len(body_data) < content_length:
        remaining_size = content_length - len(body_data)
        while remaining_size > 0:
            chunk = client_socket.recv(min(remaining_size, 4096))
            if not chunk:
                break
            body_data += chunk
            remaining_size -= len(chunk)

    # 4. Save the file
    file_path = 'uploads/' + filename
    try:
        with open(file_path, 'wb') as f:
            f.write(body_data)

        # 5. Send the success response
        response = "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
        client_socket.send(response.encode())
        logging.info("Uploaded file saved as: " + filename)

    except Exception as e:
        client_socket.send("HTTP/1.1 500 INTERNAL SERVER ERROR\r\n\r\n".encode())
        logging.error("Error saving file: " + str(e))





def handle_image(client_socket, query_string):
    # 1. Extract the filename from the URL
    filename = ""
    if 'image-name=' in query_string:
        # Split by '=', take the second part, and stop at '&' if it exists
        raw_name = query_string.split('image-name=')[1].split('&')[0]

        # Decode the name
        filename = unquote(raw_name)

    # 2. Build the fkll path to the file in the uploads folder
    file_path = os.path.join('uploads', filename)

    # 3. Check if the file actually exists before trying to open it
    if os.path.isfile(file_path):
        try:
            # Open in 'rb' (Read Binary)
            with open(file_path, 'rb') as f:
                image_data = f.read()

            # 4. Determine the Content-Type
            content_type = 'image/jpeg'
            if filename.endswith('.png'):
                content_type = 'image/png'

            # 5. Create the HTTP Header
            header = "HTTP/1.1 200 OK\r\n"
            header += f"Content-Type: {content_type}\r\n"
            header += f"Content-Length: {len(image_data)}\r\n"
            header += "\r\n"

            # 6. Send Header + Image Data
            client_socket.send(header.encode() + image_data)
            logging.info("Sent image: " + filename)

        except Exception as e:
            # If there was an error reading the file (e.g., permission issue)
            client_socket.send("HTTP/1.1 500 INTERNAL SERVER ERROR\r\n\r\n".encode())
            logging.error(f"Error sending image {filename}: {e}")
    else:
        # If the file doesn't exist in the uploads folder
        client_socket.send("HTTP/1.1 404 NOT FOUND\r\n\r\n".encode())
        logging.warning("Image not found: " + filename)







def get_file_data(file_path):
    """Reads file content in binary mode."""
    with open(file_path, 'rb') as f:
        return f.read()


def validate_http_request(header_text):
    try:
        # No need to decode here if handle_client already decoded it
        lines = header_text.split("\r\n")
        if len(lines) < 1:
            return False, None

        parts = lines[0].split(" ")
        if len(parts) != 3:
            return False, None

        method, resource, version = parts

        # ALLOW BOTH GET AND POST
        if (method == "GET" or method == "POST") and version == "HTTP/1.1":
            return True, resource

        return False, None
    except Exception:
        return False, None





def handle_client_request(resource, client_socket):
    """Generates and sends the HTTP response."""
    # Split the resource into path and query string
    if '?' in resource:
        path, query_string = resource.split('?', 1)
    else:
        path = resource
        query_string = ""

    # Route the request based on the path
    if path == '/calculate-next':
        handle_calculate_next(client_socket, query_string)

    elif path == '/calculate-area':
        handle_calculate_area(client_socket, query_string)

    elif path == '/image':
        handle_image(client_socket, query_string)

    else:
        serve_static_file(client_socket, path)


def serve_static_file(client_socket, resource):
    # 1. Handle special URIs
    if resource == '/':
        resource = '/index.html'
        logging.info(f"index is: {resource}")

    if resource == '/forbidden':
        client_socket.send("HTTP/1.1 403 FORBIDDEN\r\n\r\n".encode())
        logging.info(f"response is: {resource}")
        return
    if resource == '/moved':
        client_socket.send("HTTP/1.1 302 MOVED TEMPORARILY\r\nLocation: /\r\n\r\n".encode())
        logging.info(f"response is: {resource}")
        return
    if resource == '/error':
        client_socket.send("HTTP/1.1 500 INTERNAL SERVER ERROR\r\n\r\n".encode())
        logging.info(f"response is: {resource}")
        return
    else:
        resource = resource

    # 2. Check if file exists in WEB_ROOT
    file_path = os.path.join(WEB_ROOT, resource.lstrip('/'))
    if not os.path.isfile(file_path):
        client_socket.send("HTTP/1.1 404 NOT FOUND\r\n\r\n".encode())
        return

    # 3. Determine Content-Type
    file_extension = file_path.split('.')[-1].lower()
    content_type = CONTENT_TYPES.get(file_extension, 'application/octet-stream')

    # 4. Read data and build response [cite: 16, 18, 48]
    data = get_file_data(file_path)
    header = f"HTTP/1.1 200 OK\r\n"
    header += f"Content-Type: {content_type}\r\n"
    header += f"Content-Length: {len(data)}\r\n"
    header += "\r\n"

    client_socket.send(header.encode() + data)
    logging.info(f"file + headers were sent successfully: {header}")





def handle_client(client_socket):
    try:
        while True:
            # 1. Read the initial request (Headers + maybe some Body)
            data = client_socket.recv(2048)
            if not data:
                break

            # 2. Separate Headers and Body using the \r\n\r\n marker
            if b'\r\n\r\n' in data:
                header_part, body_part = data.split(b'\r\n\r\n', 1)
                header_text = header_part.decode()
            else:
                # If we didn't even get the full headers, this is a bad request
                break

            # 3. Validate the request (we use the first line of the header)
            is_valid, resource = validate_http_request(header_text)

            if is_valid:
                # Check if it's a POST request for upload
                if header_text.startswith('POST'):
                    # Call the upload handler with both the headers and the body we have
                    handle_upload(client_socket, header_text, body_part, resource)
                else:
                    # Regular GET requests
                    handle_client_request(resource, client_socket)
            else:
                client_socket.send("HTTP/1.1 400 BAD REQUEST\r\n\r\n".encode())
                break

    except Exception as e:
        print("Error handling client: " + str(e))
    finally:
        client_socket.close()






def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((IP, PORT))
        server_socket.listen(QUEUE_SIZE)
        print(f"Server listening on port {PORT}...")
        logging.info(f"Server listening on port {PORT}...")


        while True:
            client_socket, addr = server_socket.accept()
            # Remove the [cite: 40] from this line in your code
            client_socket.settimeout(SOCKET_TIMEOUT)
            handle_client(client_socket)
    except Exception as e:
        print(f"Server Error: {e}")
        logging.error(f"Server Error: {e}")
    finally:
        server_socket.close()




if __name__ == "__main__":
    """
    Configures the logging settings and starts the main server loop.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=
        [
            logging.FileHandler('logg_of_server'),
            # logging.StreamHandler() (only when there is a need to show the logs to the user)
        ]
    )
    main()




