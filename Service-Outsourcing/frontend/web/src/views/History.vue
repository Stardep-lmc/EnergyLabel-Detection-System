<template>
  <div>
    <div class="page-header" style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <div class="page-title">历史记录</div>
        <div class="page-subtitle">检测记录查询与筛选</div>
      </div>
      <div class="count-chip">共 {{ total }} 条</div>
    </div>
    <div class="page-body">
      <div class="glass-card filter-strip">
        <div class="fg"><label class="fl">开始日期</label><input type="date" v-model="startDate" class="input-field" /></div>
        <div class="fg"><label class="fl">结束日期</label><input type="date" v-model="endDate" class="input-field" /></div>
        <div class="fg">
          <label class="fl">状态</label>
          <select v-model="statusFilter" class="input-field">
            <option value="ALL">全部</option><option value="OK">合格</option><option value="NG">不合格</option>
          </select>
        </div>
        <button class="btn-primary" @click="page=1;fetchHistory()">🔍 查询</button>
        <button class="btn-ghost" @click="exportCSV">📥 导出CSV</button>
      </div>

      <div v-if="errMsg" class="err-msg">{{errMsg}}</div>
      <div v-if="loading" class="loading-text">加载中...</div>
      <div class="records-grid">
        <div v-for="(item,idx) in records" :key="idx" class="glass-card rec-card">
          <div class="rec-top">
            <span class="rec-time">{{ item.timestamp }}</span>
            <span class="badge" :class="item.status==='OK'?'badge-ok':'badge-ng'">{{ item.status==='OK'?'✓ 合格':'✗ 不合格' }}</span>
          </div>
          <div class="rec-body">
            <div class="rec-thumb-wrap">
              <img v-if="item.imageUrl" :src="item.imageUrl" class="rec-thumb" />
              <div v-else class="rec-thumb ph">📷</div>
            </div>
            <div class="rec-info">
              <div class="ri"><span class="ri-k">型号</span><span class="ri-v">{{ item.presetModel }}</span></div>
              <div class="ri"><span class="ri-k">标签</span><span class="ri-v">{{ item.ocrText }}</span></div>
              <div class="ri"><span class="ri-k">缺陷</span><span class="ri-v">{{ item.defectType||'无' }}</span></div>
              <div class="ri"><span class="ri-k">位置</span><span class="ri-v">{{ item.positionStatus }}</span></div>
            </div>
          </div>
        </div>
        <div v-if="records.length===0" class="glass-card empty-card">暂无记录</div>
      </div>

      <div class="pager" v-if="totalPages>1">
        <button class="btn-ghost pg-btn" :disabled="page<=1" @click="page--;fetchHistory()">← 上一页</button>
        <div class="pg-nums">
          <button v-for="p in visiblePages" :key="p" class="pg-num" :class="{active:p===page}" @click="page=p;fetchHistory()">{{ p }}</button>
        </div>
        <button class="btn-ghost pg-btn" :disabled="page>=totalPages" @click="page++;fetchHistory()">下一页 →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api, ApiError } from '../api.js'
const startDate = ref(''), endDate = ref(''), statusFilter = ref('ALL')
const page = ref(1), pageSize = 12, total = ref(0), records = ref([]), totalPages = ref(1)
const errMsg = ref(''), loading = ref(false)
const visiblePages = computed(() => {
  const s = Math.max(1, page.value - 2), e = Math.min(totalPages.value, s + 4), r = []
  for (let i = s; i <= e; i++) r.push(i)
  return r
})
const exportCSV = () => {
  const p = new URLSearchParams({ statusFilter: statusFilter.value })
  if (startDate.value) p.append('startDate', startDate.value)
  if (endDate.value) p.append('endDate', endDate.value)
  window.open(`/api/export/csv?${p}`, '_blank')
}
const fetchHistory = async () => {
  loading.value = true
  errMsg.value = ''
  try {
    const p = new URLSearchParams({ page: page.value, pageSize, statusFilter: statusFilter.value })
    if (startDate.value) p.append('startDate', startDate.value)
    if (endDate.value) p.append('endDate', endDate.value)
    const d = await api.get(`/api/history?${p}`)
    total.value = d.total; records.value = d.records; totalPages.value = Math.max(1, Math.ceil(d.total / pageSize))
  } catch (e) {
    errMsg.value = e instanceof ApiError ? e.message : '网络错误: ' + e.message
  } finally {
    loading.value = false
  }
}
onMounted(() => fetchHistory())
</script>

<style scoped>
.count-chip {
  padding:5px 14px; border-radius:20px; font-size:12px; font-weight:600;
  background:var(--bg-2); border:1px solid var(--border); color:var(--text-3);
}
.filter-strip { display:flex; align-items:flex-end; gap:12px; flex-wrap:wrap; margin-bottom:16px; animation:filterIn 0.4s ease; }
@keyframes filterIn { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:translateY(0); } }
.fg { display:flex; flex-direction:column; gap:4px; }
.fl { font-size:10px; color:var(--text-3); text-transform:uppercase; letter-spacing:0.5px; font-weight:600; }

.records-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:12px; }
.rec-card {
  padding:16px;
  opacity:0; animation:recCardIn 0.45s cubic-bezier(0.16,1,0.3,1) forwards;
  cursor:default;
}
.rec-card:nth-child(1) { animation-delay:0.03s; }
.rec-card:nth-child(2) { animation-delay:0.06s; }
.rec-card:nth-child(3) { animation-delay:0.09s; }
.rec-card:nth-child(4) { animation-delay:0.12s; }
.rec-card:nth-child(5) { animation-delay:0.15s; }
.rec-card:nth-child(6) { animation-delay:0.18s; }
.rec-card:nth-child(7) { animation-delay:0.21s; }
.rec-card:nth-child(8) { animation-delay:0.24s; }
.rec-card:nth-child(9) { animation-delay:0.27s; }
.rec-card:nth-child(10) { animation-delay:0.3s; }
.rec-card:nth-child(11) { animation-delay:0.33s; }
.rec-card:nth-child(12) { animation-delay:0.36s; }
@keyframes recCardIn { from { opacity:0; transform:translateY(16px) scale(0.97); } to { opacity:1; transform:translateY(0) scale(1); } }
.rec-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
.rec-time { font-size:11px; color:var(--text-3); font-variant-numeric:tabular-nums; }
.rec-body { display:flex; gap:14px; }
.rec-thumb-wrap {
  width:80px; height:60px; border-radius:8px; overflow:hidden;
  border:1px solid var(--border); flex-shrink:0; background:var(--bg-3);
  transition:transform 0.3s, box-shadow 0.3s;
}
.rec-card:hover .rec-thumb-wrap { transform:scale(1.05); box-shadow:0 4px 12px rgba(0,0,0,0.2); }
.rec-thumb { width:100%; height:100%; object-fit:cover; transition:transform 0.4s; }
.rec-card:hover .rec-thumb { transform:scale(1.08); }
.ph { display:flex; align-items:center; justify-content:center; font-size:20px; width:100%; height:100%; }
.rec-info { flex:1; display:flex; flex-direction:column; gap:3px; }
.ri { display:flex; justify-content:space-between; font-size:12px; transition:transform 0.2s; }
.rec-card:hover .ri { transform:translateX(2px); }
.ri-k { color:var(--text-3); }
.ri-v { font-weight:500; }
.empty-card { text-align:center; color:var(--text-3); padding:40px; }
.err-msg { margin-bottom:12px; padding:10px 14px; border-radius:8px; background:rgba(239,68,68,.08); color:var(--red); font-size:13px; }
.loading-text { text-align:center; color:var(--text-3); padding:20px; font-size:13px; }

.pager { display:flex; justify-content:center; align-items:center; gap:8px; margin-top:20px; animation:pagerIn 0.4s ease 0.3s both; }
@keyframes pagerIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.pg-btn { padding:7px 16px; font-size:12px; transition:all 0.2s; }
.pg-btn:hover:not(:disabled) { transform:translateX(-2px); }
.pg-btn:last-child:hover:not(:disabled) { transform:translateX(2px); }
.pg-btn:disabled { opacity:0.3; cursor:not-allowed; }
.pg-nums { display:flex; gap:4px; }
.pg-num {
  width:32px; height:32px; display:flex; align-items:center; justify-content:center;
  background:var(--bg-2); border:1px solid var(--border); border-radius:8px;
  color:var(--text-2); font-size:12px; cursor:pointer;
  transition:all 0.25s cubic-bezier(0.4,0,0.2,1);
}
.pg-num:hover { border-color:var(--border-hover); transform:translateY(-2px); }
.pg-num.active {
  background:linear-gradient(135deg,var(--accent),var(--purple)); color:#fff; border-color:transparent;
  box-shadow:0 4px 12px rgba(99,102,241,0.3);
  transform:scale(1.05);
}
</style>