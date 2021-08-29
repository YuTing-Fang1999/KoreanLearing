from flask import Flask, request

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def hello():
    return 'Hello, Heroku!'


if __name__ == '__main__':
    app.run()  # 啟動伺服器
