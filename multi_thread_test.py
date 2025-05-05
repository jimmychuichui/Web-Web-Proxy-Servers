import threading
import requests
import time

# Number of concurrent threads
# Double of the number of threads we have in the web server so that we can see the difference between the batch 1 and 2
NUM_THREADS = 32

# URL to test
URL = 'http://localhost:8080/test.html'

def send_request(thread_id):
    print(f"Thread-{thread_id} starting request")
    start_time = time.time()
    try:
        response = requests.get(URL)
        end_time = time.time()
        print(f"Thread-{thread_id} received response: {response.status_code} in {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"Thread-{thread_id} encountered an error: {e}")

def main():
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=send_request, args=(i+1,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
