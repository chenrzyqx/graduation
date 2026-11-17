import Vue from 'vue'
import Router from 'vue-router'

import user from './modules/user'


Vue.use(Router)

const router = new Router({
  routes: [
    {
      path: '/',
      name: 'home',
      redirect:'/default',
      component: () => import('../views/Index/index.vue'),
      children:[{
        path: 'default',
        name: 'default',
        component: () => import('../views/default/index.vue')
      },{
        path: '/peizhi',
        component: () => import('../views/peizhi/peizhi.vue')
      },{
        path: '/model1',
        component: () => import('../views/model1/model1.vue')
      },{
        path: '/model2',
        component: () => import('../views/model2/model2.vue')
      },      
      user
    ]
    },
    { path: "*", redirect: "/404", name: "notMatch", hidden: true },
    {
      path: '/404',
      name: '404',
      component: () => import('../views/common/404.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/login/login.vue'),
    },
    
  ]
})




export default  router