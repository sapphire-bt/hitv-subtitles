import base64
import hashlib
import json
import random
import re
import sys

from os.path import basename
from urllib.parse import urlencode
from xml.etree import ElementTree

import requests

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
AES_KEY = "Wcb26arWkvkcAZc378eR"
APP_KEY = "bywebabcd1234"
BLOCK_SIZE = 16


def btoa(value):
    return base64.b64encode(value.encode()).decode()

def md5(value):
    return hashlib.md5(str(value).encode()).hexdigest()

def decrypt(kv, data):
    key = kv[:BLOCK_SIZE].encode()
    vector = kv[BLOCK_SIZE:].encode()
    data = base64.b64decode(data)
    cipher = AES.new(key, AES.MODE_CBC, iv=vector)
    return unpad(cipher.decrypt(data), BLOCK_SIZE).decode()

def decrypt_response(timestamp, did, data):
    a = md5(did + str(timestamp))
    b = md5(a + AES_KEY)
    return decrypt(b, data)

def rand_id():
    char_set = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
    return "".join(random.choice(char_set) for x in range(24))

def sign(sid, eid, scid, sq):
    return md5(urlencode({
        "eid": eid,
        "scid": scid,
        "sid": sid,
        "sq": sq,
        "appkey": APP_KEY,
    }))

def format_timecode(value):
    h, m, s = value.split(":")
    s, ms = s.split(".")
    timecode = f"{h:02}:{m:02}:{s:02},{ms:03}"
    return timecode

def get(url, headers={}, params={}):
    print_url(url, params)
    headers = {
        "User-Agent": USER_AGENT,
        **headers,
    }
    return requests.get(url, headers=headers, params=params)

def api_request(endpoint, params=None):
    url = f"https://api.gohitv.com/s1/w/series/api/{endpoint}"
    did = rand_id()
    headers = {
        "platform": "pc",
        "did": did,
    }
    response = get(url, headers=headers, params=params).json()
    decrypted = decrypt_response(response["ts"], did, response["data"])
    return json.loads(decrypted)

def print_url(url, params={}):
    if params:
        url += f"?{urlencode(params)}"
    print(f"Fetching {url}")

def get_episode_id(url):
    response = get(url)
    html = response.content.decode()
    eid_str = 'eid="'
    start = html.find(eid_str) + len(eid_str)
    html = html[start:]
    episode_id = html[:html.find('"')]
    return episode_id

def get_media_sources(url):
    episode_id = get_episode_id(url)

    ep_data = api_request("episode/detail", {
        "eid": episode_id,
    })

    series_id = ep_data["episode"]["sid"]
    source_id = ep_data["episode"]["sources"][0]["scid"]
    sq = 1

    sources = api_request("series/rslv", {
        "sid": series_id,
        "eid": episode_id,
        "scid": source_id,
        "sq": sq,
        "sign": sign(series_id, episode_id, source_id, sq),
    })

    # Add some extra info for the output file names
    sources["__meta"] = {
        "series_name": ep_data["episode"]["sidAlias"],
        "episode_no": ep_data["episode"]["serialNo"],
    }

    return sources

def create_filename(sources, subtitle):
    series_name = sources["__meta"]["series_name"].replace("'", "")
    series_name = re.sub(r"[^0-9A-Za-z\-_]+", "-", series_name)
    series_name = re.sub(r"--+", "-", series_name).strip("-")
    ep_num = sources["__meta"]["episode_no"]
    sub_lang = subtitle["langCode"]
    sub_id = subtitle["subtitleId"]
    return f"{series_name}_e{ep_num:02}_{sub_lang}_{sub_id}"

class HiTVSubtitles:
    def __init__(self, key_and_vector, xml):
        self.groups = []
        root = ElementTree.fromstring(xml)
        for dia in root.iter("dia"):
            self.groups.append(SubtitleGroup(key_and_vector, dia))

    def as_srt(self):
        lines = []
        for x, item in enumerate(self.groups):
            lines.append(f"{x+1}\n{item.as_string()}")
        return "\n\n".join(lines).replace("\\N", "\n")

class SubtitleGroup:
    def __init__(self, key_and_vector, node):
        self.start = format_timecode(node.find("st").text)
        self.end = format_timecode(node.find("et").text)
        self.content = decrypt(key_and_vector, node.find("con").text)

    def as_string(self):
        return "\n".join([
            f"{self.start} --> {self.end}",
            self.content,
        ])

def main(argc, argv):
    if argc < 2:
        print("Usage:")
        print(f"    {basename(__file__)} <url> [<lang code 1>] [<lang code 2>] [...]")
        print()
        return 1

    url = argv[1]
    lang_codes = None

    if argc > 2:
        lang_codes = argv[2:]

    sources = get_media_sources(url)

    for item in sources["subtitles"]:
        if lang_codes is None or item["langCode"] in lang_codes:
            output_name = create_filename(sources, item) + ".srt"
            response = get(item["url"])
            xml = response.content.decode()
            subtitles = HiTVSubtitles(item["key"], xml)

            with open(output_name, "w", encoding="utf-8") as f:
                f.write(subtitles.as_srt())

            print(f"Saved as {output_name}")

    print("Done")
    return 0

if __name__ == "__main__":
    sys.exit(main(len(sys.argv), sys.argv))
