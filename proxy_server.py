import socket
import threading
import sys
from urllib.parse import urlparse
import time

# Define buffer size
BUFFER_SIZE = 4096

# Define proxy server address and port
PROXY_HOST = 'localhost'
PROXY_PORT = 8888  # You can choose any available port

# Cache configuration
CACHE_SIZE = 100  # Maximum number of cached entries (optional)
CACHE_LOCK = threading.Lock() # Lock to protect the cache
cache = {}  # Cache storage

# Cache Time-To-Live (TTL) in seconds
CACHE_TTL = 300  # 5 minutes

def get_cache_key(method, url):
    return f"{method} {url}"

def get_older_cache_key():
    oldest_key = None
    oldest_timestamp = float('inf')
    for key, value in cache.items():
        if value['timestamp'] < oldest_timestamp:
            oldest_key = key
            oldest_timestamp = value['timestamp']
    return oldest_key

def add_to_cache(key, response, headers):
    with CACHE_LOCK:
        if key not in cache:
            if len(cache) >= CACHE_SIZE:
                # Eviction policy: remove the oldest cache entry
                oldest_key = get_older_cache_key()
                if oldest_key:
                    del cache[oldest_key]
        cache[key] = {
            'response': response,
            'headers': headers,
            'timestamp': time.time()
        }

def get_from_cache(key):
    with CACHE_LOCK:
        if key in cache:
            entry = cache[key]
            # Check if the cache entry has expired
            if (time.time() - entry['timestamp']) < CACHE_TTL:
                return entry
            else:
                # Cache entry expired
                del cache[key]
        return None
    

def parse_headers(response_bytes):
    try:
        header_end = response_bytes.index(b'\r\n\r\n') + 4
        headers = response_bytes[:header_end].decode(errors='ignore')
        body = response_bytes[header_end:]
        header_lines = headers.split('\r\n')
        header_dict = {}
        for line in header_lines[1:]:  # Skip the status line
            if ': ' in line:
                key, value = line.split(': ', 1)
                header_dict[key.lower()] = value
        return header_dict, body
    except Exception as e:
        print(f"Failed to parse headers: {e}")
        return {}, response_bytes

def handle_client(client_socket):
    try:
        # Receive client request
        request = b""
        while True:
            chunk = client_socket.recv(BUFFER_SIZE)
            if not chunk:
                break
            request += chunk
            if b'\r\n\r\n' in request:
                break
        if not request:
            client_socket.close()
            return
        request_str = request.decode(errors='ignore')
        print(f"Received request:\n{request_str}")

        # Parse HTTP request
        first_line = request_str.split('\n')[0]
        try:
            method, url, protocol = first_line.split()
        except ValueError:
            # Malformed request line
            response = f"HTTP/1.1 400 Bad Request\r\n\r\n"
            client_socket.sendall(response.encode())
            client_socket.close()
            return

        if method not in ['GET', 'HEAD']:
            # Send 501 Not Implemented
            response = f"{protocol} 501 Not Implemented\r\n\r\n"
            client_socket.sendall(response.encode())
            client_socket.close()
            return

        # Construct cache key
        cache_key = get_cache_key(method, url)
        cached_entry = get_from_cache(cache_key)
        headers_to_send = {}
        if cached_entry:
            # Extract ETag and Last-Modified from the cache if available
            cached_headers = cached_entry['headers']
            etag = cached_headers.get('etag')
            last_modified = cached_headers.get('last-modified')
            if etag or last_modified:
                headers_to_send = {}
                if etag:
                    headers_to_send['If-None-Match'] = etag
                if last_modified:
                    headers_to_send['If-Modified-Since'] = last_modified
                    print(f"Cache data last_modified: {last_modified}\n")

        # Parse the URL to get host and port
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port if parsed_url.port else 80
        path = parsed_url.path if parsed_url.path else '/'
        if parsed_url.query:
            path += '?' + parsed_url.query

        # Modify the request line to use the path instead of the full URL
        modified_request = f"{method} {path} {protocol}\r\n"

        # Reconstruct the headers, removing proxy-specific and conditional headers
        headers = ""
        for line in request_str.split('\n')[1:]:
            if line.strip() == '':
                break
            lower_line = line.lower()
            if not (lower_line.startswith('proxy-connection') or
                    lower_line.startswith('if-none-match') or
                    lower_line.startswith('if-modified-since')):
                headers += line + "\r\n"

        # Append necessary headers
        headers += f"Host: {host}\r\n"
        headers += "Connection: close\r\n"
        # Append conditional headers if any
        for header_key, header_value in headers_to_send.items():
            headers += f"{header_key}: {header_value}\r\n"
        headers += "\r\n"

        # Combine modified request
        full_request = modified_request + headers

        # Print the modified request
        print(f"Forwarding request to {host}:\n{full_request}")
        # Connect to the destination server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.connect((host, port))
            server_socket.sendall(full_request.encode())

            # Receive response from the destination server
            response = b""
            while True:
                data = server_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                response += data

        # Print response
        #print(f"Received response from {host}:\n{response.decode(errors='ignore')}")
        # Parse response headers
        response_headers, _ = parse_headers(response)
        response_headers, response_body = parse_headers(response)
        status_line = response.decode(errors='ignore').split('\r\n')[0]
        print(f"Received response from {host}: {status_line}")
        status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0

        if cached_entry and status_code == 304:
            # Not Modified: serve cached response
            print(f"Serving cached response for {url}")
            client_socket.sendall(cached_entry['response'])
        else:
            if status_code == 200:
                # Update cache with new response
                add_to_cache(cache_key, response, response_headers)
                #print(f"Cache key: {cache_key}")
            # Send the response back to the client
            print(f"Forwarding response to client for {url}")
            client_socket.sendall(response)

    except Exception as e:
        print(f"Error handling client: {e}")
        try:
            response = "HTTP/1.1 500 Internal Server Error\r\n\r\n"
            client_socket.sendall(response.encode())
        except:
            pass
    finally:
        client_socket.close()

def start_proxy():
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy_socket:
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        proxy_socket.bind((PROXY_HOST, PROXY_PORT))
        proxy_socket.listen(100)
        print(f"Proxy server listening on {PROXY_HOST}:{PROXY_PORT}...")

        while True:
            client_conn, client_addr = proxy_socket.accept()
            print(f"Accepted connection from {client_addr}")
            # Handle client connection in a new thread
            client_thread = threading.Thread(target=handle_client, args=(client_conn,))
            client_thread.daemon = True
            client_thread.start()

if __name__ == "__main__":
    try:
        start_proxy()
    except KeyboardInterrupt:
        print("\nProxy server shutting down.")
        sys.exit(0)
