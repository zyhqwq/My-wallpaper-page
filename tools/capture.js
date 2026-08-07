const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PROFILE_ID = process.env.PROFILE_ID || '7532688806929';
const EDGE = process.env.MSEDGE || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const OUT_DIR = path.join(__dirname, 'data');
const URL = `https://www.skland.com/profile?id=${PROFILE_ID}`;

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

(async () => {
  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: 'new',
    args: ['--no-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1300, height: 950 });

  const captured = [];
  const manifest = [];

  page.on('response', async (res) => {
    const u = res.url();
    if (!u.includes('zonai.skland.com')) return;
    const ct = res.headers()['content-type'] || '';
    let buf = null;
    try { buf = await res.buffer(); } catch (e) {}
    if (!buf) return;
    const hash = crypto.createHash('md5').update(u).digest('hex').slice(0, 10);
    const isItems = /user\/items/.test(u);
    const ext = isItems || /json/.test(ct) ? 'json' : 'bin';
    const fn = `${hash}_${ext}.${ext}`;
    fs.writeFileSync(path.join(OUT_DIR, fn), buf);
    if (isItems) {
      captured.push(path.join(OUT_DIR, fn));
      manifest.push('ITEMS ' + u + ' => ' + fn);
    } else {
      manifest.push('OTHER ' + u + ' => ' + fn);
    }
  });

  console.log('Opening', URL);
  await page.goto(URL, { waitUntil: 'networkidle2', timeout: 90000 }).catch(e => console.log('nav err', e.message));

  // scroll to trigger pagination of the items feed
  for (let i = 0; i < 25; i++) {
    await page.evaluate(() => window.scrollBy(0, 1800));
    await new Promise(r => setTimeout(r, 1200));
  }
  await new Promise(r => setTimeout(r, 3000));

  fs.writeFileSync(path.join(OUT_DIR, '_manifest.txt'), manifest.join('\n'), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, '_item_files.txt'), captured.join('\n'), 'utf8');
  console.log('captured item JSON files:', captured.length);
  await browser.close();
})();