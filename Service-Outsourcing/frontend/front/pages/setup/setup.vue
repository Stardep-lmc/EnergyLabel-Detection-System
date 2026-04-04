<template>
  <scroll-view class="page" scroll-y="true">
    <view class="header">
      <text class="title">系统配置</text>
      <text class="subtitle">产品型号、检测参数与相机设置</text>
    </view>

    <!-- 预设产品型号 -->
    <view class="card">
      <text class="section-title">📋 预设产品型号</text>
      <view class="model-list">
        <view v-for="(item, idx) in presetModels" :key="idx" class="model-item">
          <view class="model-info">
            <text class="model-name">{{ item.name }}</text>
            <text class="model-desc">{{ item.model }}</text>
          </view>
          <view class="model-right">
            <picker :range="energyLevels" :value="energyLevels.indexOf(item.standardLabel)" @change="(e) => item.standardLabel = energyLevels[e.detail.value]">
              <view class="picker-val">{{ item.standardLabel }}</view>
            </picker>
            <switch :checked="item.enabled" @change="(e) => item.enabled = e.detail.value" />
            <text v-if="presetModels.length > 1" class="del-btn" @click="presetModels.splice(idx, 1)">✕</text>
          </view>
        </view>
      </view>
      <view class="add-row">
        <input v-model="newModel.name" placeholder="产品名称" class="input-field" />
        <input v-model="newModel.model" placeholder="产品型号" class="input-field" />
        <picker :range="energyLevels" @change="(e) => newModel.standardLabel = energyLevels[e.detail.value]">
          <view class="picker-val">{{ newModel.standardLabel }}</view>
        </picker>
        <button class="btn-add" @click="addModel">+ 添加</button>
      </view>
    </view>

    <!-- 检测参数 -->
    <view class="card">
      <text class="section-title">⚙️ 检测参数</text>
      <view class="param-item">
        <view class="param-top">
          <text class="param-name">📍 位置偏移容忍度</text>
          <text class="param-desc">标签偏离中心多少%算异常</text>
        </view>
        <view class="param-ctrl">
          <slider :value="positionTolerance" @change="(e) => positionTolerance = e.detail.value" min="0" max="20" step="1" activeColor="#6366f1" />
          <text class="param-val">{{ positionTolerance }}%</text>
        </view>
      </view>
      <view class="param-item">
        <view class="param-top">
          <text class="param-name">🔍 缺陷检测灵敏度</text>
          <text class="param-desc">越高越容易检出微小缺陷</text>
        </view>
        <view class="chip-row">
          <text v-for="s in sensitivityLevels" :key="s" class="chip" :class="{ active: sensitivity === s }" @click="sensitivity = s">{{ s }}</text>
        </view>
      </view>
      <view class="param-item">
        <view class="param-top">
          <text class="param-name">💡 光照补偿</text>
          <text class="param-desc">适应不同环境光线</text>
        </view>
        <view class="param-ctrl">
          <slider :value="lightCompensation" @change="(e) => lightCompensation = e.detail.value" min="-5" max="5" step="1" activeColor="#6366f1" />
          <text class="param-val">{{ lightCompensation > 0 ? '+' : '' }}{{ lightCompensation }}</text>
        </view>
      </view>
    </view>

    <!-- 相机参数 -->
    <view class="card">
      <text class="section-title">📷 相机参数</text>
      <view class="param-item">
        <view class="param-top"><text class="param-name">🔆 曝光</text></view>
        <view class="param-ctrl">
          <slider :value="exposure" @change="(e) => exposure = e.detail.value" min="-3" max="3" step="1" activeColor="#6366f1" />
          <text class="param-val">{{ exposure > 0 ? '+' : '' }}{{ exposure }}</text>
        </view>
      </view>
      <view class="param-item">
        <view class="param-top"><text class="param-name">📱 分辨率</text></view>
        <view class="chip-row">
          <text v-for="r in resolutions" :key="r" class="chip" :class="{ active: resolution === r }" @click="resolution = r">{{ r }}</text>
        </view>
      </view>
    </view>

    <!-- 操作按钮 -->
    <view class="action-row">
      <button class="btn-save" @click="saveConfig">💾 保存配置</button>
      <button class="btn-reset" @click="resetConfig">↺ 恢复默认</button>
    </view>
  </scroll-view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import api from '../../utils/api.js'

const energyLevels = ['A++', 'A+', 'A', 'B', 'C']
const sensitivityLevels = ['低', '中', '高']
const resolutions = ['640x480', '1280x720', '1920x1080']

const presetModels = ref([{ name: '冰箱', model: 'BCD-520W', standardLabel: 'A++', enabled: true }])
const newModel = ref({ name: '', model: '', standardLabel: 'A++' })
const positionTolerance = ref(10)
const sensitivity = ref('中')
const lightCompensation = ref(0)
const exposure = ref(0)
const resolution = ref('1280x720')
const defaultConfig = ref(null)

const fetchConfig = async () => {
  try {
    const d = await api.get('/api/config')
    presetModels.value = d.models || presetModels.value
    positionTolerance.value = d.positionTolerance ?? 10
    sensitivity.value = d.sensitivity ?? '中'
    lightCompensation.value = d.lightCompensation ?? 0
    exposure.value = d.camera?.exposure ?? 0
    resolution.value = d.camera?.resolution ?? '1280x720'
    defaultConfig.value = JSON.parse(JSON.stringify(d))
  } catch { /* ignore */ }
}

const addModel = () => {
  if (!newModel.value.name || !newModel.value.model) {
    uni.showToast({ title: '请填写完整信息', icon: 'none' })
    return
  }
  presetModels.value.push({ ...newModel.value, enabled: true })
  newModel.value = { name: '', model: '', standardLabel: 'A++' }
  uni.showToast({ title: '添加成功', icon: 'success' })
}

const saveConfig = async () => {
  const cfg = {
    models: presetModels.value,
    positionTolerance: positionTolerance.value,
    sensitivity: sensitivity.value,
    lightCompensation: lightCompensation.value,
    camera: { exposure: exposure.value, resolution: resolution.value },
  }
  try {
    await api.post('/api/config', cfg)
    defaultConfig.value = JSON.parse(JSON.stringify(cfg))
    // 保存后自动重载 ML 检测器
    try { await api.post('/api/ml/reload', {}) } catch { /* ignore */ }
    uni.showToast({ title: '配置已保存', icon: 'success' })
  } catch (e) {
    uni.showToast({ title: e.message || '保存失败', icon: 'none' })
  }
}

const resetConfig = () => {
  uni.showModal({
    title: '提示',
    content: '确定要恢复默认配置吗？',
    success: async (res) => {
      if (!res.confirm) return
      if (!defaultConfig.value) { uni.showToast({ title: '无默认数据', icon: 'none' }); return }
      const d = defaultConfig.value
      presetModels.value = JSON.parse(JSON.stringify(d.models))
      positionTolerance.value = d.positionTolerance
      sensitivity.value = d.sensitivity
      lightCompensation.value = d.lightCompensation
      exposure.value = d.camera?.exposure ?? 0
      resolution.value = d.camera?.resolution ?? '1280x720'
      try {
        await api.post('/api/config', d)
        uni.showToast({ title: '已恢复默认', icon: 'success' })
      } catch { uni.showToast({ title: '恢复失败', icon: 'none' }) }
    }
  })
}

onLoad(() => { fetchConfig() })
</script>

<style scoped>
.page { min-height: 100vh; background: #0a0a1a; padding-bottom: 40rpx; }
.header { padding: 30rpx; }
.title { font-size: 40rpx; font-weight: 700; color: #fff; }
.subtitle { font-size: 22rpx; color: #888; margin-top: 4rpx; display: block; }

.card { margin: 0 24rpx 20rpx; padding: 24rpx; background: rgba(15,52,96,.6); border-radius: 16rpx; border: 1rpx solid rgba(255,255,255,.06); }
.section-title { font-size: 28rpx; font-weight: 600; color: #fff; margin-bottom: 16rpx; display: block; }

.model-list { display: flex; flex-direction: column; gap: 12rpx; margin-bottom: 16rpx; }
.model-item { display: flex; align-items: center; justify-content: space-between; padding: 16rpx; background: rgba(255,255,255,.03); border-radius: 12rpx; border: 1rpx solid rgba(255,255,255,.06); }
.model-info { display: flex; flex-direction: column; }
.model-name { font-size: 26rpx; font-weight: 600; color: #fff; }
.model-desc { font-size: 20rpx; color: #888; }
.model-right { display: flex; align-items: center; gap: 16rpx; }
.picker-val { padding: 8rpx 20rpx; border-radius: 20rpx; font-size: 24rpx; background: rgba(255,255,255,.06); color: #818cf8; }
.del-btn { color: #ef4444; font-size: 28rpx; padding: 4rpx 12rpx; }

.add-row { display: flex; flex-wrap: wrap; gap: 12rpx; padding: 16rpx; background: rgba(255,255,255,.02); border-radius: 12rpx; border: 2rpx dashed rgba(255,255,255,.1); }
.input-field { flex: 1; min-width: 200rpx; background: rgba(255,255,255,.06); border: 1rpx solid rgba(255,255,255,.1); border-radius: 12rpx; padding: 12rpx 16rpx; color: #fff; font-size: 24rpx; }
.btn-add { background: rgba(99,102,241,.15); border: 1rpx solid rgba(99,102,241,.3); color: #818cf8; border-radius: 12rpx; padding: 12rpx 24rpx; font-size: 24rpx; }

.param-item { padding: 16rpx 0; border-bottom: 1rpx solid rgba(255,255,255,.04); }
.param-item:last-child { border-bottom: none; }
.param-top { display: flex; flex-direction: column; margin-bottom: 12rpx; }
.param-name { font-size: 26rpx; font-weight: 500; color: #fff; }
.param-desc { font-size: 20rpx; color: #888; margin-top: 4rpx; }
.param-ctrl { display: flex; align-items: center; gap: 16rpx; }
.param-val { min-width: 60rpx; text-align: right; font-size: 28rpx; font-weight: 700; color: #818cf8; }

.chip-row { display: flex; gap: 12rpx; }
.chip { padding: 10rpx 28rpx; border-radius: 30rpx; font-size: 24rpx; background: rgba(255,255,255,.04); border: 1rpx solid rgba(255,255,255,.08); color: #aaa; }
.chip.active { background: linear-gradient(135deg, #6366f1, #a855f7); color: #fff; border-color: transparent; }

.action-row { display: flex; gap: 16rpx; padding: 0 24rpx; }
.btn-save { flex: 2; background: linear-gradient(135deg, #6366f1, #a855f7); border: none; border-radius: 16rpx; padding: 20rpx; color: #fff; font-size: 28rpx; font-weight: 600; }
.btn-reset { flex: 1; background: rgba(255,255,255,.06); border: 1rpx solid rgba(255,255,255,.1); border-radius: 16rpx; padding: 20rpx; color: #aaa; font-size: 28rpx; }
</style>