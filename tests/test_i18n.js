'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
const context = vm.createContext({URLSearchParams,location:{search:'?lang=en'},localStorage:{getItem:()=>'zh'}});
vm.runInContext(source.slice(0, source.indexOf('const staticTranslations =')), context);
const translate = text => vm.runInContext(`tr(${JSON.stringify(text)})`,context);
assert.equal(translate('reachymini舵机调试助手'),'reachymini Servo Assistant');
assert.equal(translate('发现 9 台舵机，请核对型号和实际 ID。'),'Found 9 servos. Check their models and actual IDs.');
assert.equal(translate('9 台参数档案 · 按实际 ID 匹配'),'9 profiles · Matched by actual ID');
assert.equal(translate('舵机 6'),'Servo 6');
assert.equal(translate('新 ID 17 已被占用。'),'New ID 17 is already in use.');
assert.equal(translate('RESTORE'),'RESTORE');
for (const text of [
  '[ID_PLAN] 开始 · 演示模式，无硬件写入',
  'ID 17 固件的 Indirect Address 布局不兼容，禁止写入。',
  'ID CHANGE + VERIFY SUCCESS · 15 → 20。Torque 保持关闭；再次写入前请重新备份。',
  'ID 15 → ID 20 · XL330-M288 · V53。关闭 Torque 后仅修改 ID，保持当前波特率及配置参数。',
  '扫描超时（8 秒），已停止本次连接。请检查 U2D2 串口、供电和波特率后重试。'
]) assert.doesNotMatch(translate(text),/[\u4e00-\u9fff]/);
vm.runInContext("language = 'zh'",context);
assert.equal(translate('新 ID 17 已被占用。'),'新 ID 17 已被占用。');
console.log('Translation tests passed.');
