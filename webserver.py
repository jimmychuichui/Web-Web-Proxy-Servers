import socket
import threading
import os
from datetime import datetime, timezone
import time
from queue import Queue
import random

# Define the host and port
HOST, PORT = 'localhost', 8080

# Configuration for multiple queues and thread pools
NUM_QUEUES = 10 # Number of queues
THREADS_PER_QUEUE = 64  # Number of threads per queue

# Create multiple queues
queues = [Queue() for _ in range(NUM_QUEUES)]

def handle_client(connection, address):
    thread_name = threading.current_thread().name
    try:
        request = connection.recv(1024).decode()
        print(f"[{thread_name}] Received request from {address}:\n{request}")
        
        # Parse HTTP request
        lines = request.splitlines()

        # Empty, not a valid HTTP request
        if len(lines) == 0:
            response = "HTTP/1.1 400 Bad Request\r\n\r\n"
            connection.sendall(response.encode())
            return

        request_line = lines[0]
        parts = request_line.split()

        # The first line have wrong amount of elements, not a valid HTTP request
        if len(parts) != 3:
            response = "HTTP/1.1 400 Bad Request\r\n\r\n"
            connection.sendall(response.encode())
            return

        # Extract method, path, and version from the request line
        method, path, version = parts

        # Only GET and HEAD methods are supported for now (ignore other methods such as POST)
        if method not in ['GET', 'HEAD']:
            response = "HTTP/1.1 501 Not Implemented\r\n\r\n"
            connection.sendall(response.encode())
            return

        # Remove leading '/'
        # Default to test.html if path is '/'
        if path == '/':
            path = '/test.html'
        file_path = '.' + path

        # Introduce artificial delay for /slow.html
        if path == '/slow.html':
            print("Simulating slow response...")
            time.sleep(5)  # Delay for 5 seconds

        # Check if file exists
        if not os.path.exists(file_path):
            response = "HTTP/1.1 404 Not Found\r\n\r\n"
            connection.sendall(response.encode())
            return

        # Handle If-Modified-Since header for 304 responses
        # Also handle 200 responses if there is no If-Modified-Since header
        last_modified = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(os.path.getmtime(file_path)))

        # Extract headers to get the time
        headers = {}
        for line in lines[1:]:
            # Check if the line contains a colon, indicating a header
            if ':' in line:
                # Split the line into header name and header value at the first colon
                header_name, header_value = line.split(':', 1)
                
                # Strip leading/trailing whitespace from both name and value
                header_name = header_name.strip()
                header_value = header_value.strip()
                
                # Add the header to the dictionary
                headers[header_name] = header_value

        if 'If-Modified-Since' in headers:
            ims = headers['If-Modified-Since']
            try:
                ims_time = time.mktime(time.strptime(ims, '%a, %d %b %Y %H:%M:%S GMT'))
                file_mtime = os.path.getmtime(file_path)
                print(f"[{thread_name}] File modified time: {file_mtime}, If-Modified-Since time: {ims_time}")
                if file_mtime <= ims_time:
                    response = f"HTTP/1.1 304 Not Modified\r\nLast-Modified: {last_modified}\r\n\r\n"
                    connection.sendall(response.encode())
                    print(f"[{thread_name}] File not modified since If-Modified-Since time, sending 304 response")
                    return
            except Exception as e:
                print(f"[{thread_name}] Error parsing If-Modified-Since header: {e}")
                # If parsing fails, proceed to send the file normally

        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()


        # Build response headers
        response_headers = [
            "HTTP/1.1 200 OK",
            f"Date: {datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}",
            f"Last-Modified: {last_modified}",
            f"Content-Length: {len(content)}",
            "Connection: close",
            "",
            ""
        ]
        response_headers = "\r\n".join(response_headers).encode()

        if method == 'HEAD':
            connection.sendall(response_headers)
        else:
            connection.sendall(response_headers + content)

    except Exception as e:
        print(f"[{thread_name}] Error handling request from {address}: {e}")
        response = "HTTP/1.1 500 Internal Server Error\r\n\r\n"
        try:
            connection.sendall(response.encode())
        except:
            pass
    finally:
        connection.close()

def worker(queue, worker_id):
    thread_name = threading.current_thread().name
    while True:
        connection, address = queue.get()
        if connection is None:
            # Sentinel to shut down the thread
            print(f"{thread_name} received shutdown signal.")
            break
        print(f"{thread_name} processing connection from {address}")
        handle_client(connection, address)
        queue.task_done()

def start_server():
    # Create worker threads for each queue
    threads = []
    for i, q in enumerate(queues):
        for j in range(THREADS_PER_QUEUE):
            t = threading.Thread(target=worker, args=(q, j+1), name=f"Queue-{i+1}-Worker-{j+1}")
            t.daemon = True
            t.start()
            threads.append(t)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(100)  # Increase backlog if expecting many connections
        print(f"Serving HTTP on {HOST} port {PORT} ...")
        while True:
            try:
                conn, addr = server_socket.accept()
                print(f"Accepted connection from {addr}")
                # Select a random queue to enqueue the connection
                selected_queue = random.choice(queues)
                selected_queue.put((conn, addr))


            except KeyboardInterrupt:
                print("\nServer shutting down.")
                break
            except Exception as e:
                print(f"Error accepting connections: {e}")


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        # Close all threads gracefully
        for q in queues:
            q.put((None, None))
        # Wait for all threads to finish
        for q in queues:
            q.join()
        exit(0)
