from flask import Flask, request, render_template

web = Flask('WEB')


@web.route('/')
def index():
    return render_template("index.html")

@web.route('/test')
def getTest():
    a1 = request.args.get("a1")
    a2 = request.args.get("a2")
    print(a1, a2)
    return 'Got Args'