# KVStore
## Background
Basic Key/Value store.

HTTP requests/responses are handled by aiohttp,
  which buffers PUT requests into a stack.

A separate thread handles the updating of data periodically & data retrieval.
  The thread retrieves the top (most recent) data off the stack, & discards the rest.

The thread also writes the most recent change to disk every 5 seconds or so.
  File/Data persistence are handled by pickle.

When data needs to be retrieved, the event loop sends a signal (want_read) to the thread,
  which pushes the requested data onto the queue, and emits a return signal (read_ready)
  which the event loop polls for.

## To Install
(This project requires Python 3.5+)
0. Install virtualenv if you haven't already:
```
sudo apt install python3-venv
```

1. Navigate to a parent directory.

2. Create a virtual environment & activate it (Called KVStore in this case):
```
python3 -m venv KVStore
cd KVStore/
source bin/activate
```

3. Clone this repository & install requirements:
```
git clone https://github.com/Treayn/KVStore.git
pip install -r requirements.txt
```

## To Run
1. Run python script:
```
python scripts/main.py
```

2. Perform CRUD operations:
```
# To put:
curl -H 'Content-Type: application/json' -X PUT -d '{"name": "Gideon"}' localhost:8080/data/name
(Edit name field as needed.)

# To get:
curl localhost:8080/data/name
```

3. Ctrl-C to close.
