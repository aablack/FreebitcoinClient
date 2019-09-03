import logging
import threading
import typing


class TimerThread(threading.Thread):
    def __init__(self,
                 fn: typing.Callable,
                 interval: float,
                 event: threading.Event,
                 lock: threading.Lock,
                 start_delay: int = 0,
                 lock_timeout: int = 60,
                 name: str = 'timerthread'):
        super().__init__()
        self._fn = fn
        self._interval = interval
        self._stopped = event
        self._lock = lock
        self._start_delay = start_delay
        self._lock_timeout = lock_timeout
        self._logger = logging.getLogger(f'root.{name}')

    def _execute(self):
        self._logger.debug('Acquiring lock')
        if self._lock.acquire(timeout=self._lock_timeout):
            self._logger.debug('Lock acquired')
            try:
                self._logger.info('Executing action')
                self._fn()
                self._logger.info('Execution completed')
            except:
                self._logger.exception('Error')
                raise
            finally:
                self._logger.debug('Releasing lock')
                self._lock.release()
        else:
            self._logger.error(f'Could not acquire lock after: {self._lock_timeout} seconds. Will retry next time.')

    def run(self):
        if self._start_delay:
            self._logger.info(f'Waiting out initial start delay: {self._start_delay} seconds')

        if not self._stopped.wait(self._start_delay):
            self._execute()

        self._logger.info(f'Waiting: {self._interval} seconds')
        while not self._stopped.wait(self._interval):
            self._logger.info('Timer expired')
            self._execute()
            self._logger.info(f'Waiting: {self._interval} seconds')

        self._logger.info('Stop flag has been set by main thread. Exiting')

