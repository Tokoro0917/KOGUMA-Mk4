// ビューアの試験(Playwright)。使い方: OUT_DIR=/tmp python3 make_sample.py && OUT_DIR=/tmp node test.js
// ビューアの試験(Playwright): 見本のログを読ませて描けるか、にせの機体(ブートローダと同じ動き)で書き込めるか
const { chromium } = require('playwright');
const path = require('path');
const OUT = process.env.OUT_DIR || '/tmp';                                      // 見本のファイルと、画面の写真を置く所
const VIEWER = 'file://' + path.resolve(__dirname, '..', 'viewer.html');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1300, height: 1000 } });
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(VIEWER);
  await p.setInputFiles('#fOpen', OUT + '/sample_mk4.txt');
  await p.waitForTimeout(800);
  console.log('一覧:', await p.$$eval('#list .blk .t', (es) => es.map((e) => e.textContent)));
  const names = ['explore', 'sensor', 'current', 'run'];
  for (let k = 0; k < 4; k++) {
    await (await p.$$('#list .blk'))[k].click();
    await p.waitForTimeout(400);
    await p.screenshot({ path: `${OUT}/v_${names[k]}.png` });
    console.log(names[k], 'グラフ', await p.$$eval('canvas', (c) => c.length), '題', await p.$eval('#view h2', (h) => h.textContent));
  }
  // 書き込み: にせの機体をつなぐ。30 行目を落とし、最初は走るプログラムのふり(返事なし)で @flash を使わせる
  await p.click('#bFw');
  await p.waitForTimeout(200);
  await p.evaluate(() => {
    const img = new Uint8Array(1 << 19).fill(0xFF);
    let len = 0, crc = 0, until = 0, acked = 0, inBoot = false, count = 0, gapRep = -1;
    const reply = (t) => setTimeout(() => serialParser.feed(t + '\n'), 2);
    link = {
      kind: 'ble',
      send: async (text) => {
        for (const line of text.split('\n')) {
          if (!line) continue;
          count++;
          if (count === 30) continue;
          if (!inBoot) { if (line === '@flash') { inBoot = true; reply('#BOOT ready'); } continue; }
          if (line.startsWith('fw begin ')) {
            const a = line.split(' '); len = +a[2]; crc = parseInt(a[3], 16); until = 0; acked = 0; reply('#OK fw begin');
          } else if (line === 'fw end') {
            const ok = crc32(img.subarray(0, len)) === crc;
            reply(ok ? '#OK fw end' : '#ERR fw crc');
            if (ok) setTimeout(() => reply('#STATUS state=idle'), 20);
          } else if (line.startsWith('fw ')) {
            const a = line.split(' '); const off = +a[1];
            const d = Uint8Array.from(atob(a[2]), (c) => c.charCodeAt(0));
            if (off > until) { if (gapRep !== until) { gapRep = until; reply('#ERR fw gap ' + until); } continue; }
            img.set(d, off);
            if (off + d.length > until) until = off + d.length;
            if (Math.floor(until / 4096) > Math.floor(acked / 4096) || (until === len && acked !== len)) { acked = until; reply('#OK fw ' + until); }
          }
        }
      },
    };
    connectedUI('接続中 にせの機体');
  });
  await p.setInputFiles('input[type=file][accept=".bin"]', OUT + '/app.bin');
  await p.waitForTimeout(300);
  await p.click('#bFwWrite');
  await p.waitForFunction(() => !fw.busy && fw.log.length > 2, null, { timeout: 60000 });
  console.log((await p.evaluate(() => fw.log)).join('\n'));
  await p.screenshot({ path: OUT + '/v_fw.png' });
  console.log('エラー:', errs);
  await b.close();
})();
