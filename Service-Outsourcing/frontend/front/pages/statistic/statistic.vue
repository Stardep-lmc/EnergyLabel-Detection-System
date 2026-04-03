<template>
  <view class="page">
    <view class="header">
      <text class="title">数据统计</text>
      <text class="subtitle">检测数据分析</text>
    </view>

    <view class="stats-grid">
      <view class="stat-card">
        <text class="stat-num">{{stats.total}}</text>
        <text class="stat-label">总检测数</text>
      </view>
      <view class="stat-card ok">
        <text class="stat-num">{{stats.passCount}}</text>
        <text class="stat-label">合格数</text>
      </view>
      <view class="stat-card ng">
        <text class="stat-num">{{stats.failCount}}</text>
        <text class="stat-label">不合格数</text>
      </view>
      <view class="stat-card rate">
        <text class="stat-num">{{stats.passRate}}%</text>
        <text class="stat-label">合格率</text>
      </view>
    </view>

    <view class="section">
      <text class="section-title">缺陷分布</text>
      <view class="defect-list">
        <view v-for="(item,idx) in defectDist" :key="idx" class="defect-row">
          <text class="defect-name">{{item.name}}</text>
          <view class="defect-bar-bg">
            <view class="defect-bar" :style="{width: item.pct + '%'}"></view>
          </view>
          <text class="defect-count">{{item.count}}</text>
        </view>
        <view v-if="defectDist.length===0" class="empty-hint">
          <text class="empty-text">暂无数据</text>
        </view>
      </view>
    </view>

    <view class="section">
      <text class="section-title">最近趋势</text>
      <view class="trend-list">
        <view v-for="(item,idx) in trendData" :key="idx" class="trend-row">
          <text class="trend-time">{{item.timestamp?.slice(0,10)}}</text>
          <text class="trend-status" :class="item.status==='OK'?'ok':'ng'">{{item.status}}</text>
          <text class="trend-defect">{{item.defectType||'无'}}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      stats: { total: 0, passCount: 0, failCount: 0, passRate: 0 },
      defectDist: [],
      trendData: [],
    }
  },
  onShow() {
    this.fetchStats()
  },
  methods: {
    async fetchStats() {
      try {
        const res = await uni.request({ url: '/api/statistic', method: 'GET' })
        if (res.statusCode === 200) {
          const data = res.data || []
          const total = data.length
          const passCount = data.filter(d => d.status === 'OK').length
          const failCount = total - passCount
          this.stats = {
            total,
            passCount,
            failCount,
            passRate: total > 0 ? Math.round(passCount / total * 100) : 0
          }

          // 缺陷分布
          const defectMap = {}
          data.forEach(d => {
            if (d.hasDefect && d.defectType) {
              d.defectType.split(',').forEach(t => {
                const name = t.trim()
                if (name && name !== '无') {
                  defectMap[name] = (defectMap[name] || 0) + 1
                }
              })
            }
          })
          const maxCount = Math.max(...Object.values(defectMap), 1)
          this.defectDist = Object.entries(defectMap)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => ({
              name,
              count,
              pct: Math.round(count / maxCount * 100)
            }))

          // 最近趋势（取最后20条）
          this.trendData = data.slice(-20).reverse()
        }
      } catch (e) {
        console.error(e)
      }
    }
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #0a0a1a; padding-bottom: 30rpx; }
.header { padding: 30rpx; }
.title { font-size: 40rpx; font-weight: 700; color: #fff; }
.subtitle { font-size: 22rpx; color: #888; margin-top: 4rpx; }

.stats-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 16rpx; padding: 0 24rpx 24rpx;
}
.stat-card {
  padding: 24rpx; border-radius: 16rpx;
  background: rgba(15,52,96,.6); border: 1rpx solid rgba(255,255,255,.06);
  display: flex; flex-direction: column; align-items: center;
}
.stat-card.ok { border-color: rgba(16,185,129,.2); }
.stat-card.ng { border-color: rgba(239,68,68,.2); }
.stat-card.rate { border-color: rgba(99,102,241,.2); }
.stat-num { font-size: 44rpx; font-weight: 800; color: #fff; }
.stat-card.ok .stat-num { color: #10b981; }
.stat-card.ng .stat-num { color: #ef4444; }
.stat-card.rate .stat-num { color: #818cf8; }
.stat-label { font-size: 22rpx; color: #888; margin-top: 4rpx; }

.section {
  margin: 0 24rpx 20rpx; padding: 24rpx;
  background: rgba(15,52,96,.6); border-radius: 16rpx;
  border: 1rpx solid rgba(255,255,255,.06);
}
.section-title { font-size: 28rpx; font-weight: 600; color: #fff; margin-bottom: 16rpx; }

.defect-list { display: flex; flex-direction: column; gap: 12rpx; }
.defect-row { display: flex; align-items: center; gap: 12rpx; }
.defect-name { font-size: 24rpx; color: #aaa; width: 80rpx; }
.defect-bar-bg {
  flex: 1; height: 16rpx; background: rgba(255,255,255,.05);
  border-radius: 8rpx; overflow: hidden;
}
.defect-bar {
  height: 100%; background: linear-gradient(90deg, #6366f1, #a855f7);
  border-radius: 8rpx; transition: width 0.3s;
}
.defect-count { font-size: 22rpx; color: #818cf8; font-weight: 600; width: 60rpx; text-align: right; }

.trend-list { display: flex; flex-direction: column; gap: 8rpx; }
.trend-row { display: flex; justify-content: space-between; padding: 8rpx 0; border-bottom: 1rpx solid rgba(255,255,255,.04); }
.trend-time { font-size: 22rpx; color: #888; }
.trend-status { font-size: 22rpx; font-weight: 600; }
.trend-status.ok { color: #10b981; }
.trend-status.ng { color: #ef4444; }
.trend-defect { font-size: 22rpx; color: #aaa; }

.empty-hint { text-align: center; padding: 30rpx; }
.empty-text { font-size: 24rpx; color: #666; }
</style>