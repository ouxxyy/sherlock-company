#!/usr/bin/env node
/** Runtime and visual checks for the generated offline sample. */

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const script = path.join(root, 'skill', 'sherlock-company', 'scripts', 'render_report.py');
// 用法：node tests/verify_generated_html.mjs [case-dir-name]；默认回归 4399 案例并复写 report-v5.html。
const caseName = process.argv[2] || '4399';
const caseDir = path.join(root, 'cases', caseName);
const caseFile = path.join(caseDir, 'decision-report.json');
const htmlName = caseName === '4399' ? 'report-v5.html' : 'report.html';
const htmlFile = path.join(caseDir, htmlName);
if (!fs.existsSync(caseFile)) {
  process.stderr.write(`未找到案件 JSON：${caseFile}\n`);
  process.exit(2);
}

execFileSync('python3', [script, caseFile, '--output', htmlFile], { stdio: 'inherit' });
const decisionState = JSON.parse(fs.readFileSync(caseFile, 'utf8')).decision?.state || '';
const doc = fs.readFileSync(htmlFile, 'utf8');
const checks = [];
const check = (name, ok, detail = '') => checks.push({ name, ok: Boolean(ok), detail });

check('无 script', !doc.toLowerCase().includes('<script'));
check('侦探图像已嵌入', doc.includes('data:image/jpeg;base64,'));
check('无外链样式和字体', !doc.toLowerCase().includes('<link') && !doc.toLowerCase().includes('@import') && !doc.toLowerCase().includes('@font-face'));
for (const forbidden of [
  '恭喜抽中',
  '职场真相手办卡',
  '抽卡代码',
  '3.5 STARS',
  '信息完整度',
  'SHERLOCK COMPANY · OFFER',
  'INTERACTIVE CLUE CARDS',
  'INTERVIEW CHEAT SHEET',
  'SERIES #',
  '不猜公司好不好',
  '——',
]) {
  check(`不含「${forbidden}」`, !doc.includes(forbidden));
}
check('使用新版报告模板', doc.includes('data-template="evidence-dossier-v2"'));

const browser = await chromium.launch({ channel: 'chrome', headless: true });
for (const [label, width, height, output] of [
  ['desktop', 1440, 1000, path.join(caseDir, `${htmlName.replace('.html', '')}-desktop.png`)],
  ['mobile', 390, 844, path.join(caseDir, `${htmlName.replace('.html', '')}-mobile.png`)],
]) {
  const context = await browser.newContext({ offline: true, viewport: { width, height } });
  const page = await context.newPage();
  const unexpectedRequests = [];
  page.on('request', request => {
    if (!request.url().startsWith('file://')) unexpectedRequests.push(request.url());
  });
  await page.goto(pathToFileURL(htmlFile).href, { waitUntil: 'load' });
  const body = await page.locator('body').innerText();
  for (const text of [decisionState, '先确认“谁在招你”', '证据分盒', '有没有目标团队的真实体验', '这些结论从哪里来'].filter(Boolean)) {
    check(`${label}·含「${text}」`, body.includes(text));
  }
  const sizes = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  check(`${label}·无横向溢出`, sizes.scroll <= sizes.client, `${sizes.scroll}>${sizes.client}`);
  const overflow = await page.evaluate(() => Array.from(document.querySelectorAll('body *')).filter(el => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && (r.right > innerWidth + 1 || r.left < -1);
  }).slice(0, 8).map(el => `${el.tagName}.${String(el.className).split(' ')[0]}`));
  check(`${label}·无元素越界`, overflow.length === 0, JSON.stringify(overflow));
  check(`${label}·离线零网络请求`, unexpectedRequests.length === 0, JSON.stringify(unexpectedRequests.slice(0, 3)));
  const links = await page.locator('a').evaluateAll(els => els.map(a => ({ rawHref: a.getAttribute('href') || '', href: a.href, target: a.target, rel: a.rel })));
  const externalLinks = links.filter(link => link.rawHref && !link.rawHref.startsWith('#'));
  const unsafe = externalLinks.filter(link => !/^https?:\/\//.test(link.href) || link.target !== '_blank' || !link.rel.includes('noopener') || !link.rel.includes('noreferrer'));
  check(`${label}·外链安全`, unsafe.length === 0, JSON.stringify(unsafe.slice(0, 3)));
  await page.screenshot({ path: output, fullPage: true });
  check(`${label}·截图生成`, fs.existsSync(output), output);
  await context.close();
}
await browser.close();

const failed = checks.filter(item => !item.ok);
for (const item of checks) {
  process.stdout.write(`[${item.ok ? 'PASS' : 'FAIL'}] ${item.name}${!item.ok && item.detail ? ` -- ${item.detail}` : ''}\n`);
}
process.stdout.write(`${checks.length - failed.length} / ${checks.length} passed\n`);
process.exitCode = failed.length ? 1 : 0;
