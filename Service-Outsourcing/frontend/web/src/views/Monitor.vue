<template>
<div>
<div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
<div><div class="page-title">实时监控</div><div class="page-subtitle">上传图片检测能效标签</div></div>
<div style="display:flex;gap:8px;align-items:center">
<div class="ml-st" :class="mlOk?'on':'off'"><span class="msd"></span>ML {{mlOk?'就绪':'离线'}}</div>
<div class="live-badge"><span class="live-dot"></span>LIVE</div>
</div>
</div>
<div class="page-body">
<div class="glass-card">
<div class="section-head"><span class="section-icon">📤</span> 图片检测</div>
<div class="ua" @click="triggerUpload" @dragover.prevent @drop.prevent="onDrop">
<input ref="fileInput" type="file" accept="image/*" style="display:none" @change="onFile"/>
<div v-if="busy" class="ua-ld"><span class="spinner"></span><span>正在检测...</span></div>
<div v-else-if="purl" class="ua-pv"><img :src="purl" class="pimg"/></div>
<div v-else class="ua-ph"><span style="font-size:32px">📁</span><span>点击或拖拽图片到此处上传</span><span style="font-size:11px;color:var(--text-3)">支持 JPG / PNG 格式</span></div>
</div>
<div class="ua-act">
<button class="btn-primary" :disabled="!selFile||busy" @click="doDetect">🔍 开始检测</button>
<button class="btn-ghost" @click="clearUp">清除</button>
</div>
</div>
<div v-if="errMsg" class="err-msg">{{errMsg}}</div>

<!-- Toast -->
<transition name="toast">
<div v-if="toast.show" class="toast-bar" :class="toast.type">{{toast.msg}}</div>
</transition>

<div class="status-strip" :class="stCls" v-if="cr.status">
<div class="ss-left"><span class="ss-icon">{{stIcon}}</span><div class="ss-text"><span class="ss-title">{{stText}}</span><span class="ss-time">{{cr.timestamp||''}}</span></div></div>
<div class="ss-right"><span v-if="cr.inference_time_ms" class="ss-perf">⚡ {{cr.inference_time_ms}}ms</span><span v-if="cr.ocrText" class="ss-tag">{{cr.ocrText}}</span></div>
</div>
<div class="dash-grid" v-if="cr.status">
<div class="glass-card">
<div class="section-head"><span class="section-icon">📋</span> 标签识别</div>
<div class="ocr-area">
<div class="img-frame"><img v-if="cr.imageUrl" :src="cr.imageUrl" class="det-img"/><div v-else class="img-ph">📷</div></div>
<div class="ocr-det">
<div class="or"><span class="ok">识别标签</span><span class="ov hl">{{cr.ocrText||'--'}}</span></div>
<div class="or"><span class="ok">预设型号</span><span class="ov">{{cr.presetModel||'--'}}</span></div>
<div class="or"><span class="ok">置信度</span><span class="ov">{{cr.confidence?(cr.confidence*100).toFixed(1)+'%':'--'}}</span></div>
<div class="or"><span class="ok">结果</span><span class="badge" :class="cr.isMatch?'badge-ok':'badge-ng'">{{cr.isMatch?'✓ 匹配':'✗ 不匹配'}}</span></div>
</div>
</div>
</div>
<div class="right-stack">
<div class="glass-card">
<div class="section-head"><span class="section-icon">⚠️</span> 缺陷检测</div>
<div class="defect-row">
<div v-for="d in dTypes" :key="d.n" class="dc" :class="{active:isDefectActive(d.n)}"><span class="dci">{{d.i}}</span><span class="dcn">{{d.n}}</span><span class="dcs">{{isDefectActive(d.n)?'检出':'正常'}}</span></div>
</div>
</div>
<div class="glass-card">
<div class="section-head"><span class="section-icon">📍</span> 位置检测</div>
<div class="pos-area"><div class="pos-grid"><div v-for="i in 9" :key="i" class="pc" :class="{lit:isPC(i)}"><span v-if="isPC(i)" class="pm"></span></div></div><div class="pos-info"><span class="pl">粘贴位置</span><span class="pv" :class="cr.positionStatus==='正常'?'ok':'ng'">{{cr.positionStatus||'--'}}</span></div></div>
</div>
</div>
</div>
<div class="glass-card" style="margin-top:16px">
<div class="section-head" style="justify-content:space-between"><span><span class="section-icon">📝</span> 最近记录</span><router-link to="/history" class="see-all">查看全部 →</router-link></div>
<div class="tbl-wrap"><table class="dtable"><thead><tr><th>时间</th><th>型号</th><th>结果</th><th>缺陷</th><th>位置</th></tr></thead>
<tbody><tr v-for="item in recent" :key="item.id" class="tbl-row"><td class="td-m">{{item.timestamp?.slice(-8)}}</td><td>{{item.productModel}}</td><td><span class="badge" :class="item.status==='OK'?'badge-ok':'badge-ng'">{{item.status}}</span></td><td>{{item.defectType||'无'}}</td><td>{{item.positionStatus}}</td></tr>
<tr v-if="recent.length===0"><td colspan="5" class="td-e">暂无记录</td></tr></tbody></table></div>
</div>
</div>
</div>
</template>

<script setup>
import {ref,reactive,computed,onMounted,onUnmounted} from 'vue'
import {api,ApiError} from '../api.js'

const dTypes=[{n:'破损',i:'💔'},{n:'污渍',i:'💧'},{n:'褶皱',i:'📄'},{n:'划痕',i:'🔪'},{n:'偏移',i:'↔️'}]
const mlOk=ref(false),purl=ref(''),busy=ref(false),errMsg=ref(''),selFile=ref(null),fileInput=ref(null),wsConnected=ref(false),destroyed=ref(false)
const cr=ref({status:'',ocrText:'',presetModel:'',isMatch:false,defectType:null,positionStatus:'',positionX:50,positionY:50,timestamp:'',imageUrl:'',confidence:0,inference_time_ms:0})
const recent=ref([])
let pollTimer=null
let ws=null
let heartbeatTimer=null  // #34: 提升为外部变量，避免泄漏

// Toast
const toast=reactive({show:false,msg:'',type:'info'})
let toastTimer=null
const showToast=(msg,type='info')=>{
  clearTimeout(toastTimer)
  toast.msg=msg;toast.type=type;toast.show=true
  toastTimer=setTimeout(()=>{toast.show=false},3000)
}

const stCls=computed(()=>cr.value.status==='OK'?'strip-ok':cr.value.status==='NG'?'strip-ng':'strip-idle')
const stIcon=computed(()=>cr.value.status==='OK'?'✓':cr.value.status==='NG'?'✗':'◎')
const stText=computed(()=>cr.value.status==='OK'?'检测合格':cr.value.status==='NG'?'检测不合格':'等待检测...')

const isPC=(i)=>{
  const r=Math.floor((i-1)/3),c=(i-1)%3
  const cr2=Math.floor((cr.value.positionY||50)/34)
  const cc=Math.floor((cr.value.positionX||50)/34)
  return r===cr2&&c===cc
}

const isDefectActive=(name)=>{
  const dt=cr.value.defectType
  if(!dt||dt==='无') return false
  return dt.includes(name)
}

const triggerUpload=()=>{if(!busy.value&&fileInput.value) fileInput.value.click()}

// #35: 释放旧 Object URL 防止内存泄漏
const onFile=(e)=>{
  const f=e.target.files[0]
  if(!f) return
  if(purl.value) URL.revokeObjectURL(purl.value)
  selFile.value=f
  purl.value=URL.createObjectURL(f)
  errMsg.value=''
}

const onDrop=(e)=>{
  const f=e.dataTransfer.files[0]
  if(!f) return
  if(purl.value) URL.revokeObjectURL(purl.value)
  selFile.value=f
  purl.value=URL.createObjectURL(f)
  errMsg.value=''
}

const clearUp=()=>{
  if(purl.value) URL.revokeObjectURL(purl.value)
  purl.value=''
  selFile.value=null
  errMsg.value=''
  if(fileInput.value) fileInput.value.value=''
}

// #36: 使用 api.js 封装层
const doDetect=async()=>{
  if(!selFile.value){errMsg.value='请先选择图片';return}
  busy.value=true
  errMsg.value=''
  const fd=new FormData()
  fd.append('file',selFile.value)
  try{
    const d=await api.upload('/api/ml/detect',fd)
    cr.value={
      status:d.status||'OK',
      ocrText:d.ocr_text||d.defect_type||'',
      presetModel:d.preset_model||'',
      isMatch:d.is_qualified,
      defectType:d.defect_type==='无'?null:d.defect_type,
      positionStatus:d.position_status||'正常',
      positionX:d.position_x?Math.round(d.position_x*100):50,
      positionY:d.position_y?Math.round(d.position_y*100):50,
      timestamp:d.timestamp||new Date().toLocaleTimeString(),
      imageUrl:d.image_url||'',
      confidence:d.confidence||0,
      inference_time_ms:d.inference_time_ms||0
    }
    showToast(d.is_qualified?'检测合格 ✓':'检测不合格 ✗',d.is_qualified?'ok':'ng')
    fetchRecent()
  }catch(e){
    errMsg.value=e instanceof ApiError?e.message:'网络错误: '+e.message
  }
  busy.value=false
}

const fetchRecent=async()=>{
  try{
    const d=await api.get('/api/recent?limit=10')
    recent.value=d.map((x,i)=>({
      id:'r_'+i,
      timestamp:x.timestamp||'',
      productModel:x.presetModel,
      status:x.status,
      defectType:x.defectType,
      positionStatus:x.positionStatus
    }))
  }catch{}
}

const pollData=async()=>{
  try{
    const d=await api.get('/api/current')
    if(d.timestamp&&d.timestamp!==cr.value.timestamp){
      cr.value={...d,
        positionX:d.positionX||50,
        positionY:d.positionY||50,
        timestamp:d.timestamp
      }
    }
  }catch{}
  fetchRecent()
}

// WebSocket连接 — #34: 心跳 interval 提升为外部变量; fix B4: destroyed 守卫
let reconnectTimer=null
const connectWS=()=>{
  if(destroyed.value) return  // fix B4: 组件已卸载，不再重连
  const proto=location.protocol==='https:'?'wss:':'ws:'
  const wsUrl=`${proto}//${location.host}/ws/detection`
  try{
    ws=new WebSocket(wsUrl)
    ws.onopen=()=>{
      wsConnected.value=true
      if(pollTimer){clearInterval(pollTimer);pollTimer=null}
      // 清理旧心跳，启动新心跳
      if(heartbeatTimer) clearInterval(heartbeatTimer)
      heartbeatTimer=setInterval(()=>{
        if(ws&&ws.readyState===WebSocket.OPEN) ws.send('ping')
      },30000)
    }
    ws.onmessage=(e)=>{
      try{
        const d=JSON.parse(e.data)
        if(d.type==='detection_result'){
          cr.value={
            ...cr.value,
            status:d.status||cr.value.status,
            defectType:d.defect_type==='无'?null:d.defect_type,
            positionStatus:d.position_status||'正常',
            confidence:d.confidence||cr.value.confidence,
            timestamp:d.timestamp||new Date().toLocaleTimeString(),
            imageUrl:d.image_url||cr.value.imageUrl,
          }
          showToast(d.status==='OK'?'新检测: 合格 ✓':'新检测: 不合格 ✗',d.status==='OK'?'ok':'ng')
          fetchRecent()
        }
      }catch{}
    }
    ws.onclose=()=>{
      wsConnected.value=false
      if(heartbeatTimer){clearInterval(heartbeatTimer);heartbeatTimer=null}
      if(!destroyed.value && !pollTimer) pollTimer=setInterval(pollData,5000)
      if(!destroyed.value) reconnectTimer=setTimeout(connectWS,3000)  // fix B4
    }
    ws.onerror=()=>{ws.close()}
  }catch{}
}

onMounted(async()=>{
  // 检查ML状态
  try{
    const d=await api.get('/api/ml/status')
    mlOk.value=d.available===true
  }catch{}
  // 加载当前结果
  try{
    const d=await api.get('/api/current')
    cr.value={...d,timestamp:d.timestamp||''}
  }catch{}
  fetchRecent()
  pollTimer=setInterval(pollData,5000)
  connectWS()
})

onUnmounted(()=>{
  destroyed.value=true  // fix B4: 阻止后续重连
  if(pollTimer) clearInterval(pollTimer)
  if(heartbeatTimer) clearInterval(heartbeatTimer)
  if(reconnectTimer) clearTimeout(reconnectTimer)
  if(purl.value) URL.revokeObjectURL(purl.value)
  if(ws) ws.close()
})
</script>

<style scoped>
.ml-st{display:flex;align-items:center;gap:6px;padding:4px 12px;border-radius:16px;font-size:11px;font-weight:600;transition:all 0.3s}
.ml-st.on{background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);color:var(--green)}
.ml-st.off{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.25);color:var(--red)}
.msd{width:6px;height:6px;border-radius:50%;background:currentColor;position:relative}
.ml-st.on .msd::after{content:'';position:absolute;inset:-2px;border-radius:50%;background:var(--green);animation:msdPulse 2s infinite;opacity:0}
@keyframes msdPulse{0%{transform:scale(1);opacity:0.5}100%{transform:scale(2.5);opacity:0}}
.live-badge{display:flex;align-items:center;gap:6px;padding:4px 12px;border-radius:16px;font-size:11px;font-weight:700;letter-spacing:1.5px;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:var(--red)}
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--red);animation:blink 1.5s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
.ua{border:2px dashed var(--border);border-radius:var(--radius-lg);padding:32px;text-align:center;cursor:pointer;transition:all 0.4s cubic-bezier(0.4,0,0.2,1);min-height:140px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
.ua::before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 50% 50%,rgba(99,102,241,0.04),transparent 70%);opacity:0;transition:opacity 0.4s}
.ua:hover{border-color:var(--accent);box-shadow:0 0 24px rgba(99,102,241,0.08)}
.ua:hover::before{opacity:1;animation:uploadBreath 2s ease-in-out infinite}
@keyframes uploadBreath{0%,100%{opacity:0.5}50%{opacity:1}}
.ua-ph{display:flex;flex-direction:column;align-items:center;gap:8px;color:var(--text-2);font-size:14px}
.ua-pv{max-height:220px;overflow:hidden;border-radius:8px}
.pimg{max-width:100%;max-height:220px;object-fit:contain}
.ua-ld{display:flex;align-items:center;gap:10px;color:var(--accent-2);font-size:14px}
.spinner{width:20px;height:20px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
/* Scanning line effect during detection */
.ua-ld::after{content:'';position:absolute;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--accent),transparent);animation:scanLine 1.5s ease-in-out infinite;top:0}
@keyframes scanLine{0%{top:0;opacity:0}10%{opacity:1}90%{opacity:1}100%{top:100%;opacity:0}}
.ua-act{display:flex;gap:8px;margin-top:12px}
.ua-act .btn-primary:disabled{opacity:.4;cursor:not-allowed}
.err-msg{margin-top:8px;padding:8px 12px;border-radius:8px;background:rgba(239,68,68,.08);color:var(--red);font-size:12px}
/* Toast */
.toast-bar{position:fixed;top:20px;right:20px;padding:12px 24px;border-radius:10px;font-size:13px;font-weight:600;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.3)}
.toast-bar.ok{background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.3);color:var(--green)}
.toast-bar.ng{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);color:var(--red)}
.toast-bar.info{background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);color:var(--accent-2)}
.toast-enter-active{animation:toastIn .3s ease}
.toast-leave-active{animation:toastOut .3s ease}
@keyframes toastIn{from{opacity:0;transform:translateY(-12px)}to{opacity:1;transform:translateY(0)}}
@keyframes toastOut{from{opacity:1}to{opacity:0;transform:translateY(-12px)}}
.status-strip{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-radius:var(--radius-lg);margin:16px 0;position:relative;overflow:hidden;animation:stripIn 0.5s cubic-bezier(0.16,1,0.3,1)}
@keyframes stripIn{from{opacity:0;transform:translateY(10px) scaleY(0.9)}to{opacity:1;transform:translateY(0) scaleY(1)}}
.strip-ok{background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.2)}
.strip-ng{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2)}
.strip-idle{background:var(--bg-2);border:1px solid var(--border)}
.strip-ok::after,.strip-ng::after{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;border-radius:2px}
.strip-ok::after{background:var(--green);box-shadow:0 0 8px var(--green)}
.strip-ng::after{background:var(--red);box-shadow:0 0 8px var(--red)}
.ss-left{display:flex;align-items:center;gap:12px}
.ss-icon{font-size:28px;animation:iconPop 0.4s cubic-bezier(0.34,1.56,0.64,1)}
@keyframes iconPop{from{transform:scale(0);opacity:0}to{transform:scale(1);opacity:1}}
.ss-text{display:flex;flex-direction:column}
.ss-title{font-size:16px;font-weight:700}
.strip-ok .ss-title{color:var(--green)}.strip-ng .ss-title{color:var(--red)}.strip-idle .ss-title{color:var(--text-3)}
.ss-time{font-size:11px;color:var(--text-3)}
.ss-right{display:flex;align-items:center;gap:12px}
.ss-perf{font-size:12px;color:var(--cyan);font-weight:600}
.ss-tag{padding:6px 16px;border-radius:8px;font-size:18px;font-weight:800;background:var(--bg-3);color:var(--accent-2);animation:tagReveal 0.6s cubic-bezier(0.16,1,0.3,1)}
@keyframes tagReveal{from{opacity:0;transform:scale(0.8) translateY(4px)}to{opacity:1;transform:scale(1) translateY(0)}}
.dash-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:16px}
@media(max-width:900px){.dash-grid{grid-template-columns:1fr}}
.right-stack{display:flex;flex-direction:column;gap:16px}
.ocr-area{display:flex;gap:16px}
.img-frame{width:180px;height:130px;border-radius:var(--radius);overflow:hidden;border:1px solid var(--border);flex-shrink:0;background:var(--bg-3);display:flex;align-items:center;justify-content:center}
.det-img{width:100%;height:100%;object-fit:cover;animation:imgReveal 0.5s ease}
@keyframes imgReveal{from{opacity:0;filter:blur(8px);transform:scale(1.05)}to{opacity:1;filter:blur(0);transform:scale(1)}}
.img-ph{font-size:32px;color:var(--text-3)}
.ocr-det{flex:1;display:flex;flex-direction:column;gap:10px;justify-content:center}
.or{display:flex;justify-content:space-between;align-items:center}
.ok{font-size:13px;color:var(--text-3)}
.ov{font-size:14px;font-weight:500}
.ov.hl{font-size:20px;font-weight:800;color:var(--accent-2)}
.defect-row{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}
.dc{display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 4px;border-radius:var(--radius);background:var(--bg-3);border:1px solid var(--border);transition:all 0.35s cubic-bezier(0.4,0,0.2,1)}
.dc:hover{transform:translateY(-2px)}
.dc.active{border-color:rgba(239,68,68,.4);background:rgba(239,68,68,.06);animation:defectPulse 0.5s ease}
@keyframes defectPulse{0%{box-shadow:0 0 0 0 rgba(239,68,68,0.3)}100%{box-shadow:0 0 0 8px rgba(239,68,68,0)}}
.dci{font-size:18px}.dcn{font-size:11px;font-weight:600}.dcs{font-size:10px;color:var(--text-3)}
.dc.active .dcs{color:var(--red);font-weight:600}
.pos-area{display:flex;align-items:center;gap:20px}
.pos-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;width:72px;height:72px}
.pc{background:var(--bg-3);border-radius:4px;border:1px solid var(--border);display:flex;align-items:center;justify-content:center}
.pc.lit{background:rgba(99,102,241,.2);border-color:var(--accent);animation:pcLit 0.4s ease}
@keyframes pcLit{from{background:transparent}to{background:rgba(99,102,241,.2)}}
.pm{width:8px;height:8px;border-radius:50%;background:var(--accent);box-shadow:0 0 8px var(--accent);animation:pmPulse 1.5s ease-in-out infinite}
@keyframes pmPulse{0%,100%{box-shadow:0 0 4px var(--accent)}50%{box-shadow:0 0 12px var(--accent),0 0 20px rgba(99,102,241,0.3)}}
.pos-info{display:flex;flex-direction:column;gap:4px}
.pl{font-size:12px;color:var(--text-3)}.pv{font-size:16px;font-weight:700}
.pv.ok{color:var(--green)}.pv.ng{color:var(--red)}
.see-all{font-size:12px;color:var(--accent-2);font-weight:500}
.see-all:hover{text-decoration:underline}
.tbl-wrap{overflow-x:auto}
.dtable{width:100%;border-collapse:collapse;font-size:13px}
.dtable th{text-align:left;padding:8px 12px;font-size:11px;font-weight:600;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}
.dtable td{padding:9px 12px;border-bottom:1px solid var(--border)}
.tbl-row{transition:background 0.2s}
.tbl-row:hover td{background:rgba(255,255,255,.02)}
.tbl-row td{animation:rowIn 0.3s ease both}
.tbl-row:nth-child(1) td{animation-delay:0.05s}
.tbl-row:nth-child(2) td{animation-delay:0.1s}
.tbl-row:nth-child(3) td{animation-delay:0.15s}
.tbl-row:nth-child(4) td{animation-delay:0.2s}
.tbl-row:nth-child(5) td{animation-delay:0.25s}
@keyframes rowIn{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:translateX(0)}}
.dtable tr:last-child td{border-bottom:none}
.td-m{color:var(--text-3);font-variant-numeric:tabular-nums}
.td-e{text-align:center;color:var(--text-3);padding:28px!important}
</style>