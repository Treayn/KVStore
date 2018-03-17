import asyncio
import pickle
import queue
import threading
from datetime import datetime

from aiohttp import web

class StorageThread(threading.Thread):
    def __init__(self, terminator, in_queue, need_data, out_queue, out_ready):
        # Multithreading primitives
        self._terminator = terminator
        self._in_queue = in_queue
        self._need_data = need_data
        self._out_queue = out_queue
        self._out_ready = out_ready
        
        self._dict = {}
        self._need_update = False
        self._load_data()

        self._last_recorded_time = datetime.now()
        self._current_time = datetime.now()

        super(StorageThread, self).__init__(
            group=None,
            target=None,
            name=None,
            args=(),
            kwargs=None
        )

    def _dump_data(self):
        pickle.dump(self._dict, open("name.db", "wb"))
        self._need_update = False
    
    def _load_data(self):
        # Check for prior value and initialize if needed.
        try:
            self._dict = pickle.load(open("name.db", "rb"))
        except (EOFError, IOError, OSError) as e:
            self._dict['name'] = "Default"
    
    def _return_data(self):
        self._need_data.clear()
        self._out_queue.put_nowait(self._dict['name'])
        self._out_ready.set()

    def _update_data(self):
        # Pop (most recent) name off stack.
        self._dict['name'] = self._in_queue.get_nowait()
        self._in_queue.task_done()
        self._need_update = True
        
        # Flush (older values from) stack.
        while not self._in_queue.empty():
            try:
                self._in_queue.get_nowait()
            except queue.Empty:
                continue

            self._in_queue.task_done()

    def run(self):
        while not self._terminator.is_set():
            self._current_time = datetime.now()
            
            if self._need_data.is_set():
                self._return_data()
            
            # Check for fresh data.
            if self._in_queue.qsize() > 0:
                self._update_data()
 
            # Write (new data) to disk every 5 seconds.
            if ((self._current_time - self._last_recorded_time).total_seconds() > 5) and self._need_update:
                self._dump_data()
                self._last_recorded_time = self._current_time
                print("Committed changes to disk")


class Store:
    def __init__(self):
        self._app = web.Application()
        self._loop = asyncio.get_event_loop()
        self._stop_thread = threading.Event()

        self._read_queue = queue.Queue()
        self._read_ready = threading.Event()
        self._want_read = threading.Event()
        self._write_stack = queue.LifoQueue()
        self.thread = StorageThread(
            self._stop_thread,
            self._write_stack,
            self._want_read,
            self._read_queue,
            self._read_ready
        )

        self._app.router.add_get('/data/name', self.get_name)
        self._app.router.add_put('/data/name', self.put_name)

        self.thread.start()
    
    # Public methods
    def start_app(self):
        # Blocking call.
        web.run_app(self._app)

        # Thread cleanup.
        self._stop_thread.set()
        self.thread.join()
    
    # Asynchronous methods
    async def get_name(self, request):
        # Ask thread for data.
        self._want_read.set()

        # Poll event until data is ready.
        while not self._read_ready.is_set():
            await asyncio.sleep(0.001)

        # Clear event, get data, & respond to client.
        self._read_ready.clear()
        res = self._read_queue.get_nowait()
        self._read_queue.task_done()
        return web.json_response({ "name": res })

    async def put_name(self, request):
        # Get data from REST API.
        data = await request.json()
        name = data['name']
        
        # Remove junk whitespace & store string if existent.
        if bool(name.strip()):
            self._write_stack.put_nowait(name)

        return web.Response(status=204)