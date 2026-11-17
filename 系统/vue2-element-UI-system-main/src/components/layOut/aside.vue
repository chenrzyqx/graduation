<template>
  <el-menu
    :default-active="index"
    class="el-menu-vertical-demo"
    @open="() => {}"
    @close="() => {}"
    @select="(val) => (index = val)"
    :collapse="isCollapse"
    background-color="#3498db"
    text-color="#fff"
    active-text-color="#ffd04b"
    :router="true"
  >
    <el-menu-item index="/default">
      <i class="el-icon-location"></i>
      <span slot="title">首页</span>
    </el-menu-item>
    <el-menu-item index="/peizhi">
      <i class="el-icon-location"></i>
      <span slot="title">模型配置</span>
    </el-menu-item>
    <el-submenu index="2">
      <template slot="title">
        <i class="el-icon-location"></i>
        <span slot="title">智能体</span>
      </template>
      <el-menu-item index="/model1">智能体管理</el-menu-item>
      <el-menu-item index="/model2">智能体运行监控</el-menu-item>
    </el-submenu>
  </el-menu>
</template>
<script >
export default {
  data() {
    return {
      isCollapse: false,
      index: "/default",
    };
  },
  methods: {},
};
</script>
<style lang="less" scoped>
/deep/.el-submenu__title i {
  color: #fff;
}
/deep/.el-menu-item i {
  color: #fff;
}
</style>