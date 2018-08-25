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
        self._logger = logging.getLogger('root.%s' % name)

    def _execute(self):
        self._logger.debug('Acquiring lock')
        if self._lock.acquire(timeout=self._lock_timeout):
            self._logger.debug('Lock acquired')
            try:
                self._logger.debug('Executing action')
                self._fn()
                self._logger.debug('Execution completed')
            except:
                self._logger.exception('Error')
                raise
            finally:
                self._logger.debug('Releasing lock')
                self._lock.release()
        else:
            self._logger.error('Could not acquire lock after: %d seconds. ' +
                               'Aborting action this time around' % self._lock_timeout)

    def run(self):
        if self._start_delay:
            self._logger.debug('Waiting out initial start delay: %d seconds' % self._start_delay)

        if not self._stopped.wait(self._start_delay):
            self._execute()

        self._logger.debug('Waiting: %d seconds' % self._interval)
        while not self._stopped.wait(self._interval):
            self._logger.debug('Timer expired')
            self._execute()
            self._logger.debug('Waiting: %d seconds' % self._interval)

        self._logger.debug('Stop flag has been set by main thread. Exiting')
