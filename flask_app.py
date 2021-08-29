from flask import Flask, render_template, request, redirect,\
    url_for, redirect
import os
import shutil
import json
from crawl_data import *
import sqlite3
import requests as rq
from langconv import Converter
from bs4 import BeautifulSoup as bs
from pytube import YouTube

import soundfile as sf
import librosa

dbfile = "vlive.db"

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.route("/", methods=['GET', 'POST'])
def index():
    return redirect(url_for('home'))


@app.route("/home", methods=['GET', 'POST'])
def home():
    return render_template('home.html')


@app.route("/video/<V_id>", methods=['GET', 'POST'])
def video(V_id):
    # url='https://www.vlive.tv/video/'+V_id
    data = connect_video(V_id,
                         video_P=["720P"],
                         vtt_language=["ko_KR", "zh_TW", "en_US"])
    data['video_url'] = data["720P"]
    data['crossorigin'] = 1
    with sqlite3.connect("vlive.db") as conn:
        cur = conn.cursor()
        exist = cur.execute("SELECT EXISTS (SELECT 1 \
                           FROM video_list \
                           WHERE id=?\
                           LIMIT 1)""", (V_id, )).fetchone()[0]
        if exist == 0:
            data['favorite'] = 0
        else:
            data['favorite'] = 1
    # print(data)
    return render_template("video.html", data=data)


@app.route("/video/youtu/<V_id>", methods=['GET', 'POST'])
def youtuVideo(V_id):
    data = {}
    url = 'https://www.youtube.com/watch?v='+V_id
    # url="https://www.youtube.com/watch?v=gdZLi9oWNZg"
    yt = YouTube(url)

    if os.path.exists("static/download/youtuVideo"):
        shutil.rmtree("static/download/youtuVideo")
    vtt_language = ["ko"]  # "en"
    code_list = []

    for v in yt.captions:
        code_list.append(v.code)
    print(code_list)

    data['zh_code'] = 'zh-TW'
    if 'zh-TW' in code_list:
        save_youtu_caption(yt.captions['zh-TW'], 'zh-TW', convert=False)
        data['zh_code'] = 'zh-TW'

    elif "zh" in code_list:
        save_youtu_caption(yt.captions['zh'], 'zh', convert=True)
        data['zh_code'] = 'zh'

    elif 'zh-CN' in code_list:
        save_youtu_caption(yt.captions['zh-CN'], 'zh-CN', convert=True)
        data['zh_code'] = 'zh-CN'

    vtt_language = list(set(vtt_language) & set(code_list))

    for code in vtt_language:
        save_youtu_caption(yt.captions[code], code, convert=False)

    print(yt.streams.filter(progressive="True")[-1].url)

    data['video_url'] = yt.streams.filter(progressive="True")[-1].url
    data['subject'] = yt.title
    data['img_url'] = yt.thumbnail_url
    data['zh_TW'] = "/static/download/youtuVideo/{}.vtt".format(
        data['zh_code'])
    data['en_US'] = "/static/download/youtuVideo/en.vtt"
    data['ko_KR'] = "/static/download/youtuVideo/ko.vtt"
    data['V_id'] = 'youtu/'+V_id
    data['crossorigin'] = 0

    with sqlite3.connect("vlive.db") as conn:
        cur = conn.cursor()
        exist = cur.execute("SELECT EXISTS (SELECT 1 \
                           FROM video_list \
                           WHERE id=?\
                           LIMIT 1)""", (data['V_id'], )).fetchone()[0]
        if exist == 0:
            data['favorite'] = 0
        else:
            data['favorite'] = 1

    return render_template("video.html", data=data)


@app.route("/load_video_list", methods=['GET', 'POST'])
def load_video_list():
    with sqlite3.connect('vlive.db') as conn:
        cur = conn.execute('select * from video_list\
                           WHERE NOT id=\'conn_online\';')
        return {"video_list": cur.fetchall()}


@app.route("/add_to_my_video", methods=['GET', 'POST'])
def download_data():
    V_id = request.form.get('V_id')
    subject = request.form.get('subject')
    img_url = request.form.get('img_url')

    conn = sqlite3.connect("vlive.db")
    cur = conn.cursor()

    exist = cur.execute("SELECT EXISTS (SELECT 1 \
                     FROM video_list \
                     WHERE id=?\
                     LIMIT 1)""", ('youtu/'+V_id, )).fetchone()[0]
    if exist == 0:
        print("插入新row")
        cur.execute('insert into video_list(id, subject, img_url)\
                           values(?,?,?)', [V_id, subject, img_url])
    conn.commit()
    conn.close()

    return "ok"


@app.route('/delete_my_video', methods=['GET', 'POST'])
def delete_video_block():
    V_id = request.form.get('V_id')
    print(V_id)
    with sqlite3.connect(dbfile) as conn:
        conn.execute('delete from video_list where id=?', (V_id,))
        # if os.path.exists("static/download/"+V_id):
        #     shutil.rmtree("static/download/"+V_id)
    return "ok"


@app.route("/search/all", methods=['GET', 'POST'])
def search_all():
    query = request.args.get('query')
    if 'https://www.youtube.com/watch' in query:
        spi = query.split('?')[1].split('&')[0].split('=')[1]
        return redirect(url_for('youtuVideo', V_id=spi))

    if 'https://www.vlive.tv/video' in query:
        # reg = r'https://www.vlive.tv/video/(.*?)\?'
        # spi = re.findall(reg, query)[0]
        spi = query.split('/')[4]
        return redirect(url_for('video', V_id=spi))

    data = get_vlive_search_all(query)
    return render_template("search_all.html", data=data)


@app.route("/search/more_videos", methods=['GET', 'POST'])
def get_vlive_web_more_videos():
    data = more_videos(request.form.get('pageNo'),
                       request.form.get('sOffset'),
                       request.form.get('query'))
    return data


@app.route("/channels/<ch_id>", methods=['GET', 'POST'])
def channels(ch_id):
    data = get_vlive_channel(ch_id)
    return render_template("channel.html", data=data)


@app.route("/channels/more", methods=['GET', 'POST'])
def get_vlive_web_more_channels():
    # print(request.form.get('pageNo'),request.form.get('seq_num'))
    data = more_channels(request.form.get('pageNo'),
                         request.form.get('seq_num'))
    return data


@app.route('/naver_api', methods=['GET', 'POST'])
def call_naver_api():
    query = request.form.get('query')
    print(query)
    try:
        res = rq.get('https://tip.dict.naver.com/datajsonp/ko/zh/pc/arken?prCode=dict&entryName=' +
                     query, verify=False, timeout=5)
    except:
        print('timeout')
        return {'data': 'timeout'}
    data = Converter('zh-hant').convert(res.text)
    return data


if __name__ == "__main__":
    app.run(debug=True,
            # host='0.0.0.0',
            # port=10914,
            )
    app.jinja_env.auto_reload = True
