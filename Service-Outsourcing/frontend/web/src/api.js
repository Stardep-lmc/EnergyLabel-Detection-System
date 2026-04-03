class ApiError extends Error {
  constructor(status, detail) {
    super(detail)
    this.status = status
  }
}

async function request(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearTimeout(timeout)

    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new ApiError(res.status, body.detail || `HTTP ${res.status}`)
    }
    return res
  } catch (e) {
    clearTimeout(timeout)
    if (e.name === 'AbortError') throw new ApiError(0, '请求超时')
    throw e
  }
}

export const api = {
  get: (url, timeoutMs) => request(url, {}, timeoutMs).then(r => r.json()),
  post: (url, body, timeoutMs) => request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }, timeoutMs).then(r => r.json()),
  upload: (url, formData, timeoutMs = 60000) => request(url, {
    method: 'POST',
    body: formData,
  }, timeoutMs).then(r => r.json()),
  raw: (url, options, timeoutMs) => request(url, options, timeoutMs),
}

export { ApiError }