import argparse
import logging

import fbclient

logger = logging.getLogger('root')
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='Username')
    parser.add_argument('-p', '--password', help='Password')
    parser.add_argument('-c', '--twofactorauth', help='Two factor authentication code')
    args = parser.parse_args()

    cli = fbclient.Client()

    try:
        if cli.login(args.user, args.password, args.twofactorauth):
            print(cli.get_balance())
            print(cli.get_rewards_balance())
    finally:
        cli.close()

