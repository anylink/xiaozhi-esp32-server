# AGENTS.md - xiaozhi-esp32-server 项目上下文

## 项目概述

**xiaozhi-esp32-server** 是一个为开源智能硬件项目 [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 提供后端服务的综合性系统。由华南理工大学刘思源教授团队主导研发，基于人机共生智能理论和技术，构建了一个完整的智能语音交互后端平台。

### 核心能力
- 实时语音交互（ASR/TTS/VAD）
- 大语言模型对话（支持多种LLM/VLLM）
- 声纹识别
- 意图识别与函数调用
- 记忆系统
- 知识库集成（RAGFlow）
- IoT设备控制（Home Assistant集成）
- MCP协议支持

---

## 项目架构

```
xiaozhi-esp32-server/
├── main/
│   ├── xiaozhi-server/     # 核心AI引擎 (Python) - 端口 8000/8003
│   ├── manager-api/        # 管理后端 (Java Spring Boot) - 端口 8002
│   ├── manager-web/        # Web管理前端 (Vue 2 + Element UI) - 端口 8001
│   └── manager-mobile/     # 移动端管理 (uni-app + Vue 3) - 跨平台
├── docs/                   # 文档
└── docker-compose*.yml     # Docker部署配置
```

### 组件通信关系

```
ESP32设备 <--WebSocket--> xiaozhi-server <--HTTP--> manager-api
                                                 ↑
manager-web <------HTTP REST API-----------------+
manager-mobile <---HTTP REST API-----------------+
```

---

## 核心组件详解

### 1. xiaozhi-server (Python核心AI引擎)

**技术栈:** Python 3.10+, asyncio, websockets, aiohttp, pytorch, funasr

**入口文件:** `main/xiaozhi-server/app.py`

**核心目录结构:**
```
xiaozhi-server/
├── app.py              # 主入口
├── config.yaml         # 主配置文件
├── core/
│   ├── websocket_server.py   # WebSocket服务器
│   ├── connection.py         # 连接处理器
│   ├── http_server.py        # HTTP服务(OTA/视觉分析)
│   ├── handle/               # 消息处理器
│   │   ├── helloHandle.py
│   │   ├── receiveAudioHandle.py
│   │   ├── textHandle.py
│   │   ├── intentHandler.py
│   │   ├── functionHandler.py
│   │   └── sendAudioHandle.py
│   ├── providers/            # AI服务提供者
│   │   ├── asr/              # 语音识别
│   │   ├── tts/              # 语音合成
│   │   ├── llm/              # 大语言模型
│   │   ├── vllm/             # 视觉语言模型
│   │   ├── vad/              # 语音活动检测
│   │   ├── intent/           # 意图识别
│   │   └── memory/           # 记忆系统
│   └── utils/                # 工具模块
├── plugins_func/             # 插件系统
│   ├── functions/            # 功能插件
│   ├── loadplugins.py
│   └── register.py
└── config/
    ├── settings.py           # 配置加载
    ├── logger.py             # 日志配置
    └── assets/               # 静态资源(提示音等)
```

**启动方式:**
```bash
cd main/xiaozhi-server
pip install -r requirements.txt
python app.py
```

**支持的AI服务:**
- **ASR:** FunASR(本地), SherpaASR, 讯飞流式, 火山引擎, 阿里云, 百度, OpenAI, Groq, Vosk, Qwen3-ASR
- **LLM:** 智谱ChatGLM, 阿里百炼, DeepSeek, 火山豆包, Ollama, Dify, Gemini, Coze, HomeAssistant, FastGPT, Xinference
- **TTS:** EdgeTTS, 火山引擎, 硅基流动, Coze, FishSpeech, GPT-SoVITS, Minimax
- **VLLM:** 智谱GLM-4V, 阿里Qwen-VL

### 2. manager-api (Java管理后端)

**技术栈:** Java 21, Spring Boot 3.4, MyBatis-Plus 3.5, MySQL, Redis, Apache Shiro, Liquibase

**入口文件:** `main/manager-api/src/main/java/xiaozhi/XiaozhiApplication.java`

**核心模块 (modules/):**
- `sys` - 系统管理(用户、角色、权限、日志)
- `agent` - 智能体配置管理
- `device` - 设备管理
- `config` - xiaozhi-server配置提供
- `timbre` - TTS音色管理
- `ota` - OTA固件升级
- `security` - 安全认证

**构建与运行:**
```bash
cd main/manager-api
mvn clean package -DskipTests
java -jar target/xiaozhi-esp32-api.jar
```

**API文档:** 访问 `/xiaozhi/doc.html` 查看Knife4j生成的Swagger文档

### 3. manager-web (Vue Web管理前端)

**技术栈:** Vue 2.6, Vue Router, Vuex, Element UI, SCSS, Axios/Flyio

**入口文件:** `main/manager-web/src/main.js`

**核心目录:**
```
manager-web/src/
├── main.js          # 入口
├── App.vue          # 根组件
├── router/          # 路由配置
├── store/           # Vuex状态管理
├── views/           # 页面组件
├── components/      # 可复用组件
├── apis/            # API封装
├── i18n/            # 国际化
└── styles/          # 样式文件
```

**开发与构建:**
```bash
cd main/manager-web
npm install
npm run serve    # 开发模式
npm run build    # 生产构建
```

### 4. manager-mobile (uni-app移动端)

**技术栈:** uni-app v3, Vue 3.4, Vite 5, Pinia, TypeScript, UnoCSS, alova

**入口文件:** `main/manager-mobile/src/main.ts`

**平台支持:** H5, iOS App, Android App, 微信小程序

**开发与构建:**
```bash
cd main/manager-mobile
pnpm install
pnpm dev          # H5开发
pnpm dev:app      # App开发
pnpm build        # H5构建
pnpm build:app    # App构建
```

---

## 配置说明

### xiaozhi-server配置 (config.yaml)

配置优先级: `data/.config.yaml` > `config.yaml`

**关键配置项:**
```yaml
server:
  ip: 0.0.0.0
  port: 8000           # WebSocket端口
  http_port: 8003      # HTTP端口(OTA/视觉分析)
  websocket: ws://你的ip:8000/xiaozhi/v1/
  vision_explain: http://你的ip:8003/mcp/vision/explain

selected_module:
  VAD: SileroVAD
  ASR: FunASR
  LLM: ChatGLMLLM
  VLLM: ChatGLMVLLM
  TTS: EdgeTTS
  Memory: nomem
  Intent: function_call
```

### 环境变量

- `manager-web`: 使用 `.env.production` 配置API地址
- `manager-mobile`: 使用 `env/.env.production` 配置API地址

---

## 部署方式

### 方式一: Docker单服务部署 (仅xiaozhi-server)
```bash
cd main/xiaozhi-server
docker-compose up -d
```

### 方式二: Docker全模块部署
```bash
cd main/xiaozhi-server
docker-compose -f docker-compose_all.yml up -d
```

### 方式三: 源码部署

1. **xiaozhi-server:**
   ```bash
   cd main/xiaozhi-server
   pip install -r requirements.txt
   python app.py
   ```

2. **manager-api:**
   ```bash
   cd main/manager-api
   mvn clean package
   java -jar target/xiaozhi-esp32-api.jar
   ```

3. **manager-web:**
   ```bash
   cd main/manager-web
   npm install && npm run build
   # 将dist目录部署到Nginx
   ```

---

## 开发规范

### Python代码规范 (xiaozhi-server)
- 使用 `loguru` 进行日志记录，通过 `logger.bind(tag=TAG)` 添加标签
- 异步编程使用 `asyncio`，所有I/O操作应使用异步库
- Provider模式: 所有AI服务提供者继承基类并实现统一接口
- 插件开发: 在 `plugins_func/functions/` 目录添加模块，使用装饰器注册

### Java代码规范 (manager-api)
- 三层架构: Controller -> Service -> DAO(Mapper)
- 使用Lombok减少样板代码
- 使用MyBatis-Plus进行数据库操作
- API使用Knife4j注解生成文档

### 前端代码规范
- Vue 2 Options API (manager-web)
- Vue 3 Composition API (manager-mobile)
- 组件命名: PascalCase
- API调用统一封装在 `apis/` 或 `api/` 目录

---

## 常用命令速查

### xiaozhi-server
```bash
# 启动服务
python app.py

# 性能测试
python performance_tester.py

# 模块测试
python -m pytest test/
```

### manager-api
```bash
# 编译
mvn clean package -DskipTests

# 运行
java -jar target/xiaozhi-esp32-api.jar

# 测试
mvn test
```

### manager-web
```bash
npm run serve    # 开发
npm run build    # 构建
```

### manager-mobile
```bash
pnpm dev         # H5开发
pnpm dev:app     # App开发
pnpm build:mp-weixin  # 微信小程序构建
```

---

## 重要端口

| 服务 | 端口 | 说明 |
|------|------|------|
| xiaozhi-server WebSocket | 8000 | ESP32设备连接 |
| xiaozhi-server HTTP | 8003 | OTA、视觉分析接口 |
| manager-web | 8001 | Web控制台 |
| manager-api | 8002 | 管理API |

---

## 插件开发

在 `plugins_func/functions/` 目录创建新插件:

```python
from plugins_func.register import register_function

@register_function(
    name="my_function",
    description="功能描述",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数说明"}
        },
        "required": ["param1"]
    }
)
async def my_function(param1: str, **kwargs):
    # 实现逻辑
    return {"result": "success"}
```

然后在 `config.yaml` 的 `Intent.function_call.functions` 中添加插件名称启用。

---

## 相关文档

- [部署文档](docs/Deployment.md) - 最简化安装
- [全模块部署](docs/Deployment_all.md) - 完整功能安装
- [常见问题](docs/FAQ.md)
- [Home Assistant集成](docs/homeassistant-integration.md)
- [MCP接入点集成](docs/mcp-endpoint-integration.md)
- [声纹识别集成](docs/voiceprint-integration.md)
- [小智通信协议](https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh)

---

## 测试环境

项目提供公开测试环境:
- 智控台: https://2662r3426b.vicp.fun
- 智控台H5: https://2662r3426b.vicp.fun/h5/index.html
- 服务测试工具: https://2662r3426b.vicp.fun/test/
- API文档: https://2662r3426b.vicp.fun/xiaozhi/doc.html

---

## 许可证

MIT License
