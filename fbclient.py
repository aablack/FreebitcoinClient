import random
import logging
import re

from datetime import datetime
from datetime import timedelta
from collections import namedtuple
from collections import defaultdict

import requests

from urllib.parse import quote
from requests_html import HTMLSession

class RewardType:
    _RewardDefinition = namedtuple('RewardType', ['name', 'bonus_id'])

    Points = _RewardDefinition('Rewards Points Booster', 'free_points')
    Lottery = _RewardDefinition('Free Lottery Tickets', 'free_lott')
    FreeBTC = _RewardDefinition('Free BTC Booster', 'fp_bonus')


def check_login(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        self._logger.debug('Verifying login')
        html = self._get_main_page()

        if html.find('#balance', first=True):
            return func(*args, **kwargs)

        self._logger.error('You are not logged in')

    return wrapper


class Client:
    _URL = 'https://freebitco.in'

    def __init__(self, verify=True):
        self._logger = logging.getLogger('root.fbclient_direct')
        self._session = HTMLSession()
        self._session.verify = verify
        self._cache = defaultdict(lambda: (None, datetime.now(), 5))

    def login(self, username, password, otc=None):
        self._logger.info(f'Logging in, user: {username}')
        login_page = self._session.get(f'{self._URL}/?op=signup_page')

        csrf = login_page.cookies['csrf_token']
        self._session.headers['x-csrf-token'] = csrf

        data = (f'csrf_token={quote(csrf)}'
                f'&op=login_new'
                f'&btc_address={quote(username)}'
                f'&password={quote(password)}')

        if otc:
            data += f'&tfa_code={otc}'

        response = self._session.post(self._URL, data)
        result = response.text.split(':')

        if result[0] == 's':
            self._logger.info('Login success')
            self._session.cookies['btc_address'] = result[1]
            self._session.cookies['password'] = result[2]
            self._session.cookies['have_account'] = '1'
        elif result[0] == 'e':
            raise ValueError(f'Login failed: {result[1]}')
        else:
            raise ValueError(f'Login failed: {response}')

    @check_login
    def activate_rp_bonus(self, amount=100):
        return self._activate_bonus(RewardType.Points, amount)

    @check_login
    def activate_lottery_bonus(self, amount=100):
        return self._activate_bonus(RewardType.Lottery, amount)

    @check_login
    def activate_btc_bonus(self, amount=1000):
        return self._activate_bonus(RewardType.FreeBTC, amount)

    @check_login
    def roll(self, play_without_captcha=False):
        self._logger.info('Rolling')
        login_page = self._session.get(f'{self._URL}')

        data = (f'csrf_token={self._session.headers["x-csrf-token"]}'
                f"&op=free_play"
                f"&fingerprint=43b0ec50d04dfcf473f26b8fa7c8f72f"
                f"&client_seed={self._get_roll_seed()}"
                f"&fingerprint2=2592886125"
                f"&pwc={int(play_without_captcha)}"
                f"&89591411d5cf=1567309413%3A26e9b826a33e321aa27c09d235c158ff18de7f48ce850838ffe7f669cc30b436"
                f"&d4202f82cc23=1b208b3be22da3a07e58deb40fbecc0ef43b43b3216b8c2cc9ba7bc28646c21e")

        response = self._session.post(self._URL, data)
        result = response.text.split(':')

        if result[0] == 's':
            self._logger.info(f'Roll success, number: {result[1]}, win: {result[3]} BTC, balance: {result[2]} BTC')
            return True
        elif result[0] == 'e':
            self._logger.error(f'Roll failed: {result[1]}')
        else:
            self._logger.error(f'Roll failed: {response.text}')

        return False

    @check_login
    def get_roll_timer(self):
        self._logger.info('Retrieving roll timer')
        html = self._get_main_page()
        time_remaining_pattern = re.compile("\$\('#time_remaining'\).countdown\({until: \+(\d+)")
        match = time_remaining_pattern.search(html.html)

        if not match:
            self._logger.info('Timer not running')
            return 0

        countdown = match.group(1)
        self._logger.info(f'Timer value: {countdown}')
        return int(countdown)

    @check_login
    def get_balance(self):
        self._logger.info('Retrieving points balance')
        html = self._get_main_page()
        balance = html.find('#balance', first=True).text
        self._logger.info(f'Balance: {balance}')
        return float(balance.replace(',', ''))

    @check_login
    def get_rp_bonus_timer(self):
        return self._get_rewards_timer(RewardType.Points)

    @check_login
    def get_lottery_bonus_timer(self):
        return self._get_rewards_timer(RewardType.Lottery)

    @check_login
    def get_btc_bonus_timer(self):
        return self._get_rewards_timer(RewardType.FreeBTC)

    @check_login
    def get_rewards_balance(self):
        self._logger.info('Retrieving rewards balance')
        html = self._get_main_page()
        points = html.find('div.user_reward_points', first=True).text
        self._logger.info(f'Rewards points: {points}')
        return int(points.replace(',', ''))

    def _get_rewards_timer(self, reward_type):
        self._logger.info(f'Retrieving rewards timer: {reward_type.bonus_id}')
        html = self._get_main_page()
        bonus_pattern = re.compile(f'BonusEndCountdown\("{reward_type.bonus_id}",(\d+)\)')
        match = bonus_pattern.search(html.html)

        if not match:
            self._logger.info(f'Bonus timer: {reward_type.bonus_id} not running')
            return 0

        countdown = match.group(1)
        self._logger.info(f'Timer value: {countdown}')
        return int(countdown)

    def _get_main_page(self):
        html, expiry, cache_time = self._cache['html']

        if datetime.now() >= expiry:
            self._logger.debug('Downloading main page')
            html = self._session.get(f'{self._URL}/?op=home').html
            expiry = datetime.now() + timedelta(seconds=cache_time)
            self._cache['html'] = (html, expiry, cache_time)

        return html

    def _activate_bonus(self, reward_type, amount):
        self._logger.info('Activating: %s %d bonus' % (reward_type.name, amount))

        response = self._session.get(f'{self._URL}/'
                                     f'?op=redeem_rewards'
                                     f'&id={reward_type.bonus_id}_{amount}'
                                     f'&points='
                                     f'&csrf_token={self._session.headers["x-csrf-token"]}')

        result = response.text.split(':')

        if result[0] == 's':
            self._logger.info(f'Bonus activation successful')
            return True
        elif result[0] == 'e':
            self._logger.error(f'Roll failed: {result[1]}')
        else:
            self._logger.error(f'Roll failed: {response.text}')

        return False

    def _get_roll_seed(self, length=16):
        self._logger.info('Generating roll seed')
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890'
        seed = str.join('', (random.choice(chars) for i in range(length)))
        self._logger.debug('Seed: %s' % seed)
        return seed

