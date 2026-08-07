# -*- coding: utf-8 -*-
"""
Classify and download Skland album images by series + category, split into originals and thumbnails.

Usage:
  python download.py <items_dir> <out_root> <mode>

  items_dir  : folder containing one .json per album post (item with imageList)
  out_root   : destination folder
  mode       : 'sample' -> download 1 image per album; 'all' -> every image

Folder layout:
  out_root/<album_title>/<类别-名称>/(完整图|缩略图)/xxx.webp
"""
import io, json, os, re, sys, time, urllib.request

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'data')
OUT = sys.argv[2] if len(sys.argv) > 2 else r'D:\works\wallpaper'
MODE = sys.argv[3] if len(sys.argv) > 3 else 'sample'
FILTER = sys.argv[4] if len(sys.argv) > 4 else None  # e.g. "Delta 勘探实录" or "塔卫二干员影像"
LIMIT = 1 if MODE == 'sample' else 99999

HDRS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def clean(s):
    return re.sub(r'[\\/:*?"<>|\r\n\t]', '', s).strip()

def get_album_files(SRC):
    out = []
    for f in sorted(os.listdir(SRC)):
        if f.endswith('.json') and not f.startswith('_'):
            out.append(os.path.join(SRC, f))
    return out

def style_url(img, style):
    for i in img.get('infos', []):
        if i.get('style') == style:
            return i['url']
    return img.get('url', '')

def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return 'exists'
    if not url:
        return 'no-url'
    try:
        req = urllib.request.Request(url, headers=HDRS)
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, 'wb') as f:
            f.write(r.read())
        if os.path.getsize(dest) > 1024:
            return 'ok'
        return 'bad-size'
    except Exception as e:
        return 'err:%s' % getattr(e, 'reason', e)

def get_items_from_file(path):
    with io.open(path, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        inner = data.get('data', data)
        if isinstance(inner, dict) and isinstance(inner.get('list'), list):
            out = []
            for entry in inner['list']:
                it = entry.get('item', entry)
                if isinstance(it, dict) and it.get('imageList'):
                    out.append(it)
            return out
        if isinstance(inner, dict) and inner.get('imageList'):
            return [inner]
    return []

def classify(item):
    title = item.get('title', '')
    if FILTER and FILTER not in title:
        return None
    if '塔卫二干员影像' in title:
        return ('塔卫二干员影像', '干员', clean(title))
    if 'Delta 勘探实录' in title:
        m = re.search(r'——(.+?)】', title)
        cat = clean(m.group(1)) if m else clean(title)
        return ('Delta 勘探实录', '地点', cat)
    return (clean(title), '相册', clean(title))

def process_item(path, out_root, limit):
    items = get_items_from_file(path)
    if not items:
        return []
    report = []
    seen_titles = set()
    for it in items:
        title = it.get('title', '')
        if title in seen_titles:
            continue
        seen_titles.add(title)
        cls = classify(it)
        if cls is None:
            continue
        series, kind, cat = cls
        imgs = it.get('imageList', [])
        if not imgs:
            continue
        cat_dir = os.path.join(out_root, series, '%s-%s' % (kind, cat))
        full_dir = os.path.join(cat_dir, '完整图')
        thumb_dir = os.path.join(cat_dir, '缩略图')
        os.makedirs(full_dir, exist_ok=True)
        os.makedirs(thumb_dir, exist_ok=True)
        for idx, img in enumerate(imgs[:limit]):
            orig = style_url(img, 'origin')
            ext = orig.split('?')[0].split('.')[-1].lower()
            if ext not in ('webp', 'png', 'jpg', 'jpeg', 'gif'):
                ext = 'webp'
            fname = '%s_%02d.%s' % (clean(cat), idx + 1, ext)
            full_dest = os.path.join(full_dir, fname)
            thumb_dest = os.path.join(thumb_dir, fname)
            r1 = fetch(orig, full_dest)
            r2 = fetch(orig + '?x-oss-process=style/thumbnail', thumb_dest)
            report.append((series, kind, cat, idx + 1, r1, r2))
    return report

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    files = get_album_files(SRC)
    if not files:
        print('No JSON album files found in', SRC)
        return 1
    ok = 0
    for f in files:
        try:
            reps = process_item(f, OUT, LIMIT)
        except Exception as e:
            print('SKIP', f, e)
            continue
        for r in reps:
            print('  ', r)
            if r[4] in ('ok', 'exists'):
                ok += 1
    print('IMAGES_FULL_OK:', ok)
    return 0

if __name__ == '__main__':
    sys.exit(main())