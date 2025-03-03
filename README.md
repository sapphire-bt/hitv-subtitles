# HiTV Subtitle Ripper
Given a URL and optional language codes, downloads subtitles from http://gohitv.com/.

## Requirements
* pycryptodome - https://www.pycryptodome.org/

```bash
pip install pycryptodome
```

* requests - https://requests.readthedocs.io/

```bash
pip install requests
```

## Usage
Download all subtitles:
```bash
py get_hitv_subs.py https://www.gohitv.com/series/vi-vn/love-is-for-suckers
```

Download subtitles in Vietnamese and English:
```bash
py get_hitv_subs.py https://www.gohitv.com/series/vi-vn/love-is-for-suckers vi-VN en-US
```

## Background
https://reverseengineering.stackexchange.com/questions/32410/i-need-software-to-decode-this-subtitle-xml-file-anyone-know-what-it-encodes-wi/32413
