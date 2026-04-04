/**
 * uni-app API 封装层
 * 统一 baseURL、错误处理、请求方法
 */

// 开发环境使用 H5 代理（vite proxy），生产环境需要配置实际地址
const BASE_URL = ''  // H5 开发时留空走 proxy；真机/小程序部署时改为 'http://192.168.x.x:8000'

/**
 * 通用请求封装
 */
function request(url, options = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method: options.method || 'GET',
      data: options.data,
      header: options.header || { 'Content-Type': 'application/json' },
      timeout: options.timeout || 15000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const detail = res.data?.detail || `HTTP ${res.statusCode}`
          uni.showToast({ title: detail, icon: 'none', duration: 2000 })
          reject(new Error(detail))
        }
      },
      fail: (err) => {
        uni.showToast({ title: '网络连接失败', icon: 'none', duration: 2000 })
        reject(new Error(err.errMsg || '网络错误'))
      }
    })
  })
}

/**
 * 上传文件封装（用于图片检测）
 */
function uploadFile(url, filePath, formData = {}) {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + url,
      filePath,
      name: 'file',
      formData,
      timeout: 60000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(res.data))
          } catch {
            resolve(res.data)
          }
        } else {
          let detail = `HTTP ${res.statusCode}`
          try { detail = JSON.parse(res.data).detail || detail } catch { }
          uni.showToast({ title: detail, icon: 'none', duration: 2000 })
          reject(new Error(detail))
        }
      },
      fail: (err) => {
        uni.showToast({ title: '上传失败', icon: 'none', duration: 2000 })
        reject(new Error(err.errMsg || '上传错误'))
      }
    })
  })
}

export const api = {
  get: (url, data, timeout) => request(url, { method: 'GET', data, timeout }),
  post: (url, data, timeout) => request(url, { method: 'POST', data, timeout }),
  upload: uploadFile,
}

export default api