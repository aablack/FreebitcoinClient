import argparse
import pyotp


def gen_otc(secret):
    otc = pyotp.TOTP(secret)
    return otc.now()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--secret', help='base64 encoded 2FA secret')

    args = parser.parse_args()
    print(gen_otc(args.secret))
