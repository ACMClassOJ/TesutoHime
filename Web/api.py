from flask import Flask, request


api = Flask('API')

@api.route('/')
def hello_b():
    testM.test()
    return 'This is b'
