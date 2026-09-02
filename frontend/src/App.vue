<template>
  <el-container>
    <el-header>
      <div class="header">
        <h1>🗄️ AI 向量数据仓库</h1>
        <p>ClickHouse + BGE 语义检索 | 实时数仓看板</p>
      </div>
    </el-header>
    
    <el-container>
      <el-aside width="200px">
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/">
            <span>📊 总览</span>
          </el-menu-item>
          <el-menu-item index="/dwd">
            <span>🔹 DWD 明细层</span>
          </el-menu-item>
          <el-menu-item index="/dws">
            <span>🔸 DWS 汇总层</span>
          </el-menu-item>
          <el-menu-item index="/ads">
            <span>📈 ADS 应用层</span>
          </el-menu-item>
          <el-menu-item index="/vector">
            <span>🔍 Vector 向量层</span>
          </el-menu-item>
          <el-menu-item index="/architecture">
            <span>🏗️ 架构说明</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.el-header {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  color: white;
  padding: 20px;
}

.header h1 {
  margin: 0 0 5px 0;
  font-size: 1.8em;
}

.header p {
  margin: 0;
  opacity: 0.9;
}

.el-aside {
  background: #f5f5f5;
  height: calc(100vh - 100px);
}

.el-main {
  padding: 20px;
  background: #fafafa;
}
</style>