import requests
import stem.process
import concurrent.futures
import random
import re
import json
from datetime import datetime
import settings


NUMBER_TO_MONTH = {'1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', '5': 'May', '6': 'Jun',
                   '7': 'Jul', '8': 'Aug', '9': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'}
MONTH_TO_NUMBER = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                   'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

# 2000-03-27
yt_date_pattern = re.compile(r'([0-9]*)-0?([0-9]*)-0?([0-9]*)')
# 2000-12-27T12:30:59Z
tw_date_pattern = re.compile(r'([0-9]*)-0?([0-9]*)-0?([0-9]*)T(0|[0-9]*)[^:]*:(0|[0-9]*)[^:]*:(0|[0-9]*)')


def launch_tor(seconds=12):
    while True:
        try:
            tor = stem.process.launch_tor_with_config(
                config={'SocksPort': settings.SOCKS_PORT, 'ControlPort': settings.CONTROL_PORT},
                tor_cmd=settings.TOR_PATH, timeout=seconds)
        except Exception as e:
            print(e)
        else:
            print('Tor launched.\n...')
            return tor


def new_session(tor=False, cookies={}):
    s = requests.Session()
    s.headers = settings.HEADER

    s.cookies = requests.cookies.RequestsCookieJar()
    for c_name, c_value in cookies.items():
        s.cookies.set(c_name, c_value)
    if tor:
        creds = str(random.randint(1, 100_000_000)) + ":" + "foo"
        s.proxies = {'http': f'socks5h://{creds}@localhost:{settings.SOCKS_PORT}',
                     'https': f'socks5h://{creds}@localhost:{settings.SOCKS_PORT}'}
    return s


def scrape(url, session=requests, timeout=10):
    try:
        r = session.get(url, timeout=timeout)
    except:  # requests.exceptions.Timeout
        return None
    return r


# Concurrently scrapes URLs until every result is appropriate.
def scrape_concurrently(urls: (), tor=False, page_check=None, cookies={}, new_s=15, timeout=10):
    urls = {i: url for i, url in enumerate(urls)}
    results = {}

    while urls:
        with concurrent.futures.ThreadPoolExecutor() as ex:
            i = 0
            for k, url in urls.items():
                if i % new_s == 0:
                    session = new_session(tor, cookies)
                i += 1
                results[k] = ex.submit(scrape, url, session, timeout)

        for k in urls.copy():
            result = results[k].result()
            if result:  # if request is successful
                if page_check is not None:
                    if page_check(result.text):  # if page returns 'page_check-ed' source code
                        results[k] = result
                        del urls[k]
                else:
                    results[k] = result
                    del urls[k]
    return [result for result in dict(sorted(results.items())).values()]


def dates_format(date: str, pattern):  # pattern must be YEAR_MONTH_DAY...
    date = pattern.findall(date)[0]
    frmt_date = NUMBER_TO_MONTH[date[1]] + ' ' + date[2] + ' ' + date[0]
    datetime_date = datetime(*[int(i) for i in date])
    return frmt_date, datetime_date


def duration_format(seconds):
    seconds = int(seconds)

    hs = int(seconds / 3600)
    ms = str(int(seconds % 3600 / 60))
    ss = str(seconds % 3600 % 60)

    hs = str(hs) + ':' if hs else ''
    ms = '0' + ms + ':' if hs and len(ms) == 1 else ms + ':'
    ss = '0' + ss if len(ss) == 1 else ss
    return hs + ms + ss


def video_yt(html_text) -> {}:  # Doesn't account for short-type URLs. Yet to start premieres haven't been tested.
    name = re.compile(r'"name": "([^"]*)"').findall(html_text)[0]
    channel_id = re.compile(r'"channelId":"([^"]*)"').findall(html_text)[0]
    channel_url = settings.YT_CHANNEL_FRONTEND + '/channel/' + channel_id

    vid_id = re.compile(r'<link rel="canonical" href="[^"]*(.{11})"').findall(html_text)[0]
    url = settings.YT_VID_FRONTEND + '/watch?v=' + vid_id
    thumbnail = 'https://i1.ytimg.com/vi/' + vid_id + '/mqdefault.jpg'

    title_index = html_text.index('"og:title" content="') + 20
    title = html_text[title_index: html_text.index('">', title_index)]

    frmt_date = re.compile(r'"publishDate":"([^"]*)"').findall(html_text)[0]
    frmt_date, date = dates_format(frmt_date, yt_date_pattern)

    duration_and_views = {}
    if '{"isLiveNow":true' not in html_text:  # if not a livestream or an ongoing premiere
        frmt_duration = duration_format(re.compile(r'"lengthSeconds":"([0-9]*)"').findall(html_text)[0])
        duration_and_views['frmt_duration'] = frmt_duration

        frmt_views = re.compile(r'"views":\{"simpleText":"([^ ]*) views"}').findall(html_text)
        if frmt_views:
            frmt_views = frmt_views[0].replace(',', '.')
            duration_and_views['frmt_views'] = frmt_views

    data = {'name': name, 'channel_id': channel_id, 'channel_url': channel_url, 'url': url,
            'thumbnail': thumbnail, 'title': title, 'frmt_date': frmt_date, 'date': date}
    data.update(duration_and_views)
    return data


def recommendations(html_text) -> []:
    datas = []

    section_start = '{"compactVideoRenderer":'
    section_index = 0
    for _ in range(html_text.count(section_start)):
        section_index = html_text.index(section_start, section_index) + len(section_start)

        name_index = html_text.index('"text":"', section_index) + 8
        name = html_text[name_index: html_text.index('","', name_index)]

        channel_id_index = html_text.index('"browseId":"', section_index) + 12
        channel_id = html_text[channel_id_index: html_text.index('"', channel_id_index)]
        channel_url = settings.YT_CHANNEL_FRONTEND + '/channel/' + channel_id

        vid_id_index = html_text.index('"videoId":"', section_index) + 11
        vid_id = html_text[vid_id_index: html_text.index('"', vid_id_index)]
        url = settings.YT_VID_FRONTEND + '/watch?v=' + vid_id

        thumbnail = 'https://i1.ytimg.com/vi/' + vid_id + '/mqdefault.jpg'

        title_index = html_text.index('"simpleText":"', section_index) + 14
        title = html_text[title_index: html_text.index('"}', title_index)]

        data = {'name': name, 'channel_url': channel_url, 'url': url,
                'thumbnail': thumbnail, 'title': title, 'channel_id': channel_id}
        try:
            date_index = html_text.index('"publishedTimeText":{"simpleText":"', section_index) + 35
            frmt_date = html_text[date_index: html_text.index('"', date_index)]
            data['frmt_date'] = frmt_date
        except:
            pass
        try:
            duration_index = html_text.index('"lengthText":', section_index) + 13
            duration_index = html_text.index('"simpleText":"', duration_index) + 14
            frmt_duration = html_text[duration_index: html_text.index('"', duration_index)]
            data['frmt_duration'] = frmt_duration
        except:
            pass
        try:
            views_index = html_text.index('"viewCountText":{"simpleText":"', section_index) + 31
            frmt_views = html_text[views_index: html_text.index(' ', views_index)].replace(',', '.')
            data['frmt_views'] = frmt_views
        except:
            pass
        datas.append(data)
    return datas


def stream_tw(html_text) -> {}:
    if '"isLiveBroadcast":true' not in html_text:
        return {}
    name = re.compile(r'(?<="twitch\.tv/)([^/"]*)[/"]').findall(html_text)[0]
    url = 'https://twitch.tv/' + name

    section = json.loads(re.search(r'\{"@type":"VideoObject".*"isLiveBroadcast":true}}', html_text).group())
    thumbnail = section['thumbnailUrl'][1]

    title = section['description']

    frmt_date = dates_format(section['uploadDate'], tw_date_pattern)[0]
    date = datetime.now()

    return {'name': name, 'channel_url': url, 'url': url, 'thumbnail': thumbnail,
            'title': title, 'frmt_date': frmt_date, 'date': date}


def past_videos_tw(html_text, vid_count=5) -> []:
    datas = []

    videos = re.search(r'\{"@type":"ItemList".*=meta.tag"}]}', html_text)
    if not videos:
        return []
    name = re.compile(r'(?<="twitch\.tv/)([^/"]*)[/"]').findall(html_text)[0]
    channel_url = 'https://twitch.tv/' + name

    container = json.loads(videos.group())

    for video in range(min(videos.group().count('"@type":"VideoObject"'), vid_count)):
        url = container['itemListElement'][video]['url']
        if 'clips' not in url:
            thumbnail = container['itemListElement'][video]['thumbnailUrl'][2]

            title = container['itemListElement'][video]['name']

            frmt_date, date = dates_format(container['itemListElement'][video]['uploadDate'], tw_date_pattern)

            frmt_duration = duration_format(container['itemListElement'][video]['duration'][2:-1])

            views = int(container['itemListElement'][video]['interactionStatistic']['userInteractionCount'])
            frmt_views = str('{:,}'.format(views)).replace(',', '.')

            data = {'name': name, 'channel_url': channel_url, 'url': url, 'thumbnail': thumbnail, 'title': title,
                    'frmt_date': frmt_date, 'date': date, 'frmt_duration': frmt_duration, 'frmt_views': frmt_views}
            datas.append(data)
    return datas


def videos_bt(html_text, vid_count=5) -> []:
    datas = []

    name = re.compile(r'<title>(.*)</title>\n').findall(html_text)[0]
    channel_url = re.compile(r'rel="canonical" href="([^"]*)"').findall(html_text)[0]

    section_start = '<div class="channel-videos-container">'
    section_index = 0
    for video in range(min(html_text.count(section_start), vid_count)):
        section_index = html_text.index(section_start, section_index) + 1

        vid_id_index = html_text.index('<a href="/video/', section_index) + 16
        vid_id = html_text[vid_id_index: html_text.index('/" class="spa">', vid_id_index)]
        url = 'https://bitchute.com/video/' + vid_id

        thumbnail = re.compile(r'(?<=' + section_start + r')*<img class=".*data-src="(.*)_640x360\.jpg') \
            .findall(html_text)[video] + '_320x180.jpg'

        title = re.compile(r'(?<=' + section_start + r')*class="channel-videos-title">[^>]*>(.*)</a>\n') \
            .findall(html_text)[video]

        frmt_date = re.compile(r'(?<=' + section_start + r')*<div class="channel-videos-text-container'
                               r'">\n.*\n<span>(.*)<').findall(html_text)[video].replace(',', '')
        date = re.compile(r'([a-zA-Z]{3})[^0-9]*0?([0-9]*)[^0-9]*([0-9]*)').findall(frmt_date)[0]
        date = datetime(int(date[2]), MONTH_TO_NUMBER[date[0]], int(date[1]))

        frmt_duration = re.compile(r'(?<=' + section_start + r')*class="video-duration">(.*)<') \
            .findall(html_text)[video]

        frmt_views = re.compile(r'(?<=' + section_start + r')*<i class="far fa-eye"></i> (.*)<') \
            .findall(html_text)[video]

        data = {'name': name, 'channel_url': channel_url, 'url': url, 'thumbnail': thumbnail, 'title': title,
                'frmt_date': frmt_date, 'date': date, 'frmt_duration': frmt_duration, 'frmt_views': frmt_views}
        datas.append(data)
    return datas


# YouTube:
# /channel name
# /user/channel name
# /channel/channel id
# /channel/@channel alias

# Twitch:
# /channel name

# BitChute:
# /channel name
# /channel/channel name
# /channel/channel id
# /video/channel id
# /video/channel name ?
def find_channel_urls(urls: ""):
    yt_pattern = re.compile(r'youtube\.com/channel/UC[a-zA-Z0-9_-]{22}|youtube\.com/user/[a-zA-Z0-9_]+|'
                            r'youtube\.com/@?[^@\n-./\\#<>?^]+')
    tw_pattern = re.compile(r'twitch\.tv/[a-zA-Z0-9_]+')
    bc_pattern = re.compile(r'bitchute\.com/channel/[a-zA-Z0-9_]+|bitchute\.com/[a-zA-Z0-9_]+')

    yt_urls = ['https://' + url + '/videos' for url in yt_pattern.findall(urls)]
    bc_urls = ['https://' + url for url in bc_pattern.findall(urls)]
    tw_live_urls = ['https://' + url for url in tw_pattern.findall(urls)]
    tw_vods_urls = ['https://' + url + '/videos?filter=archives&sort=time' for url in tw_pattern.findall(urls)]
    return yt_urls, tw_live_urls, tw_vods_urls, bc_urls


def urls_of_uploads(html_text, vid_count=5):  # Gets the URLs of a Youtube channel's recent uploads.
    section_start = 'Renderer":{"videoId":"'
    urls = []
    for video in range(min(html_text.count(section_start), vid_count)):
        vid_id = re.compile(section_start + r'([^"]*)"').findall(html_text)[video]
        vid_url = 'https://youtube.com/watch?v=' + vid_id
        urls.append(vid_url)
    return urls


# Can only be used with a Youtube channel's source code
def get_channel_id(html_text):
    id_index = html_text.index('"browseId":"') + 12
    channel_id = html_text[id_index: html_text.index('"', id_index)]
    return channel_id


def order_by_date(videos: []) -> []:
    dates = [video['date'] for video in videos]

    ordered_videos = []
    for _ in range(len(videos)):
        video = list(filter(lambda v: v['date'] == max(dates), videos))[0]
        videos.remove(video)
        dates.remove(video['date'])
        del video['date']  # Dates are presumably no longer needed, so they're just removed.
        ordered_videos.append(video)
    return ordered_videos


# The following 3 functions test for ip blocked or similar returns.
# They don't account for returns of wrong URLs, so the user has to manually
# make sure every channel URL is correct before running the script.
def check_video_yt(html_text):
    if '<html>' in html_text:  # blocked ip
        return False
    data = video_yt(html_text)
    if data['title'] == 'Video Not Available' and data['channel_id'] == 'UCMDQxm7cUx3yXkfeHa5zJIQ':  # placeholder video
        return False
    return data


def check_channel_yt(html_text):
    if '<html>' in html_text:  # blocked ip
        return False
    html_start_index = html_text.index('<html') + 5
    if '>' in html_text[html_start_index: html_start_index + 30]:
        return False
    return True


def check_tw(html_text):
    if 'content="twitch.tv/' in html_text:
        return True
    return False


if __name__ == '__main__':
    tor_running = launch_tor()

    with open(settings.CHANNELS) as file_channels:
        file_channels = file_channels.read()

    urls_yt, urls_tw_live, urls_tw, urls_bt = find_channel_urls(file_channels)
    timer_start = datetime.now()
    # Scrape channel URLs:
    with concurrent.futures.ThreadPoolExecutor() as ex:
        r1 = ex.submit(scrape_concurrently, urls_yt, True, check_channel_yt, settings.YT_COOKIES)
        r2 = ex.submit(scrape_concurrently, urls_tw_live, True, check_tw)
        r3 = ex.submit(scrape_concurrently, urls_tw, True, check_tw)
        r4 = ex.submit(scrape_concurrently, urls_bt, True)
    print(datetime.now() - timer_start, '- time for scraping channels\n...')

    # Extract Youtube channels' ids and URLs of their recent uploads:
    urls_yt_videos = []
    channel_ids = []
    for web_return in r1.result():
        channel_html = web_return.text
        urls_yt_videos += urls_of_uploads(channel_html)
        channel_ids.append(get_channel_id(channel_html))

    # Scrape the uploads' URLs:
    timer_start = datetime.now()
    r5 = scrape_concurrently(urls_yt_videos, True, check_video_yt, settings.YT_COOKIES)
    print(datetime.now() - timer_start, '- time for scraping Youtube videos\n...')  # Time for scraping Youtube uploads

    # Append to sub_videos:
    sub_videos = [video_yt(web_return.text) for web_return in r5]  # YOUTUBE VIDEOS

    for web_return in r2.result():  # TWITCH LIVESTREAMS
        tw_stream_data = stream_tw(web_return.text)
        if tw_stream_data:  # if dictionary isn't empty
            sub_videos.append(tw_stream_data)

    for web_return in r3.result():  # TWITCH PAST VIDEOS
        sub_videos += past_videos_tw(web_return.text)

    for web_return in r4.result():  # BITCHUTE VIDEOS
        sub_videos += videos_bt(web_return.text)

    sub_videos = order_by_date(sub_videos)

    # Append to rec_videos:
    rec_videos = []
    rec_vids_urls = []
    for web_return in r5:
        rec_vids = recommendations(web_return.text)
        for rec_vid in rec_vids:
            if rec_vid['channel_id'] not in channel_ids and rec_vid['url'] not in rec_vids_urls:
                rec_vids_urls.append(rec_vid['url'])
                rec_videos.append(rec_vid)

    with open(settings.STORED_VIDEOS, 'w') as f:
        f.write('subVideos = ' + str(sub_videos) + '\n\n' + 'recVideos = ' + str(rec_videos))

    tor_running.kill()
    print('Tor killed.')
