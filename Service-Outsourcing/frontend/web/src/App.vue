<template>
  <div class="app-shell">
    <aside class="sidebar" v-if="showSidebar">
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="2" y="2" width="24" height="24" rx="6" stroke="url(#g1)" stroke-width="2"/>
            <path d="M8 14l4 4 8-8" stroke="url(#g1)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <defs><linearGradient id="g1" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">EnergyLabel</span>
          <span class="brand-sub">Detection System</span>
        </div>
      </div>
      <nav class="sidebar-nav">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path"
          class="nav-item" :class="{ active: $route.path === item.path }">
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-active-bar"></span>
        </router-link>
      </nav>
      <div class="sidebar-bottom">
        <div class="server-status">
          <div class="pulse-dot" :class="backendOk ? 'online' : 'offline'">
            <span class="pulse-ring"></span>
          </div>
          <div class="status-info">
            <span class="status-label">{{ backendOk ? '系统运行中' : '系统离线' }}</span>
            <span class="status-detail">Port 8000</span>
          </div>
        </div>
      </div>
    </aside>
    <main class="main-area" :class="{ 'no-sidebar': !showSidebar }">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api.js'

const route = useRoute()
const showSidebar = computed(() => route.path !== '/')
const backendOk = ref(false)

const navItems = [
  { path: '/', icon: '🏠', label: '首页' },
  { path: '/monitor', icon: '📡', label: '实时监控' },
  { path: '/history', icon: '📋', label: '历史记录' },
  { path: '/statistic', icon: '📊', label: '统计报表' },
  { path: '/setup', icon: '⚙️', label: '系统配置' },
]

onMounted(async () => {
  try { await api.get('/api/config'); backendOk.value = true } catch { backendOk.value = false }
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
  --bg-0: #080a12;
  --bg-1: #0d1017;
  --bg-2: #131620;
  --bg-3: #1a1e2e;
  --bg-4: #222738;
  --border: rgba(255,255,255,0.06);
  --border-hover: rgba(99,102,241,0.3);
  --text-1: #f0f2f5;
  --text-2: #a0a8be;
  --text-3: #5c6380;
  --accent: #6366f1;
  --accent-2: #818cf8;
  --purple: #a855f7;
  --pink: #ec4899;
  --green: #10b981;
  --red: #ef4444;
  --orange: #f59e0b;
  --cyan: #06b6d4;
  --glow-accent: 0 0 20px rgba(99,102,241,0.15);
  --glow-green: 0 0 12px rgba(16,185,129,0.3);
  --glow-red: 0 0 12px rgba(239,68,68,0.3);
  --radius: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

* { margin:0; padding:0; box-sizing:border-box; }
html { font-size:14px; }
body {
  font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
  background:var(--bg-0); color:var(--text-1);
  -webkit-font-smoothing:antialiased; overflow-x:hidden;
}
a { text-decoration:none; color:inherit; }
::-webkit-scrollbar { width:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.08); border-radius:3px; }

/* Layout */
.app-shell { display:flex; min-height:100vh; }
.sidebar {
  width:220px; background:var(--bg-1); border-right:1px solid var(--border);
  display:flex; flex-direction:column; position:fixed; top:0; left:0; bottom:0; z-index:100;
}
.main-area { flex:1; margin-left:220px; min-height:100vh; }
.main-area.no-sidebar { margin-left:0; }

/* Brand */
.sidebar-brand { display:flex; align-items:center; gap:12px; padding:20px 16px; }
.brand-icon { display:flex; }
.brand-text { display:flex; flex-direction:column; }
.brand-name { font-size:15px; font-weight:700; letter-spacing:0.5px; }
.brand-sub { font-size:10px; color:var(--text-3); letter-spacing:1px; text-transform:uppercase; }

/* Nav */
.sidebar-nav { flex:1; padding:8px 10px; display:flex; flex-direction:column; gap:2px; }
.nav-item {
  display:flex; align-items:center; gap:10px; padding:10px 14px; position:relative;
  border-radius:10px; color:var(--text-2); font-size:13px; font-weight:500;
  transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1); overflow:hidden;
}
.nav-item::before {
  content:''; position:absolute; inset:0; border-radius:10px;
  background:radial-gradient(circle at var(--mx, 50%) var(--my, 50%), rgba(99,102,241,0.08), transparent 60%);
  opacity:0; transition:opacity 0.3s;
}
.nav-item:hover::before { opacity:1; }
.nav-item:hover { background:rgba(255,255,255,0.04); color:var(--text-1); }
.nav-item.active {
  background:linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.1));
  color:var(--accent-2);
  box-shadow:inset 0 0 20px rgba(99,102,241,0.05);
}
.nav-active-bar {
  position:absolute; left:0; top:50%; transform:translateY(-50%);
  width:3px; height:0; background:linear-gradient(180deg, var(--accent), var(--purple));
  border-radius:0 2px 2px 0; transition:height 0.3s;
}
.nav-item.active .nav-active-bar { height:60%; }
.nav-icon { font-size:16px; width:22px; text-align:center; }

/* Bottom */
.sidebar-bottom { padding:16px; border-top:1px solid var(--border); }
.server-status { display:flex; align-items:center; gap:10px; }
.pulse-dot { width:10px; height:10px; border-radius:50%; position:relative; flex-shrink:0; }
.pulse-dot.online { background:var(--green); }
.pulse-dot.offline { background:var(--red); }
.pulse-ring {
  position:absolute; inset:-3px; border-radius:50%; border:2px solid currentColor; opacity:0;
}
.pulse-dot.online .pulse-ring { border-color:var(--green); animation:pulseRing 2s infinite; }
@keyframes pulseRing { 0% { opacity:0.6; transform:scale(1); } 100% { opacity:0; transform:scale(1.8); } }
.status-info { display:flex; flex-direction:column; }
.status-label { font-size:12px; font-weight:500; }
.status-detail { font-size:10px; color:var(--text-3); }

/* Page transition */
.page-enter-active { animation:pageIn 0.45s cubic-bezier(0.16, 1, 0.3, 1); }
.page-leave-active { animation:pageOut 0.25s ease; }
@keyframes pageIn { from { opacity:0; transform:translateY(20px) scale(0.98); filter:blur(4px); } to { opacity:1; transform:translateY(0) scale(1); filter:blur(0); } }
@keyframes pageOut { from { opacity:1; } to { opacity:0; transform:translateY(-8px); } }

/* Shared components */
.glass-card {
  background:var(--bg-2); border:1px solid var(--border);
  border-radius:var(--radius-lg); padding:20px;
  transition:all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter:blur(12px);
  position:relative;
  overflow:hidden;
}
.glass-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg, transparent, rgba(99,102,241,0.2), transparent);
  opacity:0; transition:opacity 0.4s;
}
.glass-card:hover {
  border-color:var(--border-hover);
  box-shadow:var(--glow-accent), 0 8px 32px rgba(0,0,0,0.2);
  transform:translateY(-2px);
}
.glass-card:hover::before { opacity:1; }

/* Staggered entrance animation */
@keyframes fadeSlideUp {
  from { opacity:0; transform:translateY(24px); }
  to { opacity:1; transform:translateY(0); }
}
.glass-card { animation:fadeSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both; }
.glass-card:nth-child(1) { animation-delay:0.05s; }
.glass-card:nth-child(2) { animation-delay:0.1s; }
.glass-card:nth-child(3) { animation-delay:0.15s; }
.glass-card:nth-child(4) { animation-delay:0.2s; }

.section-head {
  display:flex; align-items:center; gap:8px; margin-bottom:14px;
  font-size:13px; font-weight:600; color:var(--text-2); text-transform:uppercase; letter-spacing:0.5px;
}
.section-icon { font-size:16px; }

.badge { display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-ok { background:rgba(16,185,129,0.12); color:var(--green); }
.badge-ng { background:rgba(239,68,68,0.12); color:var(--red); }

.page-header { padding:28px 32px 0; }
.page-title { font-size:24px; font-weight:700; letter-spacing:-0.3px; }
.page-subtitle { font-size:13px; color:var(--text-3); margin-top:4px; }
.page-body { padding:20px 32px 32px; }

.btn-primary {
  background:linear-gradient(135deg, var(--accent), var(--purple));
  border:none; border-radius:10px; padding:10px 24px;
  color:#fff; font-size:13px; font-weight:600; cursor:pointer;
  transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position:relative; overflow:hidden;
}
.btn-primary::before {
  content:''; position:absolute; top:50%; left:50%;
  width:0; height:0; border-radius:50%;
  background:rgba(255,255,255,0.15);
  transform:translate(-50%,-50%);
  transition:width 0.5s, height 0.5s;
}
.btn-primary:hover::before { width:300px; height:300px; }
.btn-primary::after {
  content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%;
  background:linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.08) 50%, transparent 70%);
  transform:translateX(-100%); transition:none;
}
.btn-primary:hover::after { animation:btnShine 0.6s ease forwards; }
@keyframes btnShine { to { transform:translateX(100%); } }
.btn-primary:hover { transform:translateY(-2px); box-shadow:0 6px 24px rgba(99,102,241,0.35); }
.btn-primary:active { transform:translateY(0) scale(0.97); }

.btn-ghost {
  background:var(--bg-3); border:1px solid var(--border);
  border-radius:10px; padding:10px 24px;
  color:var(--text-2); font-size:13px; font-weight:500; cursor:pointer;
  transition:var(--transition);
}
.btn-ghost:hover { border-color:var(--border-hover); color:var(--accent-2); }

.input-field {
  background:var(--bg-3); border:1px solid var(--border);
  border-radius:10px; padding:9px 14px; color:var(--text-1);
  font-size:13px; outline:none; transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-family:inherit;
}
.input-field:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(99,102,241,0.12), 0 0 16px rgba(99,102,241,0.08); }

/* Smooth number font */
.tabular-nums { font-variant-numeric:tabular-nums; }

/* Gradient text utility */
.gradient-text {
  background:linear-gradient(135deg, var(--accent), var(--purple), var(--pink));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  background-size:200% 200%;
  animation:gradientShift 4s ease infinite;
}
@keyframes gradientShift {
  0%,100% { background-position:0% 50%; }
  50% { background-position:100% 50%; }
}

/* Skeleton loading */
@keyframes shimmer {
  0% { background-position:-200% 0; }
  100% { background-position:200% 0; }
}
.skeleton {
  background:linear-gradient(90deg, var(--bg-3) 25%, var(--bg-4) 50%, var(--bg-3) 75%);
  background-size:200% 100%;
  animation:shimmer 1.5s infinite;
  border-radius:8px;
}

.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
@media (max-width:860px) { .grid-2 { grid-template-columns:1fr; } }
</style>