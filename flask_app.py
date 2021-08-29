from flask import Flask, request

app = Flask(__name__)


@app.route('/')
def hello():
    return 'Hello, Heroku!'


if __name__ == '__main__':
    app.run()  # 啟動伺服器
