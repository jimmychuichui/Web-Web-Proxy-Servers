# 🖥️ Minimal Web & Proxy Server (MP1 Project)

This project implements a **multithreaded HTTP server** and **proxy server** in Python. It supports various HTTP response codes and simulates realistic performance optimizations like caching and Head-Of-Line (HOL) blocking mitigation.



## 📌 Features

### ✅ Web Server
- Parses and serves HTTP requests on `localhost:8080`
- Supports `GET` and `HEAD` methods
- Returns correct HTTP response codes:
  - `200 OK`
  - `304 Not Modified`
  - `400 Bad Request`
  - `404 Not Found`
  - `500 Internal Server Error`
  - `501 Not Implemented`
- Multi-threaded request handling

### 🔁 Proxy Server
- Forwards requests to origin server
- Caches responses with support for `If-Modified-Since`
- Returns cached content if data is unmodified
- Optimizes bandwidth and reduces latency

### 🧪 Status Code Testing

| Status Code | Trigger Condition |
|-------------|------------------|
| `400`       | Malformed or empty request |
| `501`       | Unsupported HTTP method (e.g., `POST`) |
| `404`       | Requested file not found |
| `304`       | `If-Modified-Since` provided and file unchanged |
| `200`       | Valid `GET` or `HEAD` request |
| `500`       | Unexpected internal error |


## 📁 File Structure

├── webserver.py # Main multithreaded web server<br/>
├── proxy_server.py # Proxy server with caching logic<br/>
├── multi_thread_test.py # Stress test script for threading performance<br/>
├── test_hol.py # HOL blocking simulation script<br/>
├── test.html # Example static file (fast response)<br/>
├── slow.html # Example static file (simulates delay)

## ⚙️ How It Works

### 🧵 Multithreading
- Each request is handled in its own thread
- Reduces blocking and improves throughput
- Performance test shows `4x` speedup vs. single-threaded

### 🚦 HOL Blocking Mitigation
- Without mitigation: fast requests (like `test.html`) blocked by slow ones (`slow.html`)
- With mitigation:
  - Requests randomly assigned to one of `N` queues
  - Each queue has its own thread pool
  - Greatly improves fairness and latency



## 🧪 Testing Scenarios

- Run server: `python server.py`
- Test via browser, `telnet`, or Python script
- Example tests:
  ```bash
  # 400 Bad Request
  echo "asdfasdf" | nc localhost 8080

  # 501 Not Implemented
  echo -e "POST / HTTP/1.1\r\n\r\n" | nc localhost 8080

  # 404 Not Found
  curl http://localhost:8080/notfound.html

  # 304 Not Modified
  curl -H "If-Modified-Since: Wed, 21 Oct 2025 07:28:00 GMT" http://localhost:8080/test.html

  # 200 OK
  curl http://localhost:8080/test.html

## 📊 Performance Results
| Threads          | Requests  | Avg Completion Time   | Avg Query Time (test.html|
| ---------------- | --------- | --------------------- |----------------|
| 1                | 4 slow    | 20s                   | N/A            |
| 4                | 4 slow    | 5s                    | N/A            |           
| 640 (no HOL fix) | 640 mixed | 5.39s                 | 4.53s          |
| 640 (HOL fixed)  | 640 mixed | 10.08s                | 2.59s          |




