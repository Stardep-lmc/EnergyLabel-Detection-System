<template>
  <view class="page">
    <view class="header">
      <text class="title">数据统计</text>
      <text class="subtitle">最近7天检测数据分析</text>
    </view>

    <view class="stats-grid">
      <view class="stat-card">
        <text class="stat-num">{{ stats.total }}</text>
        <text class="stat-label">总检测数</text>
      </view>
      <view class="stat-card ok">
        <text class="stat-num">{{ stats.passCount }}</text>
        <text class="stat-label">合格数</text>
      </view>
      <view class="stat-card ng">
        <text class="stat-num">{{ stats.failCount }}</text>
        <text class="stat-label">不合格数</text>
      </view>
      <view class="stat-card rate">
        <text class="stat-num">{{ stats.passRate }}%</text>
        <text class="stat-label">合格率</text>
      </view>
    </view>

    <!-- 检测趋势 -->
    <view class="section">
      <text class="section-title">📈 检测趋势</text>
      <view class="trend-chart">
        <view v-for="(day, i) in trendDays" :key="i" class="bar-col">
          <view class="bar-pair">
            <view class="bar bt" :style="{ height: barH(trendTotal[i]) }"></view>
            <view class="bar bd" :style="{ height: barH(trendDefect[i]) }"></view>
          </view>
          <text class="bar-day">{{ day }}</text>
        </view>
      </view>
      <view class="legend">
        <view class="lg"><view class="lg-dot" style="background:#6366f1"></view><text class="lg-text">检测总数</text></view>
        <view class="lg"><view class="lg-dot" style="background:#ef4444"></view><text class="lg-text">缺陷数</text></view>
      </view>
    </view>

    <!-- 缺陷分布 -->
    <view class="section">
      <text class="section-title">🍕 缺陷类型分布</text>
      <view class="dist-list">
        <view v-for="(item, i) in defectDist" :key="i" class="dist-row">
          <text class="dr-name">{{ item.name }}</text>
          <view class="dr-bar-bg">
            <view class="dr-bar" :style="{ width: pct(item.value, defectTotal) + '%' }"></view>
          </view>
          <text class="dr-val">{{ item.value }}</text>
        </view>
        <view v-if="defectDist.length === 0" class="empty-hint"><text style="color:#666">暂无数据</text></view>
      </view>
    </view>

    <!-- 型号合格率 -->
    <view class="section">
      <text class="section-title">📊 各型号合格率</text>
      <view class="rate-list">
        <view v-for="(item, i) in modelRates" :key="i" class="rate-row">
          <text class="rr-model">{{ item.model }}</text>
          <view class="rr-bar-bg">
            <view class="rr-bar" :style="{ width: item.rate + '%' }"></view>
          </view>
          <text class="rr-pct" :class="item.rate >= 90 ? 'c-green' : item.rate >= 70 ? 'c-orange' : 'c-red'">{{ item.rate }}%</text>
        </view>
        <view v-if="modelRates.length === 0" class="empty-hint"><text style="color:#666">暂无数据</text></view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import api from '../../utils/api.js'

const stats = ref({ total: 0, passCount: 0, failCount: 0, passRate: 0 })
const trendDays = ref([])
const trendTotal = ref([])
const trendDefect = ref([])
const defectDist = ref([])
const modelRates = ref([])

const defectTotal = computed(() => defectDist.value.reduce((s, d) => s + d.value, 0) || 1)
const maxV = computed(() => Math.max(1, ...trendTotal.value))
const barH = (v) => Math.max(4, (v / maxV.value) * 200) + 'rpx'
const pct = (v, t) => Math.round((v / t) * 100)

const pad = (n) => String(n).padStart(2, '0')
const fmtD = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const fmtS = (d) => `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const last7 = () => { const r = []; const n = new Date(); for (let i = 6; i >= 0; i--) { const d = new Date(n); d.setDate(n.getDate() - i); r.push(d) } return r }

const fetchStats = async () => {
  const days = last7()
  trendDays.value = days.map(fmtS)
  const start = fmtD(days[0])
  const end = fmtD(days[6])

  try {
    const data = await api.get(`/api/statistic?startDate=${start}&endDate=${end}`)
    const total = (data || []).length
    const passCount = (data || []).filter(d => d.status === 'OK').length
    const failCount = total - passCount
    stats.value = { total, passCount, failCount, passRate: total > 0 ? Math.round(passCount / total * 100) : 0 }

    // 按日期聚合趋势
    const ds = {}
    days.forEach(d => { ds[fmtD(d)] = { total: 0, defects: 0 } })
    const dc = {}
    const ms = {}

    ;(data || []).forEach(item => {
      const dt = item.timestamp ? new Date(item.timestamp) : null
      if (!dt || isNaN(dt.getTime())) return
      const k = fmtD(dt)
      if (ds[k]) { ds[k].total++; if (item.hasDefect) ds[k].defects++ }

      const defect = item.defectType
      if (!defect || defect === '无' || defect === 'none') {
        dc['正常'] = (dc['正常'] || 0) + 1
      } else {
        defect.split(',').forEach(t => { const n = t.trim(); if (n && n !== '无') dc[n] = (dc[n] || 0) + 1 })
      }

      const m = item.presetModel || '未知'
      if (!ms[m]) ms[m] = { total: 0, ok: 0 }
      ms[m].total++
      if (item.status === 'OK') ms[m].ok++
    })

    trendTotal.value = days.map(d => ds[fmtD(d)].total)
    trendDefect.value = days.map(d => ds[fmtD(d)].defects)
    defectDist.value = Object.entries(dc).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
    modelRates.value = Object.entries(ms).map(([model, s]) => ({ model, rate: s.total > 0 ? Math.round(s.ok / s.total * 100) : 0 }))
  } catch { /* ignore */ }
}

onShow(() => { fetchStats() })
</script>

<style scoped>
.page { min-height: 100vh; background: #0a0a1a; padding-bottom: 30rpx; }
.header { padding: 30rpx; }
.title { font-size: 40rpx; font-weight: 700; color: #fff; }
.subtitle { font-size: 22rpx; color: #888; margin-top: 4rpx; display: block; }

.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx; padding: 0 24rpx 24rpx; }
.stat-card { padding: 24rpx; border-radius: 16rpx; background: rgba(15,52,96,.6); border: 1rpx solid rgba(255,255,255,.06); display: flex; flex-direction: column; align-items: center; }
.stat-card.ok { border-color: rgba(16,185,129,.2); }
.stat-card.ng { border-color: rgba(239,68,68,.2); }
.stat-card.rate { border-color: rgba(99,102,241,.2); }
.stat-num { font-size: 44rpx; font-weight: 800; color: #fff; }
.stat-card.ok .stat-num { color: #10b981; }
.stat-card.ng .stat-num { color: #ef4444; }
.stat-card.rate .stat-num { color: #818cf8; }
.stat-label { font-size: 22rpx; color: #888; margin-top: 4rpx; }

.section { margin: 0 24rpx 20rpx; padding: 24rpx; background: rgba(15,52,96,.6); border-radius: 16rpx; border: 1rpx solid rgba(255,255,255,.06); }
.section-title { font-size: 28rpx; font-weight: 600; color: #fff; margin-bottom: 16rpx; display: block; }

.trend-chart { display: flex; align-items: flex-end; gap: 10rpx; height: 240rpx; padding-bottom: 40rpx; }
.bar-col { display: flex; flex-direction: column; align-items: center; flex: 1; }
.bar-pair { display: flex; gap: 4rpx; align-items: flex-end; height: 200rpx; }
.bar { width: 28rpx; border-radius: 6rpx 6rpx 0 0; }
.bt { background: linear-gradient(180deg, #818cf8, #6366f1); }
.bd { background: linear-gradient(180deg, #f87171, #ef4444); }
.bar-day { font-size: 20rpx; color: #888; margin-top: 8rpx; }

.legend { display: flex; gap: 30rpx; margin-top: 8rpx; }
.lg { display: flex; align-items: center; gap: 8rpx; }
.lg-dot { width: 16rpx; height: 16rpx; border-radius: 4rpx; }
.lg-text { font-size: 22rpx; color: #aaa; }

.dist-list { display: flex; flex-direction: column; gap: 12rpx; }
.dist-row { display: flex; align-items: center; gap: 12rpx; }
.dr-name { font-size: 24rpx; color: #aaa; width: 80rpx; }
.dr-bar-bg { flex: 1; height: 16rpx; background: rgba(255,255,255,.05); border-radius: 8rpx; overflow: hidden; }
.dr-bar { height: 100%; background: linear-gradient(90deg, #6366f1, #a855f7); border-radius: 8rpx; }
.dr-val { font-size: 22rpx; color: #818cf8; font-weight: 600; width: 60rpx; text-align: right; }

.rate-list { display: flex; flex-direction: column; gap: 16rpx; }
.rate-row { display: flex; align-items: center; gap: 12rpx; }
.rr-model { font-size: 24rpx; color: #aaa; width: 100rpx; flex-shrink: 0; }
.rr-bar-bg { flex: 1; height: 20rpx; background: rgba(255,255,255,.05); border-radius: 10rpx; overflow: hidden; }
.rr-bar { height: 100%; background: linear-gradient(90deg, #6366f1, #a855f7); border-radius: 10rpx; }
.rr-pct { font-size: 26rpx; font-weight: 800; width: 80rpx; text-align: right; }
.c-green { color: #10b981; }
.c-orange { color: #f59e0b; }
.c-red { color: #ef4444; }

.empty-hint { text-align: center; padding: 30rpx; }
</style>