<template>
  <view class="page">
    <view class="header">
      <text class="title">历史记录</text>
      <text class="subtitle">检测记录查询</text>
    </view>

    <view class="filter-bar">
      <picker mode="selector" :range="statusOptions" :value="statusIdx" @change="onStatusChange">
        <view class="filter-btn">{{statusOptions[statusIdx]}} ▾</view>
      </picker>
      <view class="count">共 {{total}} 条</view>
    </view>

    <scroll-view scroll-y class="list-area" @scrolltolower="loadMore">
      <view v-for="(item,idx) in records" :key="idx" class="record-card">
        <view class="rc-top">
          <text class="rc-time">{{item.timestamp}}</text>
          <text class="rc-badge" :class="item.status==='OK'?'ok':'ng'">{{item.status==='OK'?'合格':'不合格'}}</text>
        </view>
        <view class="rc-body">
          <view class="rc-row">
            <text class="rc-label">型号</text>
            <text class="rc-val">{{item.presetModel||'--'}}</text>
          </view>
          <view class="rc-row">
            <text class="rc-label">标签</text>
            <text class="rc-val">{{item.ocrText||'--'}}</text>
          </view>
          <view class="rc-row">
            <text class="rc-label">缺陷</text>
            <text class="rc-val">{{item.defectType||'无'}}</text>
          </view>
          <view class="rc-row">
            <text class="rc-label">位置</text>
            <text class="rc-val" :class="item.positionStatus==='正常'?'val-ok':'val-ng'">{{item.positionStatus}}</text>
          </view>
        </view>
      </view>

      <view v-if="records.length===0" class="empty">
        <text class="empty-icon">📋</text>
        <text class="empty-text">暂无记录</text>
      </view>

      <view v-if="loading" class="loading-bar">
        <text class="loading-text">加载中...</text>
      </view>
    </scroll-view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      statusOptions: ['全部', '合格', '不合格'],
      statusIdx: 0,
      statusMap: ['ALL', 'OK', 'NG'],
      records: [],
      total: 0,
      page: 1,
      pageSize: 20,
      loading: false,
      hasMore: true,
    }
  },
  onShow() {
    this.page = 1
    this.records = []
    this.fetchHistory()
  },
  methods: {
    onStatusChange(e) {
      this.statusIdx = e.detail.value
      this.page = 1
      this.records = []
      this.fetchHistory()
    },
    async fetchHistory() {
      if (this.loading) return
      this.loading = true
      try {
        const params = `page=${this.page}&pageSize=${this.pageSize}&statusFilter=${this.statusMap[this.statusIdx]}`
        const res = await uni.request({ url: `/api/history?${params}`, method: 'GET' })
        if (res.statusCode === 200) {
          const d = res.data
          this.total = d.total
          if (this.page === 1) {
            this.records = d.records || []
          } else {
            this.records = [...this.records, ...(d.records || [])]
          }
          this.hasMore = this.records.length < d.total
        }
      } catch (e) {
        console.error(e)
      }
      this.loading = false
    },
    loadMore() {
      if (!this.hasMore || this.loading) return
      this.page++
      this.fetchHistory()
    }
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #0a0a1a; padding: 0 0 20rpx; }
.header { padding: 30rpx; }
.title { font-size: 40rpx; font-weight: 700; color: #fff; }
.subtitle { font-size: 22rpx; color: #888; margin-top: 4rpx; }

.filter-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 30rpx 20rpx;
}
.filter-btn {
  padding: 10rpx 24rpx; border-radius: 30rpx; font-size: 24rpx;
  background: rgba(99,102,241,.1); border: 1rpx solid rgba(99,102,241,.25);
  color: #818cf8;
}
.count { font-size: 22rpx; color: #888; }

.list-area { height: calc(100vh - 240rpx); }

.record-card {
  margin: 0 24rpx 16rpx; padding: 24rpx;
  background: rgba(15,52,96,.6); border-radius: 16rpx;
  border: 1rpx solid rgba(255,255,255,.06);
}
.rc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16rpx; }
.rc-time { font-size: 22rpx; color: #888; }
.rc-badge {
  padding: 4rpx 16rpx; border-radius: 20rpx; font-size: 20rpx; font-weight: 600;
}
.rc-badge.ok { background: rgba(16,185,129,.1); color: #10b981; }
.rc-badge.ng { background: rgba(239,68,68,.1); color: #ef4444; }

.rc-body { display: flex; flex-direction: column; gap: 8rpx; }
.rc-row { display: flex; justify-content: space-between; }
.rc-label { font-size: 24rpx; color: #888; }
.rc-val { font-size: 24rpx; color: #fff; }
.val-ok { color: #10b981; }
.val-ng { color: #ef4444; }

.empty { display: flex; flex-direction: column; align-items: center; padding: 80rpx 0; }
.empty-icon { font-size: 60rpx; }
.empty-text { font-size: 26rpx; color: #666; margin-top: 16rpx; }

.loading-bar { text-align: center; padding: 20rpx; }
.loading-text { font-size: 22rpx; color: #888; }
</style>