import requests as rq
from bs4 import BeautifulSoup as bs
import re
import json
import os
import shutil
import sqlite3
import datetime
from pytube import YouTube

import matplotlib.pyplot as plt
import librosa
import librosa.display
import textgrid
import numpy as np
from pydub import AudioSegment

#save file from url
def save_file(dir_path,url,filr_neme):
    filename = os.path.join(dir_path,filr_neme)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    r=rq.get(url)
    with open(filename,"wb") as f:
        f.write(r.content)

def download_data_from_vlive(V_id): #isConn,video_P,vtt_language
    url='https://www.vlive.tv/video/'+V_id
    html_json,subject=getJSON(url)
    conn = sqlite3.connect("vlive.db")
    cur = conn.cursor()
    
    img_url=html_json["meta"]["cover"]["source"]
    # save_file(dir_path,image_url,"cover.jpg")

    exist=cur.execute("SELECT EXISTS (SELECT 1 \
                        FROM video_list \
                        WHERE id=?\
                        LIMIT 1)""", (V_id, )).fetchone()[0]
    if exist == 0:
        print("插入新row")
        cur.execute('insert into video_list(id, subject, img_url)\
                            values(?,?,?)',[V_id,subject,img_url])
    conn.commit()
    conn.close()

def crawl_video_url(url):
    html_json=getJSON(url)[0]
    video_url=""
    video_list=html_json["videos"]["list"]
    for v in video_list:
        if v["encodingOption"]["name"] == "720P":
            video_url=v["source"]
    return video_url

def get_vlive_search_all(query):
    cookies={'userLanguage':'zh_tw'}
    res=rq.get('https://www.vlive.tv/search/all?query='+query,cookies=cookies)
    soup=bs(res.text)

    data={}
    data['query']=query
    video_list=[]
    channel_list=[]

    if soup.find("ul", class_="channel_lst_area"):
        channel_lis=soup.find("ul", class_="channel_lst_area").find_all('li')
        for li in channel_lis:
            channel_info={}
            channel_info['channel_href']=li.find('a')['href']
            channel_info['data_ga_seq']=li.find('a')['data-ga-seq']
            channel_info['channel_name']=li.find('strong',class_='name').text
            channel_info['channel_icon_src']=li.find('img')['src']
            channel_list.append(channel_info)

    cookies={'userLanguage':'zh_tw'}
    res=rq.get('https://www.vlive.tv/search/videos?query='+query,cookies=cookies)
    soup=bs(res.text)
    if soup.find("ul", class_="video_list"):
        video_lis=soup.find("ul", class_="video_list").find_all('li')
        for li in video_lis:
            if li.find('a',class_='thumb_area'):
                video_info={}
                video_info['video_href']=li.find('a',class_='thumb_area')['href']
                video_info['img_src']=li.find('a',class_='thumb_area').find('img')['src']
                video_info['video_title']=li.find('a',class_='video_tit')['title']
                video_info['date']=li.find('span',class_='date').text
                video_info['channel_href']=li.find('div',class_='video_date').find('a')['href']
                video_info['channel_name']=li.find('div',class_='video_date').find('a').text
                video_info['data_ga_seq']=li.find('div',class_='video_date').find('a')['data-ga-seq']
                video_list.append(video_info)

        scriptString=str(soup.find_all("script", {"src":False}))
        pattern = re.compile('var sOffset = "(.*)"; var bLast = (.*);')
        info=re.findall(pattern, scriptString)[0]
        print(info)
        data['sOffset']=info[0]
        data['bLast']=info[1]
    data['query']=query
    data['video_list']=video_list
    data['channel_list']=channel_list
    return data

def get_vlive_search_videos(query):
    cookies={'userLanguage':'zh_tw'}
    res=rq.get('https://www.vlive.tv/search/videos?query='+query,cookies=cookies)
    soup=bs(res.text)
    video_lis=soup.find("ul", class_="video_list").find_all('li')
    channel_lis=[]
    data={}
    video_list=[]
    channel_list=[]
    for li in video_lis:
        video_info={}
        video_info['video_href']=li.find('a',class_='thumb_area')['href']
        video_info['img_src']=li.find('a',class_='thumb_area').find('img')['src']
        video_info['video_title']=li.find('a',class_='video_tit')['title']
        video_info['date']=li.find('span',class_='date').text
        video_info['channel_href']=li.find('div',class_='video_date').find('a')['href']
        video_info['channel_name']=li.find('div',class_='video_date').find('a').text
        video_list.append(video_info)

    # if soup.find("ul", class_="channel_lst_area"):
    #     channel_lis=soup.find("ul", class_="channel_lst_area").find_all('li')
    # for li in channel_lis:
    #     channel_info={}
    #     channel_info['channel_href']=li.find('a')['href']
    #     channel_info['data_ga_seq']=li.find('a')['data-ga-seq']
    #     channel_info['channel_name']=li.find('strong',class_='name').text
    #     channel_info['channel_icon_src']=li.find('img')['src']
    #     channel_list.append(channel_info)
    data['video_list']=video_list
    # data['channel_list']=channel_list

    scriptString=str(soup.find_all("script", {"src":False}))
    pattern = re.compile('var sOffset = "(.*)"; var bLast = (.*);')
    info=re.findall(pattern, scriptString)[0]
    print(info)
    data['sOffset']=info[0]
    data['bLast']=info[1]
    data['query']=query

    return data

def more_videos(pageNo,sOffset,query):
    #更多影片
    url='https://www.vlive.tv/search/videos/more?pageNo={}&searchOffset={}&query={}'.format(pageNo,sOffset,query)
    # print(url)
    res=rq.get(url)
    # print(res.text)
    soup=bs(res.text)
    lis=soup.find_all('li',class_="video_list_cont")

    data={}
    video_list=[]
    for li in lis:
        video_info={}
        if li.find('a',class_='thumb_area'):
            video_info['video_href']=li.find('a',class_='thumb_area')['href']
            video_info['img_src']=li.find('a',class_='thumb_area').find('img')['src']
            video_info['video_title']=li.find('a',class_='video_tit')['title']
            video_info['date']=li.find('span',class_='date').text
            video_info['channel_href']=li.find('div',class_='video_date').find('a')['href']
            video_info['channel_name']=li.find('div',class_='video_date').find('a').text
            video_list.append(video_info)

    data["video_list"]=video_list

    scriptString=str(soup.find_all("script", {"src":False}))
    pattern = re.compile('var sOffset = "(.*)"; var bLast = (.*);')
    info=re.findall(pattern, scriptString)[0]
    data['sOffset']=info[0]
    data['bLast']=info[1]

    return data
def get_vlive_channel(ch_id):
    res=rq.get('https://api-vfan.vlive.tv/vproxy/channelplus/getChannelVideoList?\
app_id=8c6cc7b45d2568fb668be6e05b6e5a3b&\
gcc=TW&locale=zh_tw&\
channelSeq='+ch_id+'&\
maxNumOfRows=30&\
pageNo=1')

    videoList=json.loads(res.text)['result']['videoList']

    video_list=[]
    for v in videoList:
        video_info={}
        video_info['video_title']=v['title']
        video_info['img_src']=v['thumbnail']
        video_info['play_time']=str(datetime.timedelta(seconds=v['playTime']))
        video_info['onAirStartAt']=v['onAirStartAt']
        video_info['channel_name']=v['representChannelName']
        video_info['videoSeq']=v['videoSeq']
        video_list.append(video_info)

    return {'video_list':video_list,'seq_num':ch_id}


def more_channels(pageNo,seq_num):
    res=rq.get('https://api-vfan.vlive.tv/vproxy/channelplus/getChannelVideoList?\
app_id=8c6cc7b45d2568fb668be6e05b6e5a3b&\
gcc=TW&locale=zh_tw&\
channelSeq='+seq_num+'&\
maxNumOfRows=30&\
pageNo='+pageNo)

    videoList=json.loads(res.text)['result']['videoList']

    video_list=[]
    for v in videoList:
        video_info={}
        video_info['video_title']=v['title']
        video_info['img_src']=v['thumbnail']
        video_info['play_time']=str(datetime.timedelta(seconds=v['playTime']))
        video_info['onAirStartAt']=v['onAirStartAt']
        video_info['channel_name']=v['representChannelName']
        video_info['videoSeq']=v['videoSeq']
        video_list.append(video_info)

    return {'video_list':video_list}

def connect_video(V_id,video_P,vtt_language):
    # get videoId
    url='https://www.vlive.tv/video/{}'.format(V_id)
    session=rq.Session()
    res=session.get(url)
    reg = r"window.__PRELOADED_STATE__=(.*?),function"
    spi = re.findall(reg, res.text)[0]

    # get inkey
    j=json.loads(spi)

    officialVideo=j["postDetail"]["post"]["officialVideo"]
    title=officialVideo['title']
    vodId=officialVideo['vodId']
    videoSeq=officialVideo['videoSeq']

    print(title)
    print(vodId)
    print(videoSeq)

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-TW,zh;q=0.9,en;q=0.8,ko;q=0.7,ja;q=0.6",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": "https://www.vlive.tv/video/{}".format(videoSeq),
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"
    }

    url="https://www.vlive.tv/globalv-web/vam-web/video/v1.0/vod/{}/inkey?appId=8c6cc7b45d2568fb668be6e05b6e5a3b&platformType=PC&gcc=TW&locale=zh_TW".format(videoSeq)
    res=session.get(url,headers=headers)
    inkey=json.loads(res.text)["inkey"]
    print(inkey)
    # inkey=json.loads(res.text)['inkey']
    
    # get json
    params={
        'key': inkey,
        'doct': 'json',
        'cpt': 'vtt',
        'videoId': vodId,
    }
    url='https://apis.naver.com/rmcnmv/rmcnmv/vod/play/v2.0/{}'.format(vodId)
    res=rq.get(url,params=params)
    vlive_json = json.loads(res.text)

    data={}
    if "captions" in vlive_json:
        for v in vlive_json["captions"]["list"]:
            if v['locale'] in vtt_language:
                vtt_language.remove(v['locale'])
                data[v['locale']]=v["source"]
                print('已下載{}.vtt'.format(v['locale']))
                # print(data[v['locale']])

    for v in vlive_json["videos"]["list"]:
        if v["encodingOption"]["name"] in video_P:
            data[v["encodingOption"]["name"]]=v["source"]
            print('已下載{}.mp4'.format(v["encodingOption"]["name"]))
            # print(data[v["encodingOption"]["name"]])

    data["subject"]=vlive_json["meta"]["subject"]
    data['V_id']=V_id
    data['img_url']=vlive_json["meta"]["cover"]["source"]

    return data

def save_youtu_caption(caption,code,convert=False):
    vtt=caption.generate_srt_captions().replace(',','.')
    if convert:
        vtt=Converter('zh-hant').convert(vtt)
    filename='static/download/youtuVideo/'+code+'.vtt'
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename,"w") as f:
        f.write('WEBVTT\n')
        f.write(vtt)




