<template>
  <scroll-view class="page" scroll-y="true">
    <view class="header">
      <view>
        <text class="title">实时监控</text>
        <text class="subtitle">上传图片检测能效标签</text>
      </view>
      <view class="ml-badge" :class="mlOk ? 'on' : 'off'">
        <view class="ml-dot"></view>
        <text>ML {{ mlOk ? '就绪' : '离线' }}</text>
      </view>
    </view>

    <view class="card">
      <text class="section-title">📤 图片检测</text>
      <view class="upload-area" @click="chooseImage">
        <view v-if="busy" class="upload-loading">
          <text>⏳ 正在检测...</text>
        </view>
        <image v-else-if="previewUrl" :src="previewUrl" class="preview-img" mode="aspectFit" />
        <view v-else class="upload-placeholder">
          <text style="font-size:32px">📁</text>
          <text>点击选择图片或拍照</text>
          <text style="font-size:11px;color:#888">支持 JPG / PNG</text>
        </view>
      </view>
      <view class="btn-row">
        <button class="btn-primary" :disabled="!selectedFile || busy" @click="doDetect">🔍 开始检测</button>
        <button class="btn-ghost" @click="clearUpload">清除</button>
      </view>
    </view>

    <view v-if="errMsg" class="err-msg"><text>{{ errMsg }}</text></view>

    <view v-if="cr.status" class="status-strip" :class="cr.status === 'OK' ? 'strip-ok' : 'strip-ng'">
      <view class="ss-left">
        <text class="ss-icon">{{ cr.status === 'OK' ? '✓' : '✗' }}</text>
        <view class="ss-text">
          <text class="ss-title">{{ cr.status === 'OK' ? '检测合格' : '检测不合格' }}</text>
          <text class="ss-time">{{ cr.timestamp }}</text>
        </view>
      </view>
      <view class="ss-right">
        <text v-if="cr.inferenceTime" class="ss-perf">⚡ {{ cr.inferenceTime }}ms</text>
        <text v-if="cr.ocrText" class="ss-tag">{{ cr.ocrText }}</text>
      </view>
    </view>

    <view v-if="cr.status" class="detail-grid">
      <view class="card">
        <text class="section-title">📋 标签识别</text>
        <view class="ocr-area">
          <image v-if="cr.imageUrl" :src="cr.imageUrl" class="det-img" mode="aspectFit" />
          <view v-else class="img-ph"><text>📷</text></view>
          <view class="ocr-info">
            <view class="info-row"><text class="lbl">识别标签</text><text class="val hl">{{ cr.ocrText || '--' }}</text></view>
            <view class="info-row"><text class="lbl">预设型号</text><text class="val">{{ cr.presetModel || '--' }}</text></view>
            <view class="info-row"><text class="lbl">置信度</text><text class="val">{{ cr.confidence ? (cr.confidence * 100).toFixed(1) + '%' : '--' }}</text></view>
            <view class="info-row"><text class="lbl">结果</text><text class="badge" :class="cr.isMatch ? 'badge-ok' : 'badge-ng'">{{ cr.isMatch ? '✓ 匹配' : '✗ 不匹配' }}</text></view>
          </view>
        </view>
      </view>

      <view class="card">
        <text class="section-title">⚠️ 缺陷检测</text>
        <view class="defect-grid">
          <view v-for="d in defectTypes" :key="d.name" class="defect-cell" :class="{ active: isDefectActive(d.name) }">
            <text class="dc-icon">{{ d.icon }}</text>
            <text class="dc-name">{{ d.name }}</text>
            <text class="dc-st">{{ isDefectActive(d.name) ? '检出' : '正常' }}</text>
          </view>
        </view>
      </view>

      <view class="card">
        <text class="section-title">📍 位置检测</text>
        <view class="pos-area">
          <view class="pos-grid">
            <view v-for="i in 9" :key="i" class="pos-cell" :class="{ lit: isPosCell(i) }">
              <view v-if="isPosCell(i)" class="pos-marker"></view>
            </view>
          </view>
          <view class="pos-info">
            <text class="pos-lbl">粘贴位置</text>
            <text class="pos-val" :class="cr.positionStatus === '正常' ? 'c-ok' : 'c-ng'">{{ cr.positionStatus || '--' }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="card">
      <text class="section-title">📝 最近记录</text>
      <view class="tbl-hd">
        <text class="th" style="width:70px">时间</text>
        <text class="th" style="flex:1">型号</text>
        <text class="th" style="width:50px">结果</text>
        <text class="th" style="width:50px">缺陷</text>
        <text class="th" style="width:50px">位置</text>
      </view>
      <view v-for="item in recentList" :key="item.id" class="tbl-row">
        <text class="td" style="width:70px;color:#888">{{ item.timestamp?.slice(-8) }}</text>
        <text class="td" style="flex:1">{{ item.productModel }}</text>
        <text class="td" :class="item.status === 'OK' ? 'c-ok' : 'c-ng'" style="width:50px">{{ item.status }}</text>
        <text class="td" style="width:50px">{{ item.defectType || '无' }}</text>
        <text class="td" style="width:50px">{{ item.positionStatus }}</text>
      </view>
      <view v-if="recentList.length === 0" class="empty-hint"><text style="color:#666">暂无记录</text></view>
    </view>
  </scroll-view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import api from '../../utils/api.js'

const defectTypes = [
  { name: '破损', icon: '💔' },
  { name: '污渍', icon: '💧' },
  { name: '褶皱', icon: '📄' },
  { name: '划痕', icon: '🔪' },
  { name: '偏移', icon: '↔️' },
]

const mlOk = ref(false)
const previewUrl = ref('')
const selectedFile = ref('')
const busy = ref(false)
const errMsg = ref('')
const cr = ref({
  status: '', ocrText: '', presetModel: '', isMatch: false,
  defectType: null, positionStatus: '', positionX: 50, positionY: 50,
  timestamp: '', imageUrl: '', confidence: 0, inferenceTime: 0,
})
const recentList = ref([])
let pollTimer = null

const isDefectActive = (name) => {
  const dt = cr.value.defectType
  if (!dt || dt === '无') return false
  return dt.includes(name)
}

const isPosCell = (i) => {
  const r = Math.floor((i - 1) / 3)
  const c = (i - 1) % 3
  return r === Math.floor((cr.value.positionY || 50) / 34) && c === Math.floor((cr.value.positionX || 50) / 34)
}

const chooseImage = () => {
  if (busy.value) return
  uni.chooseImage({
    count: 1, sizeType: ['compressed'], sourceType: ['album', 'camera'],
    success: (res) => { selectedFile.value = res.tempFilePaths[0]; previewUrl.value = res.tempFilePaths[0]; errMsg.value = '' }
  })
}

const clearUpload = () => { previewUrl.value = ''; selectedFile.value = ''; errMsg.value = '' }

const doDetect = async () => {
  if (!selectedFile.value) { errMsg.value = '请先选择图片'; return }
  busy.value = true; errMsg.value = ''
  try {
    const d = await api.upload('/api/ml/detect', selectedFile.value)
    cr.value = {
      status: d.status || 'OK', ocrText: d.ocr_text || '', presetModel: d.preset_model || '',
      isMatch: d.is_qualified, defectType: d.defect_type === '无' ? null : d.defect_type,
      positionStatus: d.position_status || '正常',
      positionX: d.position_x ? Math.round(d.position_x * 100) : 50,
      positionY: d.position_y ? Math.round(d.position_y * 100) : 50,
      timestamp: d.timestamp || new Date().toLocaleTimeString(),
      imageUrl: d.image_url || '', confidence: d.confidence || 0, inferenceTime: d.inference_time_ms || 0,
    }
    uni.showToast({ title: d.is_qualified ? '检测合格 ✓' : '检测不合格 ✗', icon: d.is_qualified ? 'success' : 'none' })
    fetchRecent()
  } catch (e) { errMsg.value = e.message || '检测失败' }
  busy.value = false
}

const fetchRecent = async () => {
  try {
    const d = await api.get('/api/recent', { limit: 10 })
    recentList.value = (d || []).map((x, i) => ({
      id: 'r_' + i, timestamp: x.timestamp || '', productModel: x.presetModel,
      status: x.status, defectType: x.defectType, positionStatus: x.positionStatus,
    }))
  } catch { /* ignore */ }
}

const pollData = async () => {
  try {
    const d = await api.get('/api/current')
    if (d.timestamp && d.timestamp !== cr.value.timestamp) {
      cr.value = { ...d, positionX: d.positionX || 50, positionY: d.positionY || 50, timestamp: d.timestamp, inferenceTime: 0 }
    }
  } catch { /* ignore */ }
  fetchRecent()
}

onMounted(async () => {
  try { const d = await api.get('/api/ml/status'); mlOk.value = d.available === true } catch { /* ignore */ }
  try { const d = await api.get('/api/current'); cr.value = { ...cr.value, ...d, timestamp: d.timestamp || '' } } catch { /* ignore */ }
  fetchRecent()
  pollTimer = setInterval(pollData, 5000)
})

onShow(() => { fetchRecent() })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.page { min-height: 100vh; background: #0a0a1a; padding-bottom: 30rpx; }
.header { display: flex; justify-content: space-between; align-items: center; padding: 24rpx 30rpx; }
.title { font-size: 40rpx; font-weight: 700; color: #fff; }
.subtitle { font-size: 22rpx; color: #888; margin-top: 4rpx; display: block; }
.ml-badge { display: flex; align-items: center; gap: 8rpx; padding: 8rpx 20rpx; border-radius: 30rpx; font-size: 22rpx; font-weight: 600; }
.ml-badge.on { background: rgba(16,185,129,.1); border: 1rpx solid rgba(16,185,129,.25); color: #10b981; }
.ml-badge.off { background: rgba(239,68,68,.1); border: 1rpx solid rgba(239,68,68,.25); color: #ef4444; }
.ml-dot { width: 12rpx; height: 12rpx; border-radius: 50%; background: currentColor; }
.card { margin: 0 24rpx 20rpx; padding: 24rpx; background: rgba(15,52,96,.6); border-radius: 16rpx; border: 1rpx solid rgba(255,255,255,.06); }
.section-title { font-size: 28rpx; font-weight: 600; color: #fff; margin-bottom: 16rpx; display: block; }
.upload-area { border: 2rpx dashed rgba(255,255,255,.15); border-radius: 16rpx; min-height: 240rpx; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.upload-placeholder { display: flex; flex-direction: column; align-items: center; gap: 8rpx; color: #888; font-size: 26rpx; }
.preview-img { width: 100%; max-height: 400rpx; }
.upload-loading { display: flex; align-items: center; gap: 12rpx; color: #818cf8; font-size: 28rpx; }
.btn-row { display: flex; gap: 16rpx; margin-top: 20rpx; }
.btn-primary { flex: 2; background: linear-gradient(135deg, #6366f1, #a855f7); border: none; border-radius: 16rpx; padding: 16rpx; color: #fff; font-size: 28rpx; font-weight: 600; }
.btn-primary[disabled] { opacity: 0.4; }
.btn-ghost { flex: 1; background: rgba(255,255,255,.06); border: 1rpx solid rgba(255,255,255,.1); border-radius: 16rpx; padding: 16rpx; color: #aaa; font-size: 28rpx; }
.err-msg { margin: 0 24rpx 16rpx; padding: 16rpx; border-radius: 12rpx; background: rgba(239,68,68,.08); color: #ef4444; font-size: 24rpx; }
.status-strip { display: flex; align-items: center; justify-content: space-between; padding: 20rpx 24rpx; margin: 0 24rpx 20rpx; border-radius: 16rpx; }
.strip-ok { background: rgba(16,185,129,.08); border: 1rpx solid rgba(16,185,129,.2); }
.strip-ng { background: rgba(239,68,68,.08); border: 1rpx solid rgba(239,68,68,.2); }
.ss-left { display: flex; align-items: center; gap: 16rpx; }
.ss-icon { font-size: 48rpx; }
.ss-text { display: flex; flex-direction: column; }
.ss-title { font-size: 30rpx; font-weight: 700; }
.strip-ok .ss-title { color: #10b981; }
.strip-ng .ss-title { color: #ef4444; }
.ss-time { font-size: 20rpx; color: #888; }
.ss-right { display: flex; align-items: center; gap: 16rpx; }
.ss-perf { font-size: 22rpx; color: #06b6d4; font-weight: 600; }
.ss-tag { padding: 8rpx 20rpx; border-radius: 12rpx; font-size: 32rpx; font-weight: 800; background: rgba(255,255,255,.05); color: #818cf8; }
.detail-grid { display: flex; flex-direction: column; }
.ocr-area { display: flex; gap: 20rpx; }
.det-img { width: 240rpx; height: 180rpx; border-radius: 12rpx; border: 1rpx solid rgba(255,255,255,.1); flex-shrink: 0; }
.img-ph { width: 240rpx; height: 180rpx; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,.03); border-radius: 12rpx; font-size: 48rpx; }
.ocr-info { flex: 1; display: flex; flex-direction: column; gap: 12rpx; justify-content: center; }
.info-row { display: flex; justify-content: space-between; align-items: center; }
.lbl { font-size: 24rpx; color: #888; }
.val { font-size: 26rpx; color: #fff; }
.hl { font-size: 34rpx; font-weight: 800; color: #818cf8; }
.badge { padding: 4rpx 16rpx; border-radius: 20rpx; font-size: 22rpx; font-weight: 600; }
.badge-ok { background: rgba(16,185,129,.12); color: #10b981; }
.badge-ng { background: rgba(239,68,68,.12); color: #ef4444; }
.defect-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10rpx; }
.defect-cell { display: flex; flex-direction: column; align-items: center; gap: 4rpx; padding: 16rpx 4rpx; border-radius: 12rpx; background: rgba(255,255,255,.03); border: 1rpx solid rgba(255,255,255,.06); }
.defect-cell.active { border-color: rgba(239,68,68,.4); background: rgba(239,68,68,.06); }
.dc-icon { font-size: 32rpx; }
.dc-name { font-size: 22rpx; font-weight: 600; color: #fff; }
.dc-st { font-size: 20rpx; color: #888; }
.defect-cell.active .dc-st { color: #ef4444; font-weight: 600; }
.pos-area { display: flex; align-items: center; gap: 30rpx; }
.pos-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4rpx; width: 120rpx; height: 120rpx; }
.pos-cell { background: rgba(255,255,255,.04); border-radius: 6rpx; border: 1rpx solid rgba(255,255,255,.06); display: flex; align-items: center; justify-content: center; }
.pos-cell.lit { background: rgba(99,102,241,.2); border-color: #6366f1; }
.pos-marker { width: 16rpx; height: 16rpx; border-radius: 50%; background: #6366f1; }
.pos-info { display: flex; flex-direction: column; gap: 6rpx; }
.pos-lbl { font-size: 22rpx; color: #888; }
.pos-val { font-size: 30rpx; font-weight: 700; }
.c-ok { color: #10b981; }
.c-ng { color: #ef4444; }
.tbl-hd { display: flex; padding: 8rpx 0; border-bottom: 1rpx solid rgba(255,255,255,.08); }
.th { font-size: 20rpx; color: #888; font-weight: 600; text-align: center; }
.tbl-row { display: flex; align-items: center; padding: 12rpx 0; border-bottom: 1rpx solid rgba(255,255,255,.04); }
.td { font-size: 22rpx; color: #ccc; text-align: center; }
.empty-hint { text-align: center; padding: 40rpx; }
</style>