<template>
  <div class="header">
    <div class="logo">
      <div class="img"><img src="../../assets/logo.png" alt="logo" /></div>
      <div style="margin-left: 30px">大模型智能体构建系统</div>
    </div>
    <div class="menu">
      <el-menu
        class="el-menu-demo"
        mode="horizontal"
        @select="() => {}"
        background-color="#3498db"
        text-color="#fff"
        active-text-color="#ffd04b"
      >
        <el-menu-item index="3">工作台</el-menu-item>
      </el-menu>
      <div class="my">
        <el-menu
          class="el-menu-demo"
          mode="horizontal"
          @select="() => {}"
          background-color="#3498db"
          text-color="#fff"
          active-text-color="#ffd04b"
        >
          <el-submenu index="2">
            <template slot="title"
              ><el-avatar
                src="https://pub-141831e61e69445289222976a15b6fb3.r2.dev/Image_to_url_V2/QQ-imagetourl.cloud-1772698219018-8sc1cq.png"
              ></el-avatar
            ></template>
            <el-menu-item index="2-1">选项1</el-menu-item>
            <el-menu-item index="2-2">选项2</el-menu-item>
            <el-menu-item index="2-3" @click="loginOut">退出登陆</el-menu-item>
          </el-submenu>
        </el-menu>
      </div>
    </div>
  </div>
</template>
<script>
import { loginOut } from "../../api/login";
export default {
  data() {
    return {};
  },
  methods: {
    async loginOut() {
      // 清除cookie  退回登录页
      const { code } = await loginOut();
      code === 200
        ? this.$router.push("/login")
        : this.$message.error("退出成功");
    },
  },
};
</script>
<style lang="less" scoped>
@import "../../assets/variables.less";

.header {
  padding: 0 20px;
  display: flex;
  background-color: @primary-color;
  overflow: hidden;
  justify-content: space-between;

  /deep/.el-menu.el-menu--horizontal {
    border-bottom: none;
  }

  .logo {
    display: flex;
    align-items: center;
    color: #fff;
    font-size: 24px;

    .img {
      width: 60px;
      height: 60px;
    }
  }

  .menu {
    display: flex;
    align-items: center;

    .el-menu-demo {
      // background-color: @primary-color !important;
      height: 60px;
    }

    .my {
      margin-left: 10px;
      position: relative;

      .contorl {
        position: absolute;
        background-color: rebeccapurple;
        width: 200px;
        height: 200px;
        // top: 100px;
      }
    }
  }
}
</style>