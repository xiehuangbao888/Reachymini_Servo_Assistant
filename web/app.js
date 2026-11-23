'use strict';
// Keep translations in this bundle so existing local servers can serve the UI without a restart.
const EN = {
  'reachymini舵机调试助手':'reachymini Servo Assistant', 'Reachy Mini 首页':'Reachy Mini home',
  '设备维护':'Device maintenance', '舵机参数恢复':'Servo configuration', '操作流程':'Workflow',
  '连接与扫描':'Connect & scan', '确认串口及舵机 ID':'Check the port and servo IDs',
  '保存原始备份':'Back up original settings', '恢复前的必需步骤':'Required before writing',
  '选择参数与目标':'Select settings & servos', '核对计划后写入':'Review the plan before writing',
  '查看校验结果':'Review verification results', '保存日志并重新测试':'Save the log and test again',
  '语言':'Language', '未连接':'Disconnected', '备份 / 恢复':'Backup / Restore',
  '演示模式':'Demo mode', '所有设备和写入均为内存模拟，不会连接串口或更改真实舵机。':'All devices and writes are simulated in memory. No serial port or physical servo is accessed.',
  '开始之前，请先关闭 reachymini 的 App 应用程序。':'Close the reachymini app before you start.',
  '插入 USB 后，点击“刷新串口”，查看新增的端口，即为我们需要选择的端口。':'After connecting USB, click “Refresh ports”. Select the port that has just appeared.',
  '在恢复参数和修改舵机 ID 之前，需要先备份原始数据，否则无法进行下一步。':'Back up the original settings before restoring parameters or changing a servo ID. A backup is required to continue.',
  '连接设备':'Connect devices', '刷新串口':'Refresh ports', 'U2D2 串口':'U2D2 serial port', '波特率':'Baud rate',
  '正在读取串口…':'Loading ports…', '连接并扫描':'Connect & scan', '重新扫描':'Rescan', '取消扫描':'Cancel scan', '断开':'Disconnect',
  '请确认舵机正常供电。默认通信速率为 1,000,000 bps。':'Make sure the servos are powered. The default baud rate is 1,000,000 bps.',
  '总线设备':'Devices on the bus', '等待扫描设备':'Waiting for a scan', '连接后显示实际 ID、型号及固件版本':'Connect to see actual IDs, models and firmware versions.',
  '舵机位置':'Servo position', '型号':'Model', '固件':'Firmware', '状态':'Status',
  '默认对应关系：ID 10 为底座舵机，ID 11～16 分别为舵机 1～6，ID 17 为右天线，ID 18 为左天线。名称按默认 ID 标注，改过 ID 的舵机请结合实际接线确认。':'Default mapping: ID 10 = base; IDs 11–16 = servos 1–6; ID 17 = right antenna; ID 18 = left antenna. Labels follow default IDs. If IDs have changed, check the physical connections.',
  '必做':'Required', '未备份':'No backup', '读取总线上全部受支持舵机的完整控制表，保存为可回退的 JSON 文件。':'Read the complete control tables of all supported servos and save a JSON backup for recovery.',
  '备份全部舵机':'Back up all servos', '下载备份 JSON':'Download backup JSON',
  '完成全量备份后，解锁恢复及修改 ID。每次写入后需重新备份。':'Complete a full backup to unlock restore and ID changes. Make a new backup after each write.',
  '选择恢复参数':'Select restore settings', '正在载入参数…':'Loading profiles…', '更换 JSON':'Load JSON',
  '恢复目标':'Restore targets', '选择全部匹配项':'Select all matching', '扫描设备后，在此勾选需要恢复的舵机。':'Scan devices, then select the servos to restore here.',
  '仅写入勾选的舵机。型号须匹配，当前 ID、档案 ID 和最终 ID 须一致；保留当前总线波特率。':'Only selected servos will be written. Models and current/profile/final IDs must match. The bus baud rate is preserved.',
  '生成恢复计划':'Generate restore plan', '恢复计划':'Restore plan', '当前 ID':'Current ID', '档案 ID':'Profile ID', '最终 ID':'Final ID', '差异 / 写入':'Changed / Written',
  '核对上述目标后，输入':'Review the targets above, then type', '确认写入':'to confirm the write', '恢复并校验':'Restore & verify',
  '写入开始后请保持供电和连接。完成后 Torque 保持关闭。':'Keep power and USB connected during writing. Torque remains OFF when finished.',
  '修改舵机 ID':'Change servo ID', '单台修改':'One servo at a time',
  '先完成全量备份，再选择当前 ID 和未占用的新 ID。请托稳机构，修改时会关闭该舵机的 Torque。':'Complete a full backup, then select the current ID and an unused new ID. Support the mechanism: torque will be turned OFF.',
  '当前舵机':'Current servo', '选择要修改的舵机':'Select a servo', '新 ID（0～252）':'New ID (0–252)', '输入未占用的 ID':'Enter an unused ID',
  '机器人程序按 ID 识别舵机，请使用预期的 ID。若已有重复 ID，请只连接待修改的一台舵机。修改后恢复参数仍按新 ID 匹配，参数档案不会自动改名。':'Robot software identifies servos by ID. Use the expected ID. If duplicate IDs exist, connect only the servo you want to change. Restore profiles still match by ID; profiles are not automatically renamed.',
  '检查并生成修改计划':'Check & generate ID plan', '确定修改舵机 ID？':'Confirm servo ID change?',
  '请托稳机构并保持供电与连接。完成后 Torque 保持关闭，再次写入前需重新备份。':'Support the mechanism and keep power and USB connected. Torque stays OFF. Make a new backup before another write.',
  '取消':'Cancel', '确定修改':'Confirm change', '操作日志':'Activity log', '就绪':'Ready', '导出日志':'Download log',
  '等待连接串口':'Waiting for a serial connection', '操作记录将在这里实时显示。':'Operation logs will appear here in real time.',
  '配置参数恢复工具 · 非固件升级':'Configuration recovery · Not a firmware updater',
  '底座舵机':'Base servo', '右天线':'Right antenna', '左天线':'Left antenna', '未标注':'Unassigned', '受支持':'Supported', '不支持':'Unsupported',
  '型号不匹配或缺少同 ID 档案':'Model mismatch or no profile with the same ID', ' · 无匹配档案':' · No matching profile',
  '寄存器':'Register', '当前值':'Current value', '标准值':'Target value', '已完成':'Completed', '需重新备份':'New backup required', '不完整':'Incomplete', '进行中':'Running', '失败':'Failed',
  '未发现串口，请连接 U2D2 后刷新':'No serial ports found. Connect U2D2 and refresh.', '请求失败':'Request failed',
  'JSON 文件不能超过 1.9 MB。':'The JSON file must be smaller than 1.9 MB.',
  '演示恢复与校验已通过。此结果来自模拟设备，没有发生真实硬件写入。':'Demo restore and verification passed. This result comes from simulated devices; no physical hardware was written.',
  'RESTORE + VERIFY SUCCESS。所选舵机参数校验通过，Torque 保持关闭。请断电再上电，在机器人上重新测试 S5 顶部负载表现，并保留备份与日志。':'RESTORE + VERIFY SUCCESS. Selected servo settings were verified and torque remains OFF. Power-cycle the servos, test S5 at the top of its travel under load, and keep the backup and log.',
  '已断开连接。':'Disconnected.', '已切回 2026-11-20 15:38 的默认恢复参数。':'Loaded the default settings from the 2026-11-20 15:38 backup.',
  '参数文件格式无效，需使用原工具导出的 JSON。':'Invalid profile format. Use a JSON backup exported by the original tool.',
  '参数文件包含无效或重复 ID。':'The profile contains invalid or duplicate IDs.',
  '正在取消扫描并释放串口…':'Cancelling the scan and releasing the port…', '操作未完成':'Operation incomplete',
  '请先连接并扫描舵机。':'Connect and scan the servos first.', '未发现舵机，请检查供电、U2D2 连接和波特率。':'No servos found. Check power, the U2D2 connection and baud rate.',
  '总线上的 ID、型号或固件已变化，请重新扫描并备份。':'Bus IDs, models or firmware have changed. Rescan and make a new backup.',
  '请选择有效串口和波特率。':'Select a valid port and baud rate.', '扫描已取消，请重新选择 U2D2 串口。':'Scan cancelled. Select the U2D2 port again.',
  '演示备份不能用于真实硬件。':'Demo backups cannot be used on physical hardware.', '写入前必须先完成当前连接的全量备份。':'Complete a full backup of the current connection before writing.',
  '请选择已扫描到的当前舵机 ID。':'Select a servo ID found in the scan.', '该舵机型号不支持修改 ID。':'Changing the ID of this model is not supported.',
  '新 ID 必须是 0～252 的整数。':'The new ID must be an integer from 0 to 252.', '新 ID 不能与当前 ID 相同。':'The new ID must differ from the current ID.',
  '请先生成并核对最新的修改 ID 计划。':'Generate and review a new ID change plan first.', '请在最新修改计划弹窗中点击“确定修改”。':'Click “Confirm change” in the latest ID plan dialog.',
  '请选择至少一台舵机，ID 不得重复。':'Select at least one servo. IDs must be unique.', '请核对最新恢复计划并输入 RESTORE。':'Review the latest restore plan and type RESTORE.',
  '已有操作正在执行，请等待结束。':'An operation is already running. Wait for it to finish.', '未知操作。':'Unknown operation.',
  '备份有读取失败项；已保存诊断文件，但不能开始恢复。请下载备份并检查日志。':'Some registers could not be read. A diagnostic backup was saved, but restore is blocked. Download the backup and check the log.',
  '当前 ID 回读不一致，请检查连接。':'Current ID readback mismatch. Check the connection.', '当前 ID 回读不一致，未修改 ID。':'Current ID readback mismatch. The ID was not written.',
  'Torque 未关闭，未修改 ID。':'Torque is not OFF. The ID was not written.', '新 ID 回读校验失败。':'New ID readback verification failed.',
  '新 ID 的 Torque OFF 校验失败。':'Torque OFF verification at the new ID failed.', '修改后的总线列表与计划不一致。':'The bus inventory after the change does not match the plan.',
  '寄存器自生成计划后发生变化。尚未写入，请重新备份和生成计划。':'Registers changed after the plan was generated. Nothing was written. Make a new backup and plan.',
  '未找到文件。':'File not found.', '请求须为 JSON 且不能超过 2 MB。':'The request must be JSON and no larger than 2 MB.', '请求格式无效。':'Invalid request format.',
  '当前没有进行中的扫描。':'No scan is running.', '操作进行中':'Operation in progress', 'Torque 未关闭':'Torque is not OFF',
  '仅允许本机访问。':'Only local access is allowed.', '仅允许同源本机操作。':'Only same-origin local requests are allowed.', '会话已变化，请刷新页面。':'The session has changed. Refresh the page.',
  '模拟 U2D2 · 不连接硬件':'Simulated U2D2 · No hardware connection'
};
// Known backend diagnostics are translated for display; downloads retain the original log.
const EN_FRAGMENTS = {
  '（内置默认）':' (built-in default)', '本地服务连接失败，请检查启动窗口。':'Cannot reach the local service. Check the terminal window. ',
  '发现 ':'Found ', ' 台舵机，请核对型号和实际 ID。':' servos. Check their models and actual IDs.', '已载入 ':'Loaded ', ' 台舵机参数档案。':' servo profiles.',
  '已完整备份 ':'Backed up ', ' 台支持的舵机。':' supported servos completely.', '修改 ID 计划：':'ID change plan: ', '，请核对后确认。':'. Review and confirm.',
  '。Torque 保持关闭；再次写入前请重新备份。':'. Torque remains OFF. Make a new backup before writing again.',
  '恢复计划已生成：仅写入选中的 ':'Restore plan ready: only the selected ', ' 台舵机，ID 和波特率保持一致。':' servos will be written. IDs and baud rate are preserved.',
  '扫描进程异常退出：':'Scan process failed: ', '新 ID ':'New ID ', ' 已被占用。':' is already in use.', '无法确认 ID ':'Cannot verify whether ID ', ' 是否空闲：':' is available: ',
  ' 型号不受支持。':' has an unsupported model.', ' 固件版本无效。':' has an invalid firmware version.', ' 档案不完整，请使用完整备份。':' has an incomplete profile. Use a complete backup.',
  ' 缺少寄存器。':' is missing registers.', ' 缺少配置项：':' is missing configuration items: ', ' 的 ID / Protocol Type 不匹配。':' has an ID / Protocol Type mismatch.',
  ' Model Number 不匹配。':' has a Model Number mismatch.', ' 波特率代码无效。':' has an invalid baud rate code.',
  '，新 ID、型号及 Torque OFF 校验通过。':': new ID, model and Torque OFF verified.', ' · 演示结果':' · Demo result', ' · 请断电再上电后测试':' · Power-cycle before testing',
  '扫描超时（':'Scan timed out (', ' 秒），已停止本次连接。请检查 U2D2 串口、供电和波特率后重试。':' s). The connection was stopped. Check the U2D2 port, power and baud rate before retrying.',
  ' 存在未知寄存器 ':' has an unknown register: ', ' 寄存器定义不匹配。':' has a register definition mismatch.', ' 数值超出范围。':' has a value outside the allowed range.',
  '] 开始':'] Started', ' · 演示模式，无硬件写入':' · Demo mode, no hardware writes',
  '[WARNING] 日志文件保存失败，请保留页面日志：':'[WARNING] Could not save the log file. Keep the on-screen log: ',
  ' 未检测到或缺少同 ID 参数档案。':' was not detected or has no profile with the same ID.', ' 当前 ':' current ', '，档案 ':'; profile ',
  ' 固件的 Indirect Address 布局不兼容，禁止写入。':' has an incompatible firmware Indirect Address layout. Writing is blocked.',
  ' 档案波特率与当前总线不同。本网页保留 ID / 波特率，请使用匹配档案。':' profile baud rate differs from the bus. This tool preserves IDs and baud rate; use a matching profile.',
  ' 配置完整校验通过；Torque OFF。':' configuration fully verified; Torque OFF. ', 'Torque OFF 无法确认：ID ':'Cannot confirm Torque OFF for IDs ',
  '，请断电检查。':'. Disconnect power and inspect the device.', '正在连接并扫描，最多等待 ':'Connecting and scanning; timeout: ', ' 秒…':' s…',
  '[WARNING] ID 写入已尝试，实际 ID 可能为 ':'[WARNING] An ID write was attempted. The actual ID may be ', ' 或 ':' or ', '；请重新扫描确认，不自动回滚。':'. Rescan to confirm; no automatic rollback.',
  '[WARNING] 未写入 ID；Torque 关闭状态未完成确认，请托稳机构并检查连接。':'[WARNING] The ID was not written. Torque OFF was not confirmed. Support the mechanism and check the connection.',
  ' 最终回读校验失败，停止后续恢复。':' final readback verification failed. Remaining restores stopped.', ' Status Return Level 校验失败：':' Status Return Level verification failed: ',
  ' Torque OFF 无法确认：':' Torque OFF could not be confirmed: ', '；请断电检查。':'; disconnect power and inspect the device.'
};
const EN_PATTERNS = [
  [/^舵机 (\d+)$/, 'Servo $1'], [/^(\d+) 台$/, '$1 servos'],
  [/^(\d+) 台参数档案 · 按实际 ID 匹配$/, '$1 profiles · Matched by actual ID'],
  [/^(\d+) 台 · 保留 ID$/, '$1 servos · IDs preserved'], [/^(\d+) \/ (\d+) 项$/, '$1 / $2 items'],
  [/ · 查看全部写入项$/, ' · View all writes'],
  [/。关闭 Torque 后仅修改 ID，保持当前波特率及配置参数。$/, '. Torque will be turned OFF. Only the ID changes; baud rate and configuration are preserved.']
];
let language = 'zh';
try { language = localStorage.getItem('reachymini-language') === 'en' ? 'en' : 'zh'; } catch (_) { /* Storage can be disabled. */ }
const requestedLanguage = new URLSearchParams(location.search).get('lang');
if (['zh','en'].includes(requestedLanguage)) language = requestedLanguage;
const diagnosticTranslations = Object.entries({...EN,...EN_FRAGMENTS}).sort((a,b) => b[0].length - a[0].length);
function tr(value) {
  const text = String(value);
  if (language !== 'en') return text;
  if (Object.hasOwn(EN,text)) return EN[text];
  let result = text;
  EN_PATTERNS.forEach(([pattern,replacement]) => {result = result.replace(pattern,replacement);});
  diagnosticTranslations.forEach(([source,target]) => {result = result.split(source).join(target);});
  return result;
}
const staticTranslations = [];
const textWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
while (textWalker.nextNode()) {
  const node = textWalker.currentNode, source = node.textContent;
  if (Object.hasOwn(EN,source.trim())) staticTranslations.push({node,source});
}
const translatedAttributes = [...document.querySelectorAll('[placeholder],[aria-label]')].flatMap(node =>
  ['placeholder','aria-label'].filter(name => node.hasAttribute(name)).map(name => ({node,name,source:node.getAttribute(name)})));
function translateStatic() {
  document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
  document.title = tr('reachymini舵机调试助手');
  staticTranslations.forEach(({node,source}) => {if(node.isConnected) node.textContent = source.replace(source.trim(),tr(source.trim()));});
  translatedAttributes.forEach(({node,name,source}) => node.setAttribute(name,tr(source)));
  $('language').value = language;
}
const $ = id => document.getElementById(id);
function servoName(id) {
  if (id === 10) return '底座舵机';
  if (id >= 11 && id <= 16) return `舵机 ${id - 10}`;
  if (id === 17) return '右天线';
  if (id === 18) return '左天线';
  return '未标注';
}
let state = null, selected = new Set(), activePlan = null, activeIdPlan = null, ignoredPlan = null, clientError = null, locked = false, logCount = 0, polling = false;
let renderedLanguage = null, planLanguage = null, idPlanLanguage = null;
function el(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = tr(text); if (className) n.className = className; return n; }
async function api(path, payload) {
  const options = payload === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Tool-Token':state.token}, body:JSON.stringify(payload)};
  const response = await fetch('/api/' + path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || '请求失败');
  return data;
}
function localError(error) { clientError = error.message; $('job-message').textContent = tr(clientError); $('job-message').className = 'job-message error'; }
function invalidatePlan(blockServer = true) { if (blockServer && state?.plan) ignoredPlan = state.plan.id; activePlan = activeIdPlan = null; $('plan').hidden = true; $('id-plan').close(); $('confirmation').value = ''; $('start-restore').disabled = $('change-id').disabled = true; }
async function action(kind, payload = {}) {
  if (locked || (state?.job.status === 'running' && kind !== 'cancel-scan')) return;
  clientError = null;
  locked = true; renderButtons();
  try { await api(kind, payload); await poll(); }
  catch (error) { localError(error); }
  finally { locked = false; renderButtons(); }
}
async function ports() {
  try {
    const items = await api('ports'); const previous = $('port').value;
    $('port').replaceChildren();
    if (!items.length) $('port').append(new Option(tr('未发现串口，请连接 U2D2 后刷新'), ''));
    items.forEach(p => $('port').append(new Option(p.device + ' · ' + tr(p.description), p.device)));
    if (items.some(p => p.device === previous)) $('port').value = previous;
    renderButtons();
  } catch(error) { localError(error); }
}
function renderButtons() {
  if (!state) return;
  const busy = locked || state.job.status === 'running', connected = !!state.connection;
  ['port','baudrate','refresh-ports'].forEach(id => $(id).disabled = busy);
  $('scan').disabled = busy || !$('port').value;
  $('scan').textContent = tr(connected ? '重新扫描' : '连接并扫描');
  $('cancel-scan').hidden = state.job.status !== 'running' || state.job.kind !== 'scan';
  $('cancel-scan').disabled = locked;
  $('disconnect').disabled = busy || !connected;
  $('backup-all').disabled = busy || !connected;
  $('profile-file').disabled = busy;
  ['old-id','new-id'].forEach(id => $(id).disabled = busy);
  const oldId = Number($('old-id').value), newId = Number($('new-id').value);
  $('make-id-plan').disabled = busy || !state.backup?.valid || $('old-id').value === '' || $('new-id').value === '' || !Number.isInteger(newId) || newId < 0 || newId > 252 || oldId === newId || state.devices.some(d => d.id === newId);
  $('change-id').disabled = busy || !activeIdPlan;
  document.querySelector('.upload-label').classList.toggle('disabled', busy);
  $('select-all').disabled = busy || !state.devices.some(eligible);
  $('make-plan').disabled = busy || !state.backup?.valid || !selected.size;
  $('confirmation').disabled = busy;
  $('start-restore').disabled = busy || !activePlan || $('confirmation').value !== 'RESTORE';
  document.querySelectorAll('#targets input').forEach(n => n.disabled = busy || n.dataset.eligible !== 'true');
}
function eligible(d) { return d.supported && state.profiles.some(p => p.id === d.id && p.model === d.model); }
function renderDevices() {
  const previousId = $('old-id').value;
  $('old-id').replaceChildren(new Option(tr('选择要修改的舵机'), ''));
  state.devices.filter(d => d.supported).forEach(d => $('old-id').append(new Option(`ID ${d.id} · ${tr(servoName(d.id))} · ${d.model}`, d.id)));
  if (state.devices.some(d => String(d.id) === previousId && d.supported)) $('old-id').value = previousId;
  $('device-count').textContent = tr(state.devices.length + ' 台');
  $('devices-empty').hidden = !!state.devices.length; $('device-table').hidden = !state.devices.length;
  $('devices-body').replaceChildren();
  state.devices.forEach(d => {
    const tr = el('tr');
    tr.append(el('td',d.id),el('td',servoName(d.id)),el('td',d.model),el('td','V' + d.firmware));
    const td = el('td'); td.append(el('span',d.supported ? '受支持' : '不支持', 'badge ' + (d.supported ? 'mint' : 'error'))); tr.append(td);
    $('devices-body').append(tr);
  });
  selected = new Set([...selected].filter(id => state.devices.some(d => d.id === id && eligible(d))));
  $('targets').replaceChildren(); $('targets-empty').hidden = !!state.devices.length;
  state.devices.forEach(d => {
    const ok = eligible(d), label = el('label',undefined,'target' + (ok ? '' : ' unavailable'));
    const input = el('input'); input.type = 'checkbox'; input.value = d.id; input.dataset.eligible = String(ok); input.checked = selected.has(d.id);
    input.addEventListener('change', () => {input.checked ? selected.add(d.id) : selected.delete(d.id); invalidatePlan(); renderButtons();});
    label.title = ok ? d.model : tr('型号不匹配或缺少同 ID 档案');
    label.append(input, el('span',`ID ${d.id} · ${tr(servoName(d.id))}` + (ok ? '' : ' · 无匹配档案'))); $('targets').append(label);
  });
}
function renderPlan(plan) {
  if (plan?.kind !== 'restore') plan = null;
  if (plan && (plan.id === ignoredPlan || plan.rows.length !== selected.size || plan.rows.some(row => !selected.has(row.current_id)))) plan = null;
  if (activePlan?.id === plan?.id && planLanguage === language) return;
  const savedConfirmation = activePlan && activePlan.id === plan?.id ? $('confirmation').value : '';
  planLanguage = language;
  invalidatePlan(false);
  if (!plan) return;
  activePlan = plan; $('plan').hidden = false;
  $('confirmation').value = savedConfirmation;
  $('plan-count').textContent = tr(plan.rows.length + ' 台 · 保留 ID');
  $('plan-body').replaceChildren(); $('plan-details').replaceChildren();
  plan.rows.forEach(row => {
    const tr = el('tr');
    [row.current_id,row.backup_id,row.final_id,`${row.changes} / ${row.write_count} 项`].forEach(v => tr.append(el('td',v)));
    $('plan-body').append(tr);
    const details = el('details'); details.append(el('summary',`ID ${row.current_id} · ${row.model} · ${row.baudrate.toLocaleString()} bps · 查看全部写入项`));
    const table = el('table'), head = el('tr'); ['寄存器','当前值','标准值'].forEach(v => head.append(el('th',v))); table.append(head);
    row.items.forEach(item => {const r = el('tr');r.append(el('td',item.name),el('td',item.before),el('td',item.after,item.before !== item.after ? 'changed' : ''));table.append(r);});
    const scroll = el('div',undefined,'table-scroll'); scroll.append(table); details.append(scroll); $('plan-details').append(details);
  });
}
function renderIdPlan(plan) {
  if (plan?.kind !== 'id' || plan.id === ignoredPlan || String(plan.current_id) !== $('old-id').value || String(plan.new_id) !== $('new-id').value) plan = null;
  if (activeIdPlan?.id === plan?.id && idPlanLanguage === language) return;
  idPlanLanguage = language;
  activeIdPlan = plan;
  if (!plan) { $('id-plan').close(); return; }
  $('id-plan-description').textContent = tr(`ID ${plan.current_id} → ID ${plan.new_id} · ${plan.model} · V${plan.firmware}。关闭 Torque 后仅修改 ID，保持当前波特率及配置参数。`);
  if (!$('id-plan').open) $('id-plan').showModal();
}
function render(next) {
  const old = state; state = next;
  $('demo-banner').hidden = !state.demo;
  $('connection-badge').textContent = state.connection ? `${state.connection.port} · ${state.connection.baudrate.toLocaleString()} bps` : tr('未连接');
  $('connection-badge').className = 'badge' + (state.connection ? ' mint' : '');
  $('profile-name').textContent = language === 'en' ? state.profile_name.replace('（内置默认）',' (built-in default)') : state.profile_name;
  $('profile-count').textContent = tr(state.profiles.length + ' 台参数档案 · 按实际 ID 匹配');
  if (!old || renderedLanguage !== language || JSON.stringify(old.devices) !== JSON.stringify(state.devices) || JSON.stringify(old.profiles) !== JSON.stringify(state.profiles)) renderDevices();
  $('backup-badge').textContent = tr(state.backup ? (state.backup.valid ? '已完成' : state.backup.complete ? '需重新备份' : '不完整') : '未备份');
  $('backup-badge').className = 'badge' + (state.backup ? (state.backup.complete ? ' mint' : ' error') : '');
  $('download-backup').hidden = !state.backup;
  if (state.backup) {$('download-backup').href = state.backup.url; $('backup-description').textContent = state.backup.name;}
  else $('backup-description').textContent = tr('完成全量备份后，解锁恢复及修改 ID。每次写入后需重新备份。');
  renderPlan(state.plan);
  renderIdPlan(state.plan);
  const statuses = {idle:'就绪',running:'进行中',success:'已完成',error:'失败'};
  $('job-badge').textContent = tr(statuses[state.job.status]);
  $('job-badge').className = 'badge ' + ({running:'running',success:'mint',error:'error'}[state.job.status] || '');
  $('job-message').textContent = tr(clientError || state.job.message);
  $('job-message').className = 'job-message ' + (clientError ? 'error' : ['error','success'].includes(state.job.status) ? state.job.status : '');
  const success = state.job.kind === 'restore' && state.job.status === 'success';
  $('result').hidden = !success;
  if (success) $('result').textContent = tr(state.demo ? '演示恢复与校验已通过。此结果来自模拟设备，没有发生真实硬件写入。' : 'RESTORE + VERIFY SUCCESS。所选舵机参数校验通过，Torque 保持关闭。请断电再上电，在机器人上重新测试 S5 顶部负载表现，并保留备份与日志。');
  $('step-connection').classList.toggle('done',!!state.connection);
  $('step-backup').classList.toggle('done',!!state.backup?.valid);
  $('step-restore').classList.toggle('done',!!state.plan || success);
  $('step-activity').classList.toggle('done',success);
  renderButtons();
  renderedLanguage = language;
}
async function poll() {
  if (polling) return;
  polling = true;
  try {
    const [next, lines] = await Promise.all([api('state'),api('logs')]); render(next);
    if (lines.length !== logCount) {
      const consoleEl = $('logs'); const atBottom = consoleEl.scrollHeight - consoleEl.scrollTop - consoleEl.clientHeight < 60;
      consoleEl.replaceChildren();
      lines.slice(-600).forEach(line => {
        const cls = line.text.includes('[FAIL]') ? 'fail' : line.text.includes('[OK]') ? 'ok' : /WARNING|SKIP/.test(line.text) ? 'warning' : '';
        const n = el('div',undefined,'log-line ' + cls); n.append(el('span',line.time,'log-time'),document.createTextNode(tr(line.text))); consoleEl.append(n);
      });
      if (atBottom) consoleEl.scrollTop = consoleEl.scrollHeight;
      logCount = lines.length;
    }
    $('download-log').hidden = !lines.length || state.job.status === 'running';
  } catch (error) { localError(new Error('本地服务连接失败，请检查启动窗口。' + error.message)); }
  finally { polling = false; }
}
$('refresh-ports').addEventListener('click',ports);
$('cancel-scan').addEventListener('click',() => action('cancel-scan'));
$('port').addEventListener('change',renderButtons);
$('scan').addEventListener('click',() => {selected.clear();invalidatePlan();action('scan',{port:$('port').value,baudrate:Number($('baudrate').value)});});
$('disconnect').addEventListener('click',() => {selected.clear();invalidatePlan();action('disconnect');});
$('backup-all').addEventListener('click',() => action('backup'));
['old-id','new-id'].forEach(id => $(id).addEventListener('input',() => {invalidatePlan();renderButtons();}));
$('make-id-plan').addEventListener('click',() => {invalidatePlan();action('id_plan',{old_id:Number($('old-id').value),new_id:Number($('new-id').value)});});
$('cancel-id-change').addEventListener('click',() => {invalidatePlan();renderButtons();});
$('id-plan').addEventListener('cancel',event => {event.preventDefault();invalidatePlan();renderButtons();});
$('change-id').addEventListener('click',() => {
  if (!activeIdPlan || locked || state?.job.status === 'running') return;
  const payload = {plan_id:activeIdPlan.id,confirm:`CHANGE ${activeIdPlan.current_id} TO ${activeIdPlan.new_id}`};
  invalidatePlan();action('change_id',payload);
});
$('select-all').addEventListener('click',() => {state.devices.filter(eligible).forEach(d => selected.add(d.id));renderDevices();invalidatePlan();renderButtons();});
$('make-plan').addEventListener('click',() => action('plan',{ids:[...selected]}));
$('confirmation').addEventListener('input',renderButtons);
$('start-restore').addEventListener('click',() => {const payload = {plan_id:activePlan?.id,confirm:$('confirmation').value};$('confirmation').value='';action('restore',payload);});
$('profile-file').addEventListener('change',async event => {
  const file = event.target.files[0]; if (!file) return;
  try {if(file.size > 1900000) throw new Error('JSON 文件不能超过 1.9 MB。'); const data = JSON.parse(await file.text());invalidatePlan();await action('profile',{name:file.name,data});}
  catch(error) {localError(error);} finally {event.target.value='';}
});
$('language').addEventListener('change',() => {
  language = $('language').value === 'en' ? 'en' : 'zh';
  try {localStorage.setItem('reachymini-language',language);} catch (_) { /* Optional preference storage. */ }
  const url = new URL(location.href); url.searchParams.set('lang',language); history.replaceState(null,'',url);
  translateStatic(); logCount = -1;
  if (state) render(state);
  ports(); poll();
});
async function init() {translateStatic();await poll();await ports();setInterval(poll,800);}
init();
