import twofagen
import argparse
import logging
import signal
import time
import threading

from logging import handlers

import fbclient
from timerthread import TimerThread


def exit_handler(signal, frame):
    logger.debug('Received signal to quit')
    stop_flag.set()
    [t.join(1) for t in threads if t.is_alive()]
    exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='Username')
    parser.add_argument('-p', '--password', help='Password')
    parser.add_argument('-c', '--otc', help='Two factor auth one-time code')
    parser.add_argument('-s', '--otc_secret',
                        help='Two factor auth secret (base64 encoded). Can be provided instead of the one-time code')
    parser.add_argument('-l', '--logpath', help='Log file path')
    parser.add_argument('-v', '--verbose', help='Debug logging', action='count', default=0)
    args = parser.parse_args()

    logger = logging.getLogger('root')

    if args.verbose == 0:
        logger.setLevel(logging.WARNING)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif args.verbose >= 2:
        logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if args.logpath:
        fileHandler = handlers.TimedRotatingFileHandler(args.logpath, 'D', 1, 365)
        fileHandler.setLevel(logger.level)
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)
    else:
        streamHandler = logging.StreamHandler()
        streamHandler.setLevel(logger.level)
        streamHandler.setFormatter(formatter)
        logger.addHandler(streamHandler)

    client = fbclient.Client()
    stop_flag = threading.Event()
    lock = threading.Lock()
    threads = []

    for sig_name in ('SIGABRT', 'SIGHUP', 'SIGILL', 'SIGINT', 'SIGSEGV', 'SIGTERM'):
        sig = getattr(signal, sig_name, None)
        if sig:
            signal.signal(sig, exit_handler)

    if args.otc_secret:
        otc = twofagen.gen_otc(args.otc_secret)
    else:
        otc = args.otc

    client.login(args.user, args.password, otc)

    def activate_btc_bonus():
        # Enforce 1200 RP buffer for activating rewards points bonus
        if (client.get_rewards_balance() or 0) >= 4400:
            client.activate_btc_bonus()
        else:
            logger.info('Not activating BTC bonus because rewards points balance is too low')

    threads.extend((
        TimerThread(lambda: client.activate_rp_bonus(), 86400, stop_flag, lock, client.get_rp_bonus_timer(), name='rewards_bonus_thread'),
        TimerThread(activate_btc_bonus, 86400, stop_flag, lock, client.get_btc_bonus_timer(), name='freebtc_bonus_thread'),
        TimerThread(lambda: client.roll(), 3600, stop_flag, lock, client.get_roll_timer(), name='roll_thread'),
    ))

    for t in threads:
        t.start()

    while not stop_flag.is_set():
        try:
            time.sleep(1)
        except:
            exit_handler(None, None)

