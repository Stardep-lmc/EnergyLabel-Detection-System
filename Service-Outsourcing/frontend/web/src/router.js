import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import Monitor from './views/Monitor.vue'
import History from './views/History.vue'
import Statistic from './views/Statistic.vue'
import Setup from './views/Setup.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  { path: '/monitor', name: 'monitor', component: Monitor },
  { path: '/history', name: 'history', component: History },
  { path: '/statistic', name: 'statistic', component: Statistic },
  { path: '/setup', name: 'setup', component: Setup },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})