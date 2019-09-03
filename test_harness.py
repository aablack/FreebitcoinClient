import argparse
import twofagen
import logging

import fbclient

logger = logging.getLogger('root')
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='Username')
    parser.add_argument('-p', '--password', help='Password')
    parser.add_argument('-c', '--otc', help='Two factor auth one-time code')
    parser.add_argument('-s', '--otc_secret',
                        help='Two factor auth secret (base64 encoded). Can be provided instead of the one-time code')
    args = parser.parse_args()

    if args.otc_secret:
        otc = twofagen.gen_otc(args.otc_secret)
    else:
        otc = args.otc

    cli = fbclient.Client(verify_ssl=False)
    #cli.login(args.user, args.password, otc)
    print(f'Balance: {cli.get_balance()}')
    print(f'Rewards balance: {cli.get_rewards_balance()}')
    print(f'Roll timer: {cli.get_roll_timer()}')
    print(f'FreeBTC bonus timer: {cli.get_btc_bonus_timer()}')
    print(f'RP bonus timer: {cli.get_rp_bonus_timer()}')
    print(f'Lottery bonus timer: {cli.get_lottery_bonus_timer()}')

