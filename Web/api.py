from flask import Flask, request


api = Flask('API')

@api.route('/')
def hello_b():
    return 'This is b'


