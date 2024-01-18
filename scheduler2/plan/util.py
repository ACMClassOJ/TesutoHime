from scheduler2.config import s3_buckets
from scheduler2.s3 import sign_url_get


class InvalidProblemException(Exception): pass
class InvalidCodeException(Exception): pass

url_scheme = 's3://'

def sign_url(url: str):
    if not url.startswith(url_scheme):
        raise InvalidProblemException(f'Invalid object url {url}')
    return sign_url_get(s3_buckets.problems, url.replace(url_scheme, '', 1))
