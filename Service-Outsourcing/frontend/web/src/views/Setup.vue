<template>
  <div>
    <div class="page-header">
      <div class="page-title">系统配置</div>
      <div class="page-subtitle">产品型号、检测参数与相机设置</div>
    </div>
    <div class="page-body">
      <!-- Models -->
      <div class="glass-card">
        <div class="section-head"><span class="section-icon">📋</span> 预设产品型号</div>
        <div class="model-list">
          <div v-for="(item,idx) in presetModels" :key="idx" class="model-row">
            <div class="mr-left">
              <span class="mr-name">{{item.name}}</span>
              <span class="mr-code">{{item.model}}</span>
            </div>
            <div class="mr-right">
              <select v-model="item.standardLabel" class="input-field sm">
                <option v-for="l in energyLevels" :key="l" :value="l">{{l}}</option>
              </select>
              <label class="toggle"><input type="checkbox" v-model="item.enabled"/><span class="track"><span class="thumb"></span></span></label>
              <button class="btn-del" @click="removeModel(idx)" title="删除" :disabled="presetModels.length<=1">✕</button>
            </div>
          </div>
        </div>
        <div class="add-row">
          <input v-model="newModel.name" placeholder="产品名称" class="input-field"/>
          <input v-model="newModel.model" placeholder="产品型号" class="input-field"/>
          <select v-model="newModel.standardLabel" class="input-field sm">
            <option v-for="l in energyLevels" :key="l" :value="l">{{l}}</option>
          </select>
          <button class="btn-primary sm-btn" @click="addModel">+ 添加</button>
        </div>
      </div>

      <!-- Detection params -->
      <div class="glass-card" style="margin-top:16px">
        <div class="section-head"><span class="section-icon">⚙️</span> 检测参数</div>
        <div class="param-stack">
          <div class="param-card">
            <div class="pc-top"><span class="pc-icon">📍</span><div class="pc-info"><span class="pc-name">位置偏移容忍度</span><span class="pc-desc">标签偏离中心多少%算异常</span></div></div>
            <div class="slider-row"><input type="range" v-model.number="positionTolerance" min="0" max="20" step="1" class="slider"/><span class="slider-val">{{positionTolerance}}%</span></div>
          </div>
          <div class="param-card">
            <div class="pc-top"><span class="pc-icon">🔍</span><div class="pc-info"><span class="pc-name">缺陷检测灵敏度</span><span class="pc-desc">越高越容易检出微小缺陷</span></div></div>
            <div class="chip-row"><button v-for="s in sensitivityLevels" :key="s" class="chip" :class="{active:sensitivity===s}" @click="sensitivity=s">{{s}}</button></div>
          </div>
          <div class="param-card">
            <div class="pc-top"><span class="pc-icon">💡</span><div class="pc-info"><span class="pc-name">光照补偿</span><span class="pc-desc">适应不同环境光线</span></div></div>
            <div class="slider-row"><input type="range" v-model.number="lightCompensation" min="-5" max="5" step="1" class="slider"/><span class="slider-val">{{lightCompensation>0?'+':''}}{{lightCompensation}}</span></div>
          </div>
        </div>
      </div>

      <!-- Camera -->
      <div class="glass-card" style="margin-top:16px">
        <div class="section-head"><span class="section-icon">📷</span> 相机参数</div>
        <div class="grid-2">
          <div class="param-card">
            <div class="pc-top"><span class="pc-icon">🔆</span><span class="pc-name">曝光</span></div>
            <div class="slider-row"><input type="range" v-model.number="exposure" min="-3" max="3" step="1" class="slider"/><span class="slider-val">{{exposure>0?'+':''}}{{exposure}}</span></div>
          </div>
          <div class="param-card">
            <div class="pc-top"><span class="pc-icon">📱</span><span class="pc-name">分辨率</span></div>
            <div class="chip-row"><button v-for="r in resolutions" :key="r" class="chip" :class="{active:resolution===r}" @click="resolution=r">{{r}}</button></div>
          </div>
        </div>
      </div>

      <div class="action-row">
        <button class="btn-primary" @click="saveConfig">💾 保存配置</button>
        <button class="btn-ghost" @click="resetConfig">↺ 恢复默认</button>
      </div>

      <!-- Toast -->
      <transition name="toast">
        <div v-if="toast.show" class="toast-bar" :class="toast.type">{{toast.msg}}</div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api, ApiError } from '../api.js'
const energyLevels = ['A++','A+','A','B','C']
const sensitivityLevels = ['低','中','高']
const resolutions = ['640x480','1280x720','1920x1080']
const presetModels = ref([{name:'冰箱',model:'BCD-520W',standardLabel:'A++',enabled:true}])
const newModel = ref({name:'',model:'',standardLabel:'A++'})
const positionTolerance = ref(10), sensitivity = ref('中'), lightCompensation = ref(0)
const exposure = ref(0), resolution = ref('1280x720'), defaultConfig = ref(null)

// Toast
const toast = reactive({show:false,msg:'',type:'info'})
let toastTimer = null
const showToast = (msg, type='info') => {
  clearTimeout(toastTimer)
  toast.msg=msg; toast.type=type; toast.show=true
  toastTimer = setTimeout(()=>{toast.show=false}, 3000)
}

const fetchConfig = async () => {
  try {
    const d = await api.get('/api/config')
    presetModels.value = d.models ?? presetModels.value
    positionTolerance.value = d.positionTolerance ?? 10
    sensitivity.value = d.sensitivity ?? '中'
    lightCompensation.value = d.lightCompensation ?? 0
    exposure.value = d.camera?.exposure ?? 0
    resolution.value = d.camera?.resolution ?? '1280x720'
    defaultConfig.value = JSON.parse(JSON.stringify(d))
  } catch {}
}
const addModel = () => {
  if (!newModel.value.name||!newModel.value.model) return
  presetModels.value.push({...newModel.value,enabled:true})
  newModel.value = {name:'',model:'',standardLabel:'A++'}
}
const removeModel = (idx) => {
  if (presetModels.value.length <= 1) return
  presetModels.value.splice(idx, 1)
}
const saveConfig = async () => {
  const cfg = {models:presetModels.value,positionTolerance:positionTolerance.value,sensitivity:sensitivity.value,lightCompensation:lightCompensation.value,camera:{exposure:exposure.value,resolution:resolution.value}}
  try {
    await api.post('/api/config', cfg)
    defaultConfig.value = JSON.parse(JSON.stringify(cfg))
    // 配置保存后自动重载ML检测器，使灵敏度等参数立即生效
    try { await api.post('/api/ml/reload', {}) } catch {}
    showToast('配置已保存 ✓','ok')
  } catch (e) {
    showToast(e instanceof ApiError ? e.message : '网络请求失败','ng')
  }
}
const resetConfig = () => {
  if (!defaultConfig.value) { showToast('无默认配置可恢复','ng'); return }
  const d = defaultConfig.value
  presetModels.value = JSON.parse(JSON.stringify(d.models))
  positionTolerance.value = d.positionTolerance; sensitivity.value = d.sensitivity
  lightCompensation.value = d.lightCompensation; exposure.value = d.camera.exposure; resolution.value = d.camera.resolution
}
onMounted(() => fetchConfig())
</script>

<style scoped>
.model-list { display:flex; flex-direction:column; gap:6px; margin-bottom:12px; }
.model-row {
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 14px; background:var(--bg-3); border-radius:var(--radius);
  border:1px solid var(--border);
  transition:all 0.3s cubic-bezier(0.4,0,0.2,1);
  opacity:0; animation:modelRowIn 0.4s ease forwards;
}
.model-row:nth-child(1) { animation-delay:0.05s; }
.model-row:nth-child(2) { animation-delay:0.1s; }
.model-row:nth-child(3) { animation-delay:0.15s; }
.model-row:nth-child(4) { animation-delay:0.2s; }
@keyframes modelRowIn { from { opacity:0; transform:translateX(-12px); } to { opacity:1; transform:translateX(0); } }
.model-row:hover { border-color:var(--border-hover); transform:translateX(4px); box-shadow:0 2px 12px rgba(0,0,0,0.1); }
.mr-left { display:flex; flex-direction:column; }
.mr-name { font-size:13px; font-weight:600; }
.mr-code { font-size:11px; color:var(--text-3); }
.mr-right { display:flex; align-items:center; gap:12px; }
.btn-del {
  width:24px; height:24px; border-radius:6px; border:1px solid var(--border);
  background:transparent; color:var(--red); cursor:pointer; font-size:12px;
  display:flex; align-items:center; justify-content:center; transition:all 0.2s; font-family:inherit;
}
.btn-del:hover:not(:disabled) { background:rgba(239,68,68,0.1); border-color:var(--red); }
.btn-del:disabled { opacity:0.2; cursor:not-allowed; }

.input-field.sm { padding:6px 10px; }
.sm-btn { padding:8px 16px; font-size:12px; }

/* Toggle */
.toggle { position:relative; display:inline-flex; cursor:pointer; }
.toggle input { position:absolute; opacity:0; width:0; height:0; }
.track {
  width:36px; height:20px; background:var(--bg-0); border:1px solid var(--border);
  border-radius:20px; position:relative; transition:all 0.35s cubic-bezier(0.4,0,0.2,1);
}
.thumb {
  position:absolute; width:14px; height:14px; border-radius:50%;
  background:var(--text-3); top:2px; left:2px;
  transition:all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toggle input:checked + .track { background:var(--accent); border-color:var(--accent); box-shadow:0 0 10px rgba(99,102,241,0.3); }
.toggle input:checked + .track .thumb { transform:translateX(16px); background:#fff; box-shadow:0 0 6px rgba(255,255,255,0.4); }

.add-row {
  display:flex; gap:8px; padding:12px; background:var(--bg-3);
  border-radius:var(--radius); border:1px dashed var(--border);
  transition:all 0.3s;
}
.add-row:hover { border-color:var(--accent); background:rgba(99,102,241,0.03); }

.param-stack { display:flex; flex-direction:column; gap:10px; }
.param-card {
  padding:14px; background:var(--bg-3); border-radius:var(--radius);
  border:1px solid var(--border);
  transition:all 0.3s cubic-bezier(0.4,0,0.2,1);
  opacity:0; animation:paramIn 0.4s ease forwards;
}
.param-card:nth-child(1) { animation-delay:0.05s; }
.param-card:nth-child(2) { animation-delay:0.1s; }
.param-card:nth-child(3) { animation-delay:0.15s; }
@keyframes paramIn { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
.param-card:hover { border-color:var(--border-hover); transform:translateY(-2px); box-shadow:0 4px 16px rgba(0,0,0,0.1); }
.pc-top { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.pc-icon { font-size:18px; }
.pc-info { display:flex; flex-direction:column; }
.pc-name { font-size:13px; font-weight:600; }
.pc-desc { font-size:10px; color:var(--text-3); }

.slider-row { display:flex; align-items:center; gap:12px; }
.slider {
  flex:1; -webkit-appearance:none; height:5px; border-radius:3px;
  background:var(--bg-0); outline:none;
  transition:background 0.3s;
}
.slider::-webkit-slider-thumb {
  -webkit-appearance:none; width:18px; height:18px; border-radius:50%;
  background:var(--accent); cursor:pointer; border:2px solid var(--bg-2);
  box-shadow:0 0 8px rgba(99,102,241,0.4);
  transition:all 0.2s;
}
.slider::-webkit-slider-thumb:hover {
  transform:scale(1.2);
  box-shadow:0 0 14px rgba(99,102,241,0.5);
}
.slider:active::-webkit-slider-thumb {
  box-shadow:0 0 20px rgba(99,102,241,0.6);
}
.slider-val {
  min-width:36px; text-align:right; font-size:15px; font-weight:700; color:var(--accent-2);
  transition:transform 0.2s;
}
.param-card:hover .slider-val { transform:scale(1.05); }

.chip-row { display:flex; gap:6px; }
.chip {
  padding:6px 16px; border-radius:20px; font-size:12px; cursor:pointer;
  background:var(--bg-0); border:1px solid var(--border);
  color:var(--text-2); transition:all 0.3s cubic-bezier(0.4,0,0.2,1); font-family:inherit;
}
.chip:hover { border-color:var(--border-hover); transform:translateY(-1px); }
.chip.active {
  background:linear-gradient(135deg,var(--accent),var(--purple)); color:#fff; border-color:transparent;
  box-shadow:0 4px 12px rgba(99,102,241,0.3);
  transform:scale(1.05);
}

.action-row { display:flex; gap:12px; margin-top:20px; animation:actionIn 0.4s ease 0.2s both; }
@keyframes actionIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.action-row .btn-primary { flex:2; }
.action-row .btn-ghost { flex:1; }

/* Toast */
.toast-bar{position:fixed;top:20px;right:20px;padding:12px 24px;border-radius:10px;font-size:13px;font-weight:600;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.3)}
.toast-bar.ok{background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.3);color:var(--green)}
.toast-bar.ng{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);color:var(--red)}
.toast-bar.info{background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);color:var(--accent-2)}
.toast-enter-active{animation:toastIn .3s ease}
.toast-leave-active{animation:toastOut .3s ease}
@keyframes toastIn{from{opacity:0;transform:translateY(-12px)}to{opacity:1;transform:translateY(0)}}
@keyframes toastOut{from{opacity:1}to{opacity:0;transform:translateY(-12px)}}
</style>