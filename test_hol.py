import threading
import requests
import time

# Define the server address
SERVER = 'http://localhost:8080'

# Configuration: Number of requests per endpoint
REQUEST_CONFIG = {
    '/slow.html': 640,  # Number of requests to /slow.html
    '/test.html': 640,  # Number of requests to /test.html
}

# Function to send a request and record the time
def send_request(path, results, index):
    #print(f"Sending request of {path}...")
    start_time = time.time()
    try:
        response = requests.get(f"{SERVER}{path}")
        end_time = time.time()
        results[index] = end_time - start_time
    except Exception as e:
        results[index] = None
        print(f"Request to {path} failed: {e}")

def main():
    # Build the list of requests based on the configuration
    start_time = time.time()
    requests_list = []
    for path, count in REQUEST_CONFIG.items():
        requests_list.extend([path] * count)
    
    num_requests = len(requests_list)
    threads = []
    results = [0] * num_requests

    print(f"Starting {num_requests} requests:")
    for path, count in REQUEST_CONFIG.items():
        print(f"  {count} requests to {path}")

    # Start all threads
    for i in range(num_requests):
        #sleep for 0.01 seconds between requests
        #time.sleep(0.01)
        path = requests_list[i]
        t = threading.Thread(target=send_request, args=(path, results, i))
        threads.append(t)
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

    
    end_time = time.time()
    print("\nResults:")
    time_slow = 0
    time_test = 0
    # Print the results
    for i in range(num_requests):
        path = requests_list[i]
        duration = results[i]
        if path == '/slow.html':
            time_slow += duration
        if path == '/test.html':
            time_test += duration
        if duration is not None:
            print(f"Request to {path} took {duration:.2f} seconds.")
        else:
            print(f"Request to {path} failed.")
    print(f"All requests completed in {end_time - start_time} seconds.")
    print(f"Average query time for /slow.html: {time_slow/640} seconds")
    print(f"Average query time for /test.html: {time_test/640} seconds")


if __name__ == "__main__":
    main()
