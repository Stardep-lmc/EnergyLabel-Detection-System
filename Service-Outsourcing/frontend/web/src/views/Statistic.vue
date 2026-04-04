<template>
  <div>
    <div class="page-header">
      <div class="page-title">统计报表</div>
      <div class="page-subtitle">最近7天检测数据分析</div>
    </div>
    <div class="page-body">
      <!-- Trend chart -->
      <div class="glass-card">
        <div class="section-head"><span class="section-icon">📈</span> 检测趋势</div>
        <div class="chart-box">
          <div class="bar-chart">
            <div v-for="(day,i) in trendDays" :key="i" class="bar-col">
              <div class="bar-pair">
                <div class="bar bt" :style="{height:barH(trendTotal[i])}"><span class="bar-num" v-if="trendTotal[i]">{{trendTotal[i]}}</span></div>
                <div class="bar bd" :style="{height:barH(trendDefect[i])}"><span class="bar-num" v-if="trendDefect[i]">{{trendDefect[i]}}</span></div>
              </div>
              <span class="bar-day">{{day}}</span>
            </div>
          </div>
          <div class="legend"><span class="lg"><span class="lg-dot" style="background:var(--accent)"></span>检测总数</span><span class="lg"><span class="lg-dot" style="background:var(--red)"></span>缺陷数</span></div>
        </div>
      </div>

      <div class="grid-2" style="margin-top:16px">
        <!-- Defect distribution -->
        <div class="glass-card">
          <div class="section-head"><span class="section-icon">🍕</span> 缺陷类型分布</div>
          <div class="dist-list">
            <div v-for="(item,i) in defectDist" :key="i" class="dist-row">
              <div class="dr-left"><span class="dr-dot" :style="{background:pieC[i]}"></span><span class="dr-name">{{item.name}}</span></div>
              <div class="dr-right"><div class="dr-bar-bg"><div class="dr-bar" :style="{width:pct(item.value,defectTotal)+'%',background:pieC[i]}"></div></div><span class="dr-val">{{item.value}}</span></div>
            </div>
          </div>
        </div>
        <!-- Position distribution -->
        <div class="glass-card">
          <div class="section-head"><span class="section-icon">📍</span> 位置缺陷分布</div>
          <div class="dist-list">
            <div v-for="(item,i) in posDist" :key="i" class="dist-row">
              <div class="dr-left"><span class="dr-dot" :style="{background:posC[i]}"></span><span class="dr-name">{{item.name}}</span></div>
              <div class="dr-right"><div class="dr-bar-bg"><div class="dr-bar" :style="{width:pct(item.value,posTotal)+'%',background:posC[i]}"></div></div><span class="dr-val">{{item.value}}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pass rate -->
      <div class="glass-card" style="margin-top:16px">
        <div class="section-head"><span class="section-icon">📊</span> 各型号合格率</div>
        <div class="rate-list">
          <div v-for="(item,i) in modelRates" :key="i" class="rate-row">
            <span class="rr-model">{{item.model}}</span>
            <div class="rr-bar-bg"><div class="rr-bar" :style="{width:item.rate+'%'}"></div></div>
            <span class="rr-pct" :class="item.rate>=90?'c-green':item.rate>=70?'c-orange':'c-red'">{{item.rate}}%</span>
          </div>
          <div v-if="modelRates.length===0" class="empty-text">暂无数据</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
const trendDays = ref([]), trendTotal = ref([]), trendDefect = ref([])
const defectDist = ref([]), posDist = ref([]), modelRates = ref([])
const pieC = ['#6366f1','#ef4444','#f59e0b','#10b981']
const posC = ['#10b981','#ef4444','#f59e0b','#6366f1','#a855f7']
const defectTotal = computed(() => defectDist.value.reduce((s,d) => s+d.value, 0) || 1)
const posTotal = computed(() => posDist.value.reduce((s,d) => s+d.value, 0) || 1)
const maxV = computed(() => Math.max(1, ...trendTotal.value))
const barH = (v) => Math.max(2, (v/maxV.value)*140) + 'px'
const pct = (v, t) => Math.round((v/t)*100)
const pad = (n) => String(n).padStart(2,'0')
const fmtD = (d) => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`
const fmtS = (d) => `${pad(d.getMonth()+1)}-${pad(d.getDate())}`
const last7 = () => { const r=[],n=new Date(); for(let i=6;i>=0;i--){const d=new Date(n);d.setDate(n.getDate()-i);r.push(d)} return r }

onMounted(async () => {
  const days = last7()
  trendDays.value = days.map(fmtS)
  const start = fmtD(days[0]), end = fmtD(days[6])
  try {
    // fix B2: 优先使用 SQL 聚合接口，避免全量加载 ORM 对象
    const agg = await api.get(`/api/statistic/aggregated?startDate=${start}&endDate=${end}`)
    // 趋势数据
    const ds = {}; days.forEach(d => { ds[fmtD(d)] = {total:0,defects:0} })
    ;(agg.trend || []).forEach(t => { if (ds[t.day]) { ds[t.day].total = t.total; ds[t.day].defects = t.defects } })
    trendTotal.value = days.map(d => ds[fmtD(d)].total)
    trendDefect.value = days.map(d => ds[fmtD(d)].defects)
    // 缺陷分布
    const dc = {}
    Object.entries(agg.defect_distribution || {}).forEach(([k, v]) => {
      if (!k || k === '无' || k === '' || k === 'none' || k === 'normal') { dc['正常'] = (dc['正常'] || 0) + v }
      else { k.split(',').forEach(d => { const t = d.trim(); if (t && t !== '无') dc[t] = (dc[t] || 0) + v }) }
    })
    defectDist.value = Object.entries(dc).map(([name,value]) => ({name,value})).sort((a,b) => b.value - a.value)
    // 位置分布 — 从趋势数据无法直接获取，暂用缺陷分布中的偏移项
    const pc = {}
    Object.entries(agg.defect_distribution || {}).forEach(([k, v]) => {
      if (k && (k.includes('偏移') || k.toLowerCase().includes('offset'))) pc['偏移'] = (pc['偏移'] || 0) + v
      else pc['正常'] = (pc['正常'] || 0) + v
    })
    posDist.value = Object.entries(pc).map(([name,value]) => ({name,value})).sort((a,b) => b.value - a.value)
    // 型号合格率
    modelRates.value = (agg.model_rates || []).map(r => ({model: r.model, rate: r.rate}))
  } catch {
    // 降级：使用旧的全量接口
    try {
      const data = await api.get(`/api/statistic?startDate=${start}&endDate=${end}`)
      const ds = {}; days.forEach(d => { ds[fmtD(d)] = {total:0,defects:0} })
      const dc = {}, pc = {}, ms = {}
      data.forEach(item => {
        // fix B6: 后端返回 UTC 时间无 Z 后缀，强制追加以避免时区偏移
        const raw = item.timestamp || ''
        const dt = new Date(raw.includes('T') || raw.includes('Z') ? raw : raw + 'Z')
        if (isNaN(dt.getTime())) return
        const k = fmtD(dt)
        if (ds[k]) { ds[k].total++; if (item.hasDefect === true) ds[k].defects++ }
        const defect = item.defectType
        if (!defect || defect === '无' || defect === 'none' || defect === 'normal') dc['正常'] = (dc['正常'] || 0) + 1
        else defect.split(',').forEach(d => { const t = d.trim(); if (t && t !== '无') dc[t] = (dc[t] || 0) + 1 })
        if (item.positionStatus) pc[item.positionStatus] = (pc[item.positionStatus] || 0) + 1
        const m = item.presetModel||'未知'; if (!ms[m]) ms[m] = {total:0,ok:0}; ms[m].total++; if (item.status==='OK') ms[m].ok++
      })
      trendTotal.value = days.map(d => ds[fmtD(d)].total)
      trendDefect.value = days.map(d => ds[fmtD(d)].defects)
      defectDist.value = Object.entries(dc).map(([name,value]) => ({name,value})).sort((a,b) => b.value - a.value)
      posDist.value = Object.entries(pc).map(([name,value]) => ({name,value})).sort((a,b) => b.value - a.value)
      modelRates.value = Object.entries(ms).map(([model,s]) => ({model, rate: s.total>0 ? Math.round((s.ok/s.total)*100) : 0}))
    } catch {}
  }
})
</script>

<style scoped>
.chart-box { padding:8px 0; }
.bar-chart { display:flex; align-items:flex-end; gap:10px; height:180px; padding-bottom:28px; }
.bar-col { display:flex; flex-direction:column; align-items:center; flex:1; }
.bar-pair { display:flex; gap:3px; align-items:flex-end; height:140px; }
.bar {
  width:20px; border-radius:4px 4px 0 0; position:relative;
  transition:height 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
  transform-origin:bottom;
  animation:barGrow 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes barGrow { from { transform:scaleY(0); } to { transform:scaleY(1); } }
.bar-col:nth-child(1) .bar { animation-delay:0.05s; }
.bar-col:nth-child(2) .bar { animation-delay:0.1s; }
.bar-col:nth-child(3) .bar { animation-delay:0.15s; }
.bar-col:nth-child(4) .bar { animation-delay:0.2s; }
.bar-col:nth-child(5) .bar { animation-delay:0.25s; }
.bar-col:nth-child(6) .bar { animation-delay:0.3s; }
.bar-col:nth-child(7) .bar { animation-delay:0.35s; }
.bt { background:linear-gradient(180deg, var(--accent-2), var(--accent)); }
.bt:hover { filter:brightness(1.2); box-shadow:0 0 12px rgba(99,102,241,0.3); }
.bd { background:linear-gradient(180deg, #f87171, var(--red)); }
.bd:hover { filter:brightness(1.2); box-shadow:0 0 12px rgba(239,68,68,0.3); }
.bar-num {
  position:absolute; top:-18px; left:50%; transform:translateX(-50%);
  font-size:10px; color:var(--text-3); white-space:nowrap; font-weight:600;
  opacity:0; animation:numFade 0.4s ease 0.8s forwards;
}
@keyframes numFade { to { opacity:1; } }
.bar-day { font-size:11px; color:var(--text-3); margin-top:6px; }
.legend { display:flex; gap:20px; margin-top:4px; }
.lg { display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text-2); }
.lg-dot { width:10px; height:10px; border-radius:3px; }

.dist-list { display:flex; flex-direction:column; gap:10px; }
.dist-row {
  display:flex; align-items:center; gap:8px;
  opacity:0; animation:distRowIn 0.4s ease forwards;
}
.dist-row:nth-child(1) { animation-delay:0.1s; }
.dist-row:nth-child(2) { animation-delay:0.15s; }
.dist-row:nth-child(3) { animation-delay:0.2s; }
.dist-row:nth-child(4) { animation-delay:0.25s; }
.dist-row:nth-child(5) { animation-delay:0.3s; }
@keyframes distRowIn { from { opacity:0; transform:translateX(-12px); } to { opacity:1; transform:translateX(0); } }
.dr-left { display:flex; align-items:center; gap:8px; width:56px; flex-shrink:0; }
.dr-dot { width:8px; height:8px; border-radius:3px; flex-shrink:0; transition:transform 0.3s; }
.dist-row:hover .dr-dot { transform:scale(1.4); }
.dr-name { font-size:12px; color:var(--text-2); }
.dr-right { flex:1; display:flex; align-items:center; gap:8px; }
.dr-bar-bg { flex:1; height:8px; background:var(--bg-3); border-radius:4px; overflow:hidden; }
.dr-bar {
  height:100%; border-radius:4px;
  transition:width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
  position:relative;
}
.dr-bar::after {
  content:''; position:absolute; top:0; right:0; bottom:0; width:20px;
  background:linear-gradient(90deg, transparent, rgba(255,255,255,0.15));
  border-radius:0 4px 4px 0;
}
.dr-val { width:28px; text-align:right; font-size:13px; font-weight:700; }

.rate-list { display:flex; flex-direction:column; gap:12px; }
.rate-row {
  display:flex; align-items:center; gap:12px;
  opacity:0; animation:rateRowIn 0.5s ease forwards;
  transition:transform 0.2s;
}
.rate-row:hover { transform:translateX(4px); }
.rate-row:nth-child(1) { animation-delay:0.1s; }
.rate-row:nth-child(2) { animation-delay:0.18s; }
.rate-row:nth-child(3) { animation-delay:0.26s; }
.rate-row:nth-child(4) { animation-delay:0.34s; }
@keyframes rateRowIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.rr-model { width:56px; font-size:12px; color:var(--text-2); flex-shrink:0; }
.rr-bar-bg { flex:1; height:12px; background:var(--bg-3); border-radius:6px; overflow:hidden; position:relative; }
.rr-bar {
  height:100%; border-radius:6px;
  background:linear-gradient(90deg,var(--accent),var(--purple));
  transition:width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
  position:relative;
}
.rr-bar::after {
  content:''; position:absolute; inset:0;
  background:linear-gradient(90deg, transparent 60%, rgba(255,255,255,0.1));
  border-radius:6px;
}
.rr-pct { width:42px; text-align:right; font-size:14px; font-weight:800; }
.c-green { color:var(--green); }
.c-orange { color:var(--orange); }
.c-red { color:var(--red); }
.empty-text { text-align:center; color:var(--text-3); padding:20px; font-size:13px; }
</style>