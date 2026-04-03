<template>
  <div class="landing">
    <!-- Particle starfield background -->
    <canvas ref="starCanvas" class="star-canvas"></canvas>
    <div class="bg-effects">
      <div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div>
      <div class="grid-bg"></div>
      <div class="aurora"></div>
    </div>

    <section class="hero">
      <div class="hi">
        <div class="chips" v-show="entered">
          <span class="chip ch-oh anim-item" style="--d:0.1s">🔷 OpenHarmony 生态</span>
          <span class="chip ch-cm anim-item" style="--d:0.2s">🏢 诚迈科技命题</span>
        </div>
        <h1 v-show="entered">
          <span class="l1 anim-item" style="--d:0.3s">产品能效标签</span>
          <span class="l2 anim-item" style="--d:0.45s">智能检测系统</span>
        </h1>
        <p class="hp anim-item" v-show="entered" style="--d:0.55s">
          基于 <b>OpenHarmony</b> 与 <b>YOLO 知识蒸馏</b> 技术，实现能效标签的实时识别、缺陷检测与位置校验，助力家电制造业智能化与绿色化发展
        </p>
        <div class="ctas anim-item" v-show="entered" style="--d:0.65s">
          <router-link to="/monitor" class="btn-primary cta glow-btn">
            <span class="btn-text">进入检测系统</span>
            <span class="btn-arrow">→</span>
          </router-link>
          <router-link to="/statistic" class="btn-ghost cta">数据报表</router-link>
        </div>
      </div>
    </section>

    <!-- Animated metrics -->
    <section class="sec">
      <div class="mg">
        <div v-for="(m,i) in metrics" :key="m.l" class="mc anim-item" :style="{'--d': (0.2+i*0.08)+'s'}" v-show="entered">
          <div class="mi" :style="{background:m.b}">
            <span class="mi-icon">{{m.i}}</span>
          </div>
          <div class="mb">
            <span class="mv" ref="counterRefs">
              <span class="counter-value">{{animatedValues[i] || m.v}}</span>
            </span>
            <span class="ml">{{m.l}}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Architecture flow -->
    <section class="sec">
      <div class="sh anim-item" v-show="entered" style="--d:0.1s">
        <span class="sb">SYSTEM ARCHITECTURE</span>
        <h2 class="s2">系统架构</h2>
      </div>
      <div class="af">
        <template v-for="(n,i) in arch" :key="i">
          <div class="an anim-item" :style="{'--d': (0.15+i*0.1)+'s'}" v-show="entered">
            <div class="ai" :style="{background:n.b}">{{n.i}}</div>
            <span class="at">{{n.t}}</span>
            <span class="ad">{{n.d}}</span>
            <div class="an-glow"></div>
          </div>
          <div v-if="i<arch.length-1" class="aa anim-item" :style="{'--d': (0.2+i*0.1)+'s'}" v-show="entered">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </template>
      </div>
    </section>

    <!-- Core capabilities -->
    <section class="sec">
      <div class="sh anim-item" v-show="entered" style="--d:0.1s">
        <span class="sb">CORE CAPABILITIES</span>
        <h2 class="s2">五维检测能力</h2>
      </div>
      <div class="cg">
        <div v-for="(c,i) in caps" :key="c.t" class="cc anim-item" :style="{'--d': (0.15+i*0.08)+'s'}" v-show="entered">
          <div class="ci" :style="{background:c.b}">{{c.i}}</div>
          <span class="ct">{{c.t}}</span>
          <span class="cd">{{c.d}}</span>
          <div class="cc-shine"></div>
        </div>
      </div>
    </section>

    <!-- Quick access -->
    <section class="sec">
      <div class="sh anim-item" v-show="entered" style="--d:0.1s">
        <span class="sb">QUICK ACCESS</span>
        <h2 class="s2">功能入口</h2>
      </div>
      <div class="fg">
        <router-link v-for="(f,i) in feats" :key="f.p" :to="f.p" class="fc anim-item" :style="{'--d': (0.15+i*0.1)+'s'}" v-show="entered">
          <div class="fi" :style="{background:f.b}">{{f.i}}</div>
          <div class="fb"><span class="ft">{{f.t}}</span><span class="fd">{{f.d}}</span></div>
          <span class="fa">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M7 4l6 6-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </router-link>
      </div>
    </section>

    <!-- Tech stack -->
    <section class="sec tc anim-item" v-show="entered" style="--d:0.2s">
      <div class="tl">技术栈</div>
      <div class="tt">
        <span v-for="(t,i) in techs" :key="t" class="tg" :style="{'animation-delay': (i*0.05)+'s'}">{{t}}</span>
      </div>
    </section>

    <footer class="lf anim-item" v-show="entered" style="--d:0.3s">
      <div>第十七届中国大学生服务外包创新创业大赛 · A02 · 诚迈科技股份有限公司</div>
      <div class="lfs">基于 OpenHarmony 的产品能效标签与缺陷检测系统 · 智能计算方向</div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

const entered = ref(false)
const starCanvas = ref(null)
const animatedValues = ref([])
let animFrame = null

const metrics = [
  {i:'🎯',v:'99.2%',l:'识别准确率',b:'rgba(99,102,241,0.12)',num:99.2,suffix:'%'},
  {i:'⚡',v:'<50ms',l:'推理延迟',b:'rgba(245,158,11,0.12)',num:50,prefix:'<',suffix:'ms'},
  {i:'🔍',v:'5维',l:'检测维度',b:'rgba(16,185,129,0.12)',num:5,suffix:'维'},
  {i:'🏭',v:'24/7',l:'持续运行',b:'rgba(168,85,247,0.12)',num:24,suffix:'/7'},
  {i:'📱',v:'3端',l:'多端协同',b:'rgba(236,72,153,0.12)',num:3,suffix:'端'},
  {i:'🔄',v:'实时',l:'流水线检测',b:'rgba(6,182,212,0.12)',text:'实时'},
]

const arch = [
  {i:'📷',t:'图像采集',d:'OpenHarmony 设备',b:'rgba(6,182,212,0.12)'},
  {i:'🧠',t:'AI 推理',d:'YOLO + 知识蒸馏',b:'rgba(99,102,241,0.12)'},
  {i:'📝',t:'OCR 识别',d:'PaddleOCR',b:'rgba(245,158,11,0.12)'},
  {i:'✅',t:'综合判定',d:'多维度校验',b:'rgba(16,185,129,0.12)'},
  {i:'📊',t:'数据分析',d:'统计与报表',b:'rgba(168,85,247,0.12)'},
]

const caps = [
  {i:'🏷️',t:'标签识别',d:'OCR 识别能效等级标签文字',b:'rgba(99,102,241,0.12)'},
  {i:'🔄',t:'标签比对',d:'与预设型号标准自动比对',b:'rgba(6,182,212,0.12)'},
  {i:'💔',t:'缺陷检测',d:'破损、污渍、褶皱等缺陷',b:'rgba(239,68,68,0.12)'},
  {i:'📍',t:'位置检测',d:'标签粘贴位置规范校验',b:'rgba(245,158,11,0.12)'},
  {i:'🌐',t:'多场景适应',d:'不同光照背景稳定运行',b:'rgba(16,185,129,0.12)'},
]

const feats = [
  {p:'/monitor',i:'📡',t:'实时监控',d:'生产线检测结果实时展示',b:'rgba(99,102,241,0.12)'},
  {p:'/history',i:'📋',t:'历史记录',d:'多维度筛选查询检测数据',b:'rgba(16,185,129,0.12)'},
  {p:'/statistic',i:'📊',t:'统计报表',d:'趋势分析与合格率可视化',b:'rgba(245,158,11,0.12)'},
  {p:'/setup',i:'⚙️',t:'系统配置',d:'型号管理与参数调优',b:'rgba(168,85,247,0.12)'},
]

const techs = ['OpenHarmony','YOLOv8','知识蒸馏','PaddleOCR','FastAPI','Vue 3','SQLite','CNN','数据增强','迁移学习']

// Number counter animation
function animateCounters() {
  const duration = 1500
  const start = performance.now()
  const targets = metrics.map(m => m.num || 0)

  function tick(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3) // easeOutCubic

    animatedValues.value = metrics.map((m, i) => {
      if (m.text) return m.text
      const val = targets[i] * ease
      const prefix = m.prefix || ''
      const suffix = m.suffix || ''
      if (Number.isInteger(m.num)) return prefix + Math.round(val) + suffix
      return prefix + val.toFixed(1) + suffix
    })

    if (progress < 1) animFrame = requestAnimationFrame(tick)
  }
  animFrame = requestAnimationFrame(tick)
}

// Starfield canvas
let stars = []
let starAnim = null
let resizeHandler = null

function initStarfield() {
  const canvas = starCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1

  function resize() {
    canvas.width = window.innerWidth * dpr
    canvas.height = window.innerHeight * 2 * dpr
    canvas.style.width = '100%'
    canvas.style.height = '200vh'
    ctx.scale(dpr, dpr)
  }
  resize()
  resizeHandler = resize
  window.addEventListener('resize', resize)

  const w = () => canvas.width / (window.devicePixelRatio || 1)
  const h = () => canvas.height / (window.devicePixelRatio || 1)

  stars = Array.from({length: 120}, () => ({
    x: Math.random() * w(),
    y: Math.random() * h(),
    r: Math.random() * 1.2 + 0.3,
    speed: Math.random() * 0.3 + 0.05,
    opacity: Math.random() * 0.6 + 0.2,
    twinkle: Math.random() * Math.PI * 2,
  }))

  function draw() {
    ctx.clearRect(0, 0, w(), h())
    for (const s of stars) {
      s.twinkle += 0.02
      s.y -= s.speed
      if (s.y < -5) { s.y = h() + 5; s.x = Math.random() * w() }
      const alpha = s.opacity * (0.6 + 0.4 * Math.sin(s.twinkle))
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(165,180,252,${alpha})`
      ctx.fill()
    }
    starAnim = requestAnimationFrame(draw)
  }
  draw()
}

onMounted(() => {
  nextTick(() => {
    entered.value = true
    initStarfield()
    setTimeout(animateCounters, 600)
  })
})

onUnmounted(() => {
  if (animFrame) cancelAnimationFrame(animFrame)
  if (starAnim) cancelAnimationFrame(starAnim)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})
</script>

<style scoped>
.landing { min-height:100vh; position:relative; overflow-x:hidden; }

/* Starfield */
.star-canvas { position:fixed; inset:0; z-index:0; pointer-events:none; }

/* Background effects */
.bg-effects { position:fixed; inset:0; pointer-events:none; z-index:0; }
.orb { position:absolute; border-radius:50%; filter:blur(80px); animation:fl 20s ease-in-out infinite; }
.o1 { width:500px; height:500px; top:-10%; left:-5%; background:rgba(99,102,241,.12); }
.o2 { width:400px; height:400px; bottom:-5%; right:-5%; background:rgba(168,85,247,.1); animation-delay:-7s; }
.o3 { width:300px; height:300px; top:40%; left:50%; background:rgba(236,72,153,.06); animation-delay:-14s; }
@keyframes fl { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(30px,-20px) scale(1.05)} 66%{transform:translate(-20px,15px) scale(.95)} }

.aurora {
  position:absolute; top:0; left:50%; transform:translateX(-50%);
  width:120%; height:400px;
  background:radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.06) 0%, transparent 70%);
  pointer-events:none;
}

.grid-bg {
  position:absolute; inset:0;
  background-image:linear-gradient(rgba(255,255,255,.012) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.012) 1px,transparent 1px);
  background-size:60px 60px;
  mask-image:radial-gradient(ellipse at 50% 30%, black 20%, transparent 70%);
}

/* Entrance animation */
.anim-item {
  opacity:0; transform:translateY(28px);
  animation:animIn 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay:var(--d, 0s);
}
@keyframes animIn { to { opacity:1; transform:translateY(0); } }

/* Sections */
.sec { position:relative; z-index:1; max-width:800px; margin:0 auto; padding:0 32px; margin-bottom:32px; }
.hero { position:relative; z-index:1; padding:80px 32px 20px; text-align:center; max-width:800px; margin:0 auto; }
.hi { max-width:680px; margin:0 auto; }

/* Chips */
.chips { display:flex; justify-content:center; gap:10px; margin-bottom:24px; flex-wrap:wrap; }
.chip {
  display:inline-flex; align-items:center; gap:4px; padding:5px 14px;
  border-radius:20px; font-size:11px; font-weight:600;
  backdrop-filter:blur(8px);
}
.ch-oh { background:rgba(6,182,212,.08); border:1px solid rgba(6,182,212,.2); color:var(--cyan); }
.ch-cm { background:rgba(99,102,241,.08); border:1px solid rgba(99,102,241,.2); color:var(--accent-2); }

/* Title */
h1 { margin-bottom:16px; }
.l1 {
  display:block; font-size:48px; font-weight:800; letter-spacing:-1px; line-height:1.15;
  color:var(--text-1);
}
.l2 {
  display:block; font-size:48px; font-weight:800; letter-spacing:-1px; line-height:1.15;
  background:linear-gradient(135deg, var(--accent), var(--purple), var(--pink), var(--cyan));
  background-size:300% 300%;
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  animation:gradFlow 6s ease infinite;
}
@keyframes gradFlow {
  0%,100% { background-position:0% 50%; }
  50% { background-position:100% 50%; }
}

.hp { font-size:15px; color:var(--text-2); line-height:1.8; margin-bottom:32px; }
.hp b { color:var(--accent-2); }

/* CTAs */
.ctas { display:flex; justify-content:center; gap:12px; }
.cta { padding:12px 28px; font-size:14px; }
.glow-btn {
  position:relative;
  display:inline-flex; align-items:center; gap:8px;
}
.glow-btn .btn-arrow {
  display:inline-block; transition:transform 0.3s;
}
.glow-btn:hover .btn-arrow { transform:translateX(4px); }

/* Metrics */
.mg { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.mc {
  display:flex; align-items:center; gap:12px; padding:14px 16px;
  background:rgba(19,22,32,0.8); border:1px solid var(--border);
  border-radius:var(--radius); transition:all 0.35s cubic-bezier(0.4,0,0.2,1);
  backdrop-filter:blur(8px);
}
.mc:hover { border-color:var(--border-hover); transform:translateY(-3px); box-shadow:0 8px 24px rgba(0,0,0,0.2); }
.mi {
  width:42px; height:42px; border-radius:12px;
  display:flex; align-items:center; justify-content:center;
  font-size:18px; flex-shrink:0;
  transition:transform 0.3s;
}
.mc:hover .mi { transform:scale(1.1) rotate(-5deg); }
.mi-icon { font-size:18px; }
.mb { display:flex; flex-direction:column; }
.mv { font-size:22px; font-weight:800; color:var(--accent-2); font-variant-numeric:tabular-nums; }
.counter-value { display:inline-block; }
.ml { font-size:11px; color:var(--text-3); }

/* Architecture */
.sh { text-align:center; margin-bottom:20px; }
.sb { font-size:10px; color:var(--text-3); text-transform:uppercase; letter-spacing:2px; }
.s2 { font-size:22px; font-weight:700; margin-top:4px; }

.af { display:flex; align-items:center; justify-content:center; gap:8px; flex-wrap:wrap; }
.an {
  display:flex; flex-direction:column; align-items:center; gap:6px;
  padding:16px 12px; background:rgba(19,22,32,0.8);
  border:1px solid var(--border); border-radius:var(--radius-lg);
  min-width:100px; transition:all 0.35s; position:relative; overflow:hidden;
}
.an:hover { border-color:var(--border-hover); transform:translateY(-3px); }
.an-glow {
  position:absolute; bottom:-20px; left:50%; transform:translateX(-50%);
  width:60px; height:40px; border-radius:50%;
  background:radial-gradient(circle, rgba(99,102,241,0.15), transparent);
  opacity:0; transition:opacity 0.3s;
}
.an:hover .an-glow { opacity:1; }
.ai { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; }
.at { font-size:13px; font-weight:600; }
.ad { font-size:10px; color:var(--text-3); }
.aa { color:var(--text-3); font-size:18px; animation:arrowPulse 2s ease-in-out infinite; }
@keyframes arrowPulse { 0%,100%{opacity:0.4;transform:translateX(0)} 50%{opacity:1;transform:translateX(3px)} }

/* Capabilities */
.cg { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }
.cc {
  display:flex; flex-direction:column; align-items:center; gap:6px;
  padding:16px 8px; background:rgba(19,22,32,0.8);
  border:1px solid var(--border); border-radius:var(--radius-lg);
  text-align:center; transition:all 0.35s; position:relative; overflow:hidden;
}
.cc:hover { border-color:var(--border-hover); transform:translateY(-4px); box-shadow:0 8px 24px rgba(0,0,0,0.15); }
.cc-shine {
  position:absolute; top:-50%; left:-50%; width:200%; height:200%;
  background:linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.03) 50%, transparent 60%);
  transform:translateX(-100%); transition:none;
}
.cc:hover .cc-shine { animation:cardShine 0.8s ease forwards; }
@keyframes cardShine { to { transform:translateX(100%); } }
.ci { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; transition:transform 0.3s; }
.cc:hover .ci { transform:scale(1.15); }
.ct { font-size:13px; font-weight:600; }
.cd { font-size:10px; color:var(--text-3); line-height:1.4; }

/* Feature cards */
.fg { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.fc {
  display:flex; align-items:center; gap:14px; padding:16px;
  background:rgba(19,22,32,0.8); border:1px solid var(--border);
  border-radius:var(--radius-lg); transition:all 0.35s; position:relative; overflow:hidden;
}
.fc::after {
  content:''; position:absolute; inset:0;
  background:linear-gradient(135deg, rgba(99,102,241,0.03), transparent);
  opacity:0; transition:opacity 0.3s;
}
.fc:hover::after { opacity:1; }
.fc:hover { border-color:var(--border-hover); transform:translateY(-3px); box-shadow:0 8px 24px rgba(99,102,241,0.1); }
.fi { width:42px; height:42px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; transition:transform 0.3s; }
.fc:hover .fi { transform:scale(1.1) rotate(-5deg); }
.fb { flex:1; display:flex; flex-direction:column; position:relative; z-index:1; }
.ft { font-size:14px; font-weight:600; }
.fd { font-size:11px; color:var(--text-3); margin-top:2px; }
.fa { color:var(--text-3); transition:all 0.3s; position:relative; z-index:1; }
.fc:hover .fa { color:var(--accent-2); transform:translateX(4px); }

/* Tech stack */
.tc { text-align:center; }
.tl { font-size:10px; color:var(--text-3); text-transform:uppercase; letter-spacing:2px; margin-bottom:12px; }
.tt { display:flex; flex-wrap:wrap; justify-content:center; gap:8px; }
.tg {
  padding:5px 14px; border-radius:20px; font-size:11px; font-weight:500;
  background:rgba(26,30,46,0.8); border:1px solid var(--border);
  color:var(--text-2); transition:all 0.3s;
  opacity:0; animation:tagIn 0.4s ease forwards;
}
@keyframes tagIn { from { opacity:0; transform:scale(0.8); } to { opacity:1; transform:scale(1); } }
.tg:hover { border-color:var(--accent); color:var(--accent-2); transform:translateY(-2px); box-shadow:0 4px 12px rgba(99,102,241,0.15); }

/* Footer */
.lf { position:relative; z-index:1; text-align:center; padding:40px 32px 32px; font-size:12px; color:var(--text-3); }
.lfs { font-size:11px; margin-top:4px; color:var(--text-3); opacity:.6; }

/* Responsive */
@media(max-width:700px) {
  .l1,.l2 { font-size:32px; }
  .mg { grid-template-columns:repeat(2,1fr); }
  .cg { grid-template-columns:repeat(2,1fr); }
  .fg { grid-template-columns:1fr; }
  .af { flex-direction:column; }
  .aa { transform:rotate(90deg); }
}
</style>