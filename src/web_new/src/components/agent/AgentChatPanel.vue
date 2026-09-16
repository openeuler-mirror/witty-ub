<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useAgentChat } from '../../composables/useAgentChat'
import { renderAgentMarkdown } from '../../utils/agentMarkdown'
import type { LogKnowledge } from '../../types'

const props = defineProps<{ asset: LogKnowledge | null }>()

const {
  view,
  connectionState,
  connectionError,
  isLoggingIn,
  remoteUsername,
  remotePassword,
  remoteAddress,
  connectedModels,
  providerNames,
  selectedModel,
  providerApiKey,
  isAuthorizing,
  modelSearch,
  providerSearch,
  expandedProviderId,
  sessionStatuses,
  sessionId,
  isSessionsLoading,
  isHistoryLoading,
  isHistoryFailed,
  isSessionCreating,
  isSessionSaving,
  isSubmitting,
  sessionSearch,
  messages,
  input,
  isSending,
  sessionDialog,
  sessionTitleInput,
  sessionDialogError,
  messagesRef,
  filteredSessions,
  activeSessionTitle,
  filteredModels,
  filteredProviders,
  displayPartsOf,
  setAsset,
  restore,
  loginLocalAgent,
  loginRemoteAgent,
  authorizeProvider,
  refreshSessions,
  openConversation,
  newConversation,
  showSessionDialog,
  submitSessionDialog,
  abortAgentSession,
  suspend,
  sendMessage,
  scrollToBottom,
  sessionAssetName,
  selectModel,
  goBack,
} = useAgentChat()

const open = ref(false)
const fabRef = ref<HTMLButtonElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const tintRef = ref<HTMLElement | null>(null)

/* ===== FAB ↔ 面板变形（点击按钮展开为 Agent 窗口）=====
   面板与 FAB 都是 right/bottom 定位、右下角共点，CSS 里 transform-origin 也是 right bottom，
   所以「折叠态」只要按两个方向的尺寸比 scale、再 translate 补齐右下角偏差，
   就能精确落在按钮矩形上（位置/尺寸/圆角都对得上），动画结束后撤销覆盖样式，
   面板回到常规尺寸（包含用户拖拽缩放后的尺寸）。 */
const PANEL_RADIUS = 22
const MORPH_OPEN_MS = 420
const MORPH_CLOSE_MS = 300
const MORPH_TINT_OPEN_MS = 210
const MORPH_EASE_OUT = 'cubic-bezier(0.16, 1, 0.3, 1)'
const MORPH_EASE_IN = 'cubic-bezier(0.4, 0, 0.2, 1)'

// 变形期间 FAB 让位（面板从按钮处长出并盖住它），关闭动画结束时再显示
const fabHidden = ref(false)
let morphAnimation: Animation | undefined
let tintAnimation: Animation | undefined
let morphing = false

// 面板可拖拽缩放（上/左/左上角手柄）
const panelSize = reactive<{ width: number | null; height: number | null }>({
  width: null,
  height: null,
})
const panelStyle = computed(() => ({
  ...(panelSize.width === null ? {} : { width: `${panelSize.width}px` }),
  ...(panelSize.height === null ? {} : { height: `${panelSize.height}px` }),
}))
let panelResize:
  | {
      direction: 'top' | 'left' | 'corner'
      startX: number
      startY: number
      width: number
      height: number
    }
  | undefined

const resizePanel = (event: PointerEvent) => {
  if (!panelResize) return
  // 面板右下角固定在 FAB 处（right 28 / bottom 26），左/上各留 16px 让拖拽有边界
  const maxWidth = Math.max(320, window.innerWidth - 44)
  const maxHeight = Math.max(320, window.innerHeight - 42)
  const minWidth = Math.min(760, maxWidth)
  const minHeight = Math.min(520, maxHeight)
  if (panelResize.direction !== 'top') {
    panelSize.width = Math.min(
      maxWidth,
      Math.max(minWidth, panelResize.width + panelResize.startX - event.clientX),
    )
  }
  if (panelResize.direction !== 'left') {
    panelSize.height = Math.min(
      maxHeight,
      Math.max(minHeight, panelResize.height + panelResize.startY - event.clientY),
    )
  }
}

const stopPanelResize = () => {
  if (!panelResize) return
  panelResize = undefined
  document.body.classList.remove(
    'agent-panel-resizing',
    'agent-panel-resizing-top',
    'agent-panel-resizing-left',
    'agent-panel-resizing-corner',
  )
  window.removeEventListener('pointermove', resizePanel)
  window.removeEventListener('pointerup', stopPanelResize)
  window.removeEventListener('pointercancel', stopPanelResize)
}

const prefersReducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true

// 半径是椭圆写法（水平 垂直）：折叠时按两个方向的缩放比分别换算，
// 观感上圆角与按钮一致（单值半径在非等比缩放下会变成扁圆）
const cornerRadiusFrame = (radiusX: number, radiusY: number) => ({
  borderTopLeftRadius: `${radiusX}px ${radiusY}px`,
  borderTopRightRadius: `${radiusX}px ${radiusY}px`,
  borderBottomRightRadius: `${radiusX}px ${radiusY}px`,
  borderBottomLeftRadius: `${radiusX}px ${radiusY}px`,
})

// 折叠帧：面板缩成 FAB 的矩形（位置/尺寸/圆角都对得上按钮）
const collapseFrame = (): Keyframe | null => {
  const panel = panelRef.value
  const fab = fabRef.value
  if (!panel || !fab) return null
  const panelRect = panel.getBoundingClientRect()
  const fabRect = fab.getBoundingClientRect()
  if (panelRect.width < 1 || panelRect.height < 1 || fabRect.width < 1) return null
  const scaleX = fabRect.width / panelRect.width
  const scaleY = fabRect.height / panelRect.height
  return {
    transform: `translate(${fabRect.right - panelRect.right}px, ${
      fabRect.bottom - panelRect.bottom
    }px) scale(${scaleX}, ${scaleY})`,
    ...cornerRadiusFrame(
      Math.min(9999, PANEL_RADIUS / scaleX),
      Math.min(9999, PANEL_RADIUS / scaleY),
    ),
  }
}

const panelFrame = (): Keyframe => ({
  transform: 'translate(0px, 0px) scale(1, 1)',
  ...cornerRadiusFrame(PANEL_RADIUS, PANEL_RADIUS),
})

// 面板补间（尺寸/圆角）+ 按钮色罩补间（渐变→白/白→渐变）同时起跑
const runMorph = (
  frames: Keyframe[],
  duration: number,
  easing: string,
  tint: { from: number; to: number; duration: number; easing: string },
) => {
  const panel = panelRef.value
  if (!panel || typeof panel.animate !== 'function') return null
  morphAnimation?.cancel()
  tintAnimation?.cancel()
  morphAnimation = panel.animate(frames, { duration, easing, fill: 'backwards' })
  const tintEl = tintRef.value
  if (tintEl) {
    tintAnimation = tintEl.animate([{ opacity: tint.from }, { opacity: tint.to }], {
      duration: tint.duration,
      easing: tint.easing,
      fill: 'backwards',
    })
  }
  return morphAnimation
}

const cancelMorph = () => {
  morphAnimation?.cancel()
  tintAnimation?.cancel()
  morphAnimation = undefined
  tintAnimation = undefined
}

const startPanelResize = (direction: 'top' | 'left' | 'corner', event: PointerEvent) => {
  const panel = panelRef.value
  if (!panel) return
  event.preventDefault()
  const bounds = panel.getBoundingClientRect()
  panelResize = {
    direction,
    startX: event.clientX,
    startY: event.clientY,
    width: bounds.width,
    height: bounds.height,
  }
  document.body.classList.add('agent-panel-resizing')
  document.body.classList.add(`agent-panel-resizing-${direction}`)
  window.addEventListener('pointermove', resizePanel)
  window.addEventListener('pointerup', stopPanelResize)
  window.addEventListener('pointercancel', stopPanelResize)
}

// 切资产：登记当前资产并重置会话视角
const syncAsset = () =>
  setAsset(props.asset ? { id: props.asset.id, name: props.asset.name } : null)

// 点按钮：面板从按钮矩形长出（折叠帧 → 常规帧），按钮在变形期间让位，屏幕不再同时摆按钮和窗口
const openPanel = () => {
  if (open.value || morphing) return
  morphing = true
  syncAsset()
  restoreOnce()
  open.value = true
  fabHidden.value = true
  void scrollToBottom()
  void nextTick(() => {
    panelRef.value?.focus()
    const collapsed = prefersReducedMotion() ? null : collapseFrame()
    const animation = collapsed
      ? runMorph([collapsed, panelFrame()], MORPH_OPEN_MS, MORPH_EASE_OUT, {
          from: 1,
          to: 0,
          duration: MORPH_TINT_OPEN_MS,
          easing: 'linear',
        })
      : null
    if (!animation) {
      morphing = false
      return
    }
    void animation.finished
      .then(() => cancelMorph())
      .catch(() => {})
      .finally(() => {
        morphing = false
      })
  })
}

// 关闭：面板收回按钮矩形，落位后再把 FAB 显示出来（两者同形，交接无跳变）
const closePanel = () => {
  if (!open.value || morphing) return
  morphing = true
  const collapsed = prefersReducedMotion() ? null : collapseFrame()
  const animation = collapsed
    ? runMorph([panelFrame(), collapsed], MORPH_CLOSE_MS, MORPH_EASE_IN, {
        from: 0,
        to: 1,
        duration: MORPH_CLOSE_MS,
        easing: 'ease-in',
      })
    : null
  const finish = () => {
    cancelMorph()
    open.value = false
    fabHidden.value = false
    morphing = false
    void nextTick(() => fabRef.value?.focus())
  }
  if (!animation) {
    finish()
    return
  }
  void animation.finished.then(finish).catch(() => {})
}

let restored = false
const restoreOnce = () => {
  if (restored) return
  restored = true
  void restore()
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Escape' || !open.value) return
  closePanel()
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  syncAsset()
  restoreOnce()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  stopPanelResize()
  cancelMorph()
  suspend()
})

const statusLabelOf = () =>
  connectionState.value === 'connected'
    ? '已连接'
    : connectionState.value === 'connecting'
      ? '连接中'
      : '未连接'

// 显示 Provider 名（OpenCode Zen）而非 providerID（opencode）
const providerNameOf = (providerID: string) => providerNames.value[providerID] || providerID

const currentModelLabel = () => {
  const selected = selectedModel.value
  if (!selected) return '未选择模型'
  const model = connectedModels.value.find(
    (item) => item.providerID === selected.providerID && item.id === selected.modelID,
  )
  return `${providerNameOf(selected.providerID)} · ${model?.name ?? selected.modelID}`
}

const onInputKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendMessage()
  }
}
</script>

<template>
  <!-- FAB：仅分析页挂载（App.vue 控制挂载时机）；打开时它变成面板，所以变形期间隐藏自己 -->
  <button
    ref="fabRef"
    :class="['agent-fab', { 'agent-fab-hidden': fabHidden }]"
    type="button"
    title="AI 故障诊断助手"
    :aria-label="open ? '关闭 AI 故障诊断助手' : '打开 AI 故障诊断助手'"
    :aria-expanded="open"
    aria-controls="agent-chat-panel"
    @click="openPanel"
  >
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <path d="M32 8v7" />
      <circle cx="32" cy="6" r="3" />
      <rect x="12" y="16" width="40" height="34" rx="12" />
      <circle cx="24" cy="31" r="3.5" />
      <circle cx="40" cy="31" r="3.5" />
      <path d="M23 41c5 4 13 4 18 0M12 29H7v11h5M52 29h5v11h-5M24 50v6M40 50v6" />
    </svg>
    <span
      v-if="!fabHidden"
      class="agent-fab-pulse"
      :class="{ disconnected: connectionState !== 'connected' }"
      aria-hidden="true"
    ></span>
  </button>

  <aside
    v-if="open"
    id="agent-chat-panel"
    ref="panelRef"
    class="agent-chat-panel"
    :style="panelStyle"
    role="dialog"
    aria-modal="true"
    aria-label="AI 故障诊断助手"
    tabindex="-1"
  >
    <div
      class="agent-panel-resize-handle agent-panel-resize-top"
      aria-hidden="true"
      @pointerdown="startPanelResize('top', $event)"
    ></div>
    <div
      class="agent-panel-resize-handle agent-panel-resize-left"
      aria-hidden="true"
      @pointerdown="startPanelResize('left', $event)"
    ></div>
    <div
      class="agent-panel-resize-handle agent-panel-resize-corner"
      aria-hidden="true"
      @pointerdown="startPanelResize('corner', $event)"
    ></div>
    <header class="agent-chat-header">
      <button
        v-if="view !== 'login' && view !== 'chat'"
        class="agent-auth-back"
        type="button"
        aria-label="返回上一级"
        @click="goBack"
      >
        ‹
      </button>
      <div class="agent-chat-heading">
        <span
          class="agent-chat-status"
          :class="{ disconnected: connectionState !== 'connected' }"
          :title="statusLabelOf()"
          :aria-label="'连接状态：' + statusLabelOf()"
          role="status"
        ></span>
        <div>
          <strong>AI 故障诊断助手</strong>
          <span v-if="view === 'chat'">当前模型：{{ currentModelLabel() }}</span>
          <span v-else>时延与通断故障分析</span>
        </div>
      </div>
      <div class="agent-session-header-actions">
        <button
          v-if="view === 'chat'"
          type="button"
          class="agent-model-switch"
          title="切换当前会话使用的模型"
          @click="view = 'models'"
        >
          <span aria-hidden="true">⇄</span>
          模型切换
        </button>
        <button type="button" title="关闭" aria-label="关闭 AI 故障诊断助手" @click="closePanel">
          ✕
        </button>
      </div>
    </header>

    <div v-if="connectionError && view !== 'chat'" class="agent-chat-error" role="alert">
      {{ connectionError }}
    </div>

    <!-- ===== 登录视图 ===== -->
    <main v-if="view === 'login'" class="agent-auth-page">
      <div class="agent-auth-intro">
        <span class="agent-chat-welcome-icon" aria-hidden="true">✦</span>
        <h3>连接 OpenCode</h3>
        <p>选择本地服务器，或使用登录信息连接远程服务器。</p>
      </div>
      <div class="agent-auth-connectors">
        <button
          class="agent-auth-local"
          type="button"
          :disabled="isLoggingIn || connectionState === 'connecting'"
          @click="loginLocalAgent"
        >
          <strong>连接到本机 OpenCode 服务器</strong>
          <span>127.0.0.1:4096 · 无需用户名和密码</span>
        </button>
        <form class="agent-auth-form agent-auth-remote" @submit.prevent="loginRemoteAgent">
          <div class="agent-auth-remote-title">
            <strong>远程连接</strong>
            <span>使用远程服务器的登录信息</span>
          </div>
          <label>
            <span>用户名</span>
            <input
              v-model.trim="remoteUsername"
              autocomplete="username"
              placeholder="请输入用户名"
            />
          </label>
          <label>
            <span>密码</span>
            <input
              v-model="remotePassword"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
            />
          </label>
          <label>
            <span>URL</span>
            <input
              v-model.trim="remoteAddress"
              autocomplete="url"
              placeholder="远程服务器的 IP:端口号"
            />
          </label>
          <button class="agent-auth-primary" type="submit" :disabled="isLoggingIn">
            {{ isLoggingIn ? '连接中…' : '连接远程服务器' }}
          </button>
        </form>
      </div>
    </main>

    <!-- ===== 模型视图 ===== -->
    <main v-else-if="view === 'models'" class="agent-auth-page agent-selection-page">
      <div class="agent-selection-title">
        <div>
          <h3>选择大模型</h3>
          <p>选择一个已连接的模型开始诊断。</p>
        </div>
        <button class="agent-add-provider" type="button" @click="view = 'providers'">
          ＋ 新增
        </button>
      </div>
      <input
        v-model="modelSearch"
        class="agent-search"
        placeholder="搜索模型 / Provider"
        aria-label="搜索模型 / Provider"
      />
      <div class="agent-option-list">
        <button
          v-for="model in filteredModels"
          :key="model.providerID + '/' + model.id"
          type="button"
          class="agent-model-option"
          :class="{
            active:
              selectedModel?.providerID === model.providerID && selectedModel?.modelID === model.id,
          }"
          @click="selectModel(model.providerID, model.id)"
        >
          <span>{{ model.name }}</span>
          <small>{{ providerNameOf(model.providerID) }}</small>
        </button>
        <p v-if="filteredModels.length === 0" class="agent-empty-options">没有找到已连接的模型</p>
      </div>
    </main>

    <!-- ===== Provider / API key 视图 ===== -->
    <main v-else-if="view === 'providers'" class="agent-auth-page agent-selection-page">
      <div class="agent-selection-title">
        <div>
          <h3>添加提供商</h3>
          <p>选择提供商并输入 API key。</p>
        </div>
      </div>
      <input
        v-model="providerSearch"
        class="agent-search"
        placeholder="搜索 Provider"
        aria-label="搜索 Provider"
      />
      <div class="agent-option-list">
        <section
          v-for="provider in filteredProviders"
          :key="provider.id"
          class="agent-provider-option"
        >
          <button
            type="button"
            class="agent-provider-toggle"
            :aria-expanded="expandedProviderId === provider.id"
            @click="expandedProviderId = expandedProviderId === provider.id ? '' : provider.id"
          >
            <span>{{ provider.name }}</span>
            <span aria-hidden="true">{{ expandedProviderId === provider.id ? '▾' : '▸' }}</span>
          </button>
          <form
            v-if="expandedProviderId === provider.id"
            class="agent-api-key-form"
            @submit.prevent="authorizeProvider(provider.id)"
          >
            <input
              type="password"
              v-model="providerApiKey"
              :placeholder="provider.name + ' API Key'"
              autocomplete="off"
              aria-label="API key"
            />
            <button
              class="agent-api-key-submit"
              type="submit"
              :disabled="!providerApiKey || isAuthorizing"
            >
              {{ isAuthorizing ? '认证中' : '认证' }}
            </button>
          </form>
        </section>
        <p v-if="filteredProviders.length === 0" class="agent-empty-options">
          暂无需要配置的 Provider
        </p>
      </div>
    </main>

    <!-- ===== 会话视图 ===== -->
    <div v-else class="agent-conversation-layout">
      <aside class="agent-session-manager" aria-label="会话列表">
        <div class="agent-session-manager-title">
          <div>
            <strong>会话</strong>
          </div>
          <button
            type="button"
            :disabled="isSessionCreating || isSessionSaving || isSubmitting"
            @click="newConversation"
          >
            {{ isSessionCreating ? '创建中…' : '＋ 新建' }}
          </button>
        </div>
        <button
          type="button"
          class="agent-session-refresh"
          :disabled="isSessionsLoading || isSessionCreating || isSessionSaving"
          @click="refreshSessions"
        >
          刷新会话列表
        </button>
        <input
          v-model.trim="sessionSearch"
          class="agent-search"
          placeholder="搜索会话标题或资产库名称"
          aria-label="搜索会话标题或资产库名称"
        />
        <div class="agent-session-list">
          <p v-if="isSessionsLoading" class="agent-empty-options">正在加载会话…</p>
          <template v-else>
            <article
              v-for="session in filteredSessions"
              :key="session.id"
              class="agent-session-item"
              :class="{ active: session.id === sessionId }"
              :title="session.title || '无标题会话'"
            >
              <button
                class="agent-session-open"
                type="button"
                :disabled="isSessionCreating || isSessionSaving || isSubmitting"
                :aria-current="session.id === sessionId ? 'true' : undefined"
                @click="openConversation(session.id)"
              >
                <strong>{{ session.title || '无标题会话' }}</strong>
                <span>{{ sessionAssetName(session.id) || '未知资产库' }}</span>
                <span>{{
                  sessionStatuses[session.id]?.type === 'busy'
                    ? '正在回答'
                    : sessionStatuses[session.id]?.type === 'retry'
                      ? '正在重试连接'
                      : session.time?.updated
                        ? new Date(session.time.updated).toLocaleString()
                        : '刚刚创建'
                }}</span>
              </button>
              <div class="agent-session-item-actions">
                <button
                  type="button"
                  title="修改标题"
                  :aria-label="'重命名会话 ' + (session.title || '无标题会话')"
                  :disabled="isSessionSaving || isSubmitting"
                  @click="showSessionDialog('rename', session)"
                >
                  ✎
                </button>
                <button
                  type="button"
                  title="删除会话"
                  :aria-label="'删除会话 ' + (session.title || '无标题会话')"
                  :disabled="isSessionSaving || isSubmitting"
                  @click="showSessionDialog('delete', session)"
                >
                  ×
                </button>
              </div>
            </article>
            <p v-if="filteredSessions.length === 0" class="agent-empty-options">没有找到会话</p>
          </template>
        </div>
      </aside>

      <div class="agent-conversation-main">
        <div class="agent-conversation-context">
          <strong>{{ activeSessionTitle }}</strong>
          <span>{{
            sessionId
              ? sessionAssetName(sessionId) || '未关联资产'
              : props.asset?.name || '未选择资产'
          }}</span>
        </div>
        <form
          v-if="sessionDialog"
          class="agent-session-dialog"
          role="dialog"
          :aria-label="sessionDialog.kind === 'rename' ? '重命名会话' : '删除会话'"
          @submit.prevent="submitSessionDialog"
          @keydown.esc="!isSessionSaving && (sessionDialog = null)"
        >
          <strong>{{ sessionDialog.kind === 'rename' ? '重命名会话' : '删除会话' }}</strong>
          <label v-if="sessionDialog.kind === 'rename'">
            会话标题
            <input
              v-model="sessionTitleInput"
              aria-label="会话标题"
              maxlength="200"
              :disabled="isSessionSaving"
            />
          </label>
          <p v-else>
            确认删除「{{
              sessionDialog.session.title || '无标题会话'
            }}」及其历史消息？正在运行的回答会先停止，此操作无法撤销。
          </p>
          <p v-if="sessionDialogError" class="agent-message-error" role="alert">
            {{ sessionDialogError }}
          </p>
          <div>
            <button type="button" :disabled="isSessionSaving" @click="sessionDialog = null">
              取消
            </button>
            <button type="submit" :disabled="isSessionSaving">
              {{
                isSessionSaving
                  ? '保存中…'
                  : sessionDialog.kind === 'rename'
                    ? '保存标题'
                    : '确认删除'
              }}
            </button>
          </div>
        </form>
        <div ref="messagesRef" class="agent-chat-messages" aria-live="polite">
          <p v-if="isHistoryLoading" class="agent-empty-options">正在加载历史消息…</p>
          <div v-else-if="messages.length === 0" class="agent-chat-welcome">
            <span class="agent-chat-welcome-icon" aria-hidden="true">✦</span>
            <strong>你好，我是故障诊断助手</strong>
            <p>可以问我当前资产库的时延异常、通断故障或故障码根因。</p>
          </div>
          <template v-else>
            <article
              v-for="message in messages"
              :key="message.id"
              class="agent-chat-message"
              :class="message.role"
            >
              <div v-if="message.role === 'assistant'" class="agent-chat-avatar" aria-hidden="true">
                AI
              </div>
              <div class="agent-chat-bubble">
                <!-- 用户消息为纯文本，继承气泡白字 -->
                <template v-if="message.role === 'user'">
                  <p v-for="part in displayPartsOf(message)" :key="part.id">{{ part.text }}</p>
                </template>
                <template v-else>
                  <template v-for="part in displayPartsOf(message)" :key="part.id">
                    <section v-if="part.type === 'reasoning'" class="agent-reasoning">
                      <button
                        type="button"
                        class="agent-response-label agent-reasoning-toggle"
                        :aria-expanded="!part.collapsed"
                        @click="part.collapsed = !part.collapsed"
                      >
                        <span>思考过程</span>
                        <span
                          v-if="message.status === 'thinking'"
                          class="agent-thinking-dots"
                          aria-label="思考中"
                        >
                          <i></i><i></i><i></i>
                        </span>
                        <span class="agent-reasoning-chevron" aria-hidden="true">⌄</span>
                      </button>
                      <div v-show="!part.collapsed">
                        <p v-if="part.text">{{ part.text }}</p>
                        <p v-else class="agent-reasoning-placeholder">正在分析问题并查询诊断数据</p>
                      </div>
                    </section>
                    <section v-else class="agent-final-answer">
                      <div class="agent-markdown" v-html="renderAgentMarkdown(part.text)"></div>
                    </section>
                  </template>
                </template>
                <p v-if="message.status === 'error'" class="agent-message-error">响应失败</p>
              </div>
            </article>
          </template>
        </div>

        <div v-if="connectionError" class="agent-chat-error" role="alert">
          {{ connectionError }}
          <button
            v-if="isHistoryFailed && sessionId"
            type="button"
            @click="openConversation(sessionId)"
          >
            重新加载会话
          </button>
        </div>

        <form class="agent-chat-composer" @submit.prevent="sendMessage">
          <textarea
            v-model="input"
            rows="1"
            aria-label="输入诊断问题"
            placeholder="输入你想诊断的问题…"
            :disabled="
              isSending ||
              isHistoryLoading ||
              isHistoryFailed ||
              isSessionCreating ||
              isSessionSaving
            "
            @keydown="onInputKeydown"
          ></textarea>
          <button
            v-if="!isSending"
            type="submit"
            title="发送消息"
            aria-label="发送消息"
            :disabled="
              !input.trim() ||
              isHistoryLoading ||
              isHistoryFailed ||
              isSessionCreating ||
              isSessionSaving ||
              isSubmitting
            "
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="m4 4 17 8-17 8 3-8-3-8Zm3.8 7h7.4L7 7.1 7.8 11Zm-.8 5.9 8.2-3.9H7.8L7 16.9Z"
              />
            </svg>
          </button>
          <button
            v-else
            type="button"
            class="stop"
            title="停止本次会话"
            aria-label="停止本次会话"
            @click="abortAgentSession"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="7" y="7" width="10" height="10" rx="2" />
            </svg>
          </button>
        </form>
      </div>
    </div>

    <!-- 按钮色罩：变形首帧完全覆盖面板（渐变与按钮一致），随生长淡出把窗口化开 -->
    <span ref="tintRef" class="agent-panel-morph-tint" aria-hidden="true"></span>
  </aside>
</template>

<style scoped>
/* 主样式表缺 button/input 基础重置会露出 UA 黑框；
   :where() 降到 0 权重，避免压过下面的按钮配色 */
:where(.agent-chat-panel) :where(button, input, textarea),
.agent-fab {
  font: inherit;
}
:where(.agent-chat-panel) button {
  border: 0;
  background: transparent;
  color: inherit;
}
:where(.agent-chat-panel) input,
:where(.agent-chat-panel) textarea {
  color: #1e293b;
}
.agent-fab {
  position: fixed;
  right: 28px;
  bottom: 26px;
  /* 低于面板（119）：面板从按钮处展开时正好盖住它，读起来就是「按钮变成了窗口」 */
  z-index: 118;
  display: grid;
  width: 62px;
  height: 62px;
  place-items: center;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 22px;
  background: linear-gradient(145deg, #4f8cff, #4f46e5);
  box-shadow:
    0 16px 35px rgba(37, 99, 235, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  color: #fff;
  transition:
    transform 0.2s ease,
    border-radius 0.2s ease,
    box-shadow 0.2s ease,
    opacity 0.16s ease;
}
.agent-fab:hover {
  transform: translateY(-3px);
  box-shadow:
    0 20px 42px rgba(37, 99, 235, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}
/* 变形期间直接让位（transition: none，避免和面板的变形动画抢视觉），
   收拢结束摘掉类名时用上面的 opacity 过渡淡入 */
.agent-fab-hidden {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  transition: none;
}
.agent-fab svg {
  width: 38px;
  height: 38px;
  overflow: visible;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2.5;
}
.agent-fab-pulse {
  position: absolute;
  right: -2px;
  top: -2px;
  width: 14px;
  height: 14px;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.6);
  animation: agent-pulse 2s infinite;
}
.agent-fab-pulse.disconnected {
  background: #ef4444;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.55);
  animation-name: agent-pulse-danger;
}
.agent-chat-panel {
  position: fixed;
  /* 右下角与 FAB 共点（right/bottom 同值）：面板直接占用按钮位置，不再为按钮预留下方空间 */
  right: 28px;
  bottom: 26px;
  z-index: 119;
  display: flex;
  overflow: hidden;
  /* 阻断滚动链：面板头部/会话区顶栏/输入区都不是滚动容器，
     没有这一条时滚轮会沿祖先链交给文档，把面板背后的页面滚走 */
  overscroll-behavior: contain;
  width: min(1240px, calc(100vw - 44px));
  height: min(880px, calc(100vh - 42px));
  max-width: calc(100vw - 44px);
  max-height: calc(100vh - 42px);
  min-width: min(760px, calc(100vw - 44px));
  min-height: min(520px, calc(100vh - 42px));
  flex-direction: column;
  border: 1px solid rgba(203, 213, 225, 0.86);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 28px 70px rgba(15, 23, 42, 0.2),
    0 8px 24px rgba(59, 130, 246, 0.1);
  /* 变形原点：面板从右下角（按钮处）长出/收回，JS 的 transform 依赖这个原点 */
  transform-origin: right bottom;
}
/* 与 FAB 同款渐变，静态不透明度为 0（只在变形期间由 JS 补间），
   因此面板平时不会多出一层色罩 */
.agent-panel-morph-tint {
  position: absolute;
  z-index: 5;
  inset: 0;
  background: linear-gradient(145deg, #4f8cff, #4f46e5);
  opacity: 0;
  pointer-events: none;
}
.agent-panel-resize-handle {
  position: absolute;
  z-index: 4;
  touch-action: none;
}
.agent-panel-resize-top {
  top: 0;
  right: 14px;
  left: 14px;
  height: 8px;
  cursor: ns-resize;
}
.agent-panel-resize-left {
  top: 14px;
  bottom: 14px;
  left: 0;
  width: 8px;
  cursor: ew-resize;
}
.agent-panel-resize-corner {
  top: 0;
  left: 0;
  width: 18px;
  height: 18px;
  cursor: nwse-resize;
}
:global(body.agent-panel-resizing) {
  user-select: none;
}
:global(body.agent-panel-resizing-top) {
  cursor: ns-resize;
}
:global(body.agent-panel-resizing-left) {
  cursor: ew-resize;
}
:global(body.agent-panel-resizing-corner) {
  cursor: nwse-resize;
}
.agent-chat-header {
  display: flex;
  min-height: 74px;
  align-items: center;
  padding: 15px 19px;
  border-bottom: 1px solid #e8edf5;
  background:
    radial-gradient(circle at 90% -40%, rgba(96, 165, 250, 0.3), transparent 55%),
    linear-gradient(135deg, #f8fbff, #f5f3ff);
}
.agent-auth-back {
  width: 34px;
  height: 34px;
  margin-right: 10px;
  cursor: pointer;
  border-radius: 10px;
  background: #eaf1ff;
  color: #315ecf;
  font-size: 1.7rem;
  line-height: 1;
}
.agent-chat-heading {
  display: flex;
  align-items: center;
  gap: 11px;
}
.agent-chat-heading > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.agent-chat-heading strong {
  color: #172554;
  font-size: 0.96rem;
}
.agent-chat-heading span:not(.agent-chat-status) {
  color: #64748b;
  font-size: 0.75rem;
}
.agent-chat-status {
  width: 10px;
  height: 10px;
  flex: 0 0 10px;
  border: 2px solid #d1fae5;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1);
}
.agent-chat-status.disconnected {
  border-color: #fee2e2;
  background: #ef4444;
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.12);
}
.agent-session-header-actions {
  display: flex;
  margin-left: auto;
  gap: 7px;
}
.agent-session-header-actions button,
.agent-session-item-actions button {
  display: grid;
  width: 32px;
  height: 32px;
  cursor: pointer;
  place-items: center;
  border: 1px solid #d7e1f1;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.75);
  color: #475569;
  font-size: 1rem;
}
.agent-session-header-actions .agent-model-switch {
  display: inline-flex;
  width: auto;
  align-items: center;
  padding: 0 13px;
  gap: 6px;
  font-size: 0.78rem;
  font-weight: 700;
}
.agent-session-header-actions button:hover,
.agent-session-item-actions button:hover {
  border-color: #9ab7f5;
  background: #eaf1ff;
  color: #315ecf;
}

/* ===== 登录 / 模型 / Provider 视图 ===== */
.agent-auth-page {
  min-height: 0;
  flex: 1;
  padding: 28px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.agent-auth-intro {
  margin: 8px 0 24px;
  text-align: center;
}
.agent-chat-welcome-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  margin: 0 auto 12px;
  border-radius: 17px;
  background: linear-gradient(145deg, #dbeafe, #ede9fe);
  color: #4f46e5;
  font-size: 1.5rem;
}
.agent-auth-intro h3,
.agent-selection-title h3 {
  margin: 0;
  color: #172554;
  font-size: 1.1rem;
}
.agent-auth-intro p,
.agent-selection-title p {
  margin: 7px 0 0;
  color: #64748b;
  font-size: 0.8rem;
}
.agent-auth-connectors {
  display: grid;
  max-width: 410px;
  margin: 0 auto;
  gap: 18px;
}
.agent-auth-local {
  display: grid;
  width: 100%;
  padding: 17px 18px;
  cursor: pointer;
  border: 1px solid #60a5fa;
  border-radius: 14px;
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.24);
  color: #fff;
  gap: 5px;
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}
.agent-auth-local:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.32);
}
.agent-auth-local strong {
  font-size: 0.95rem;
}
.agent-auth-local span {
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.75rem;
}
.agent-auth-remote {
  padding: 18px;
  border: 1px solid #dbe3ef;
  border-radius: 14px;
  background: #f8fafc;
}
.agent-auth-remote-title {
  display: grid;
  padding-bottom: 13px;
  border-bottom: 1px solid #e2e8f0;
  color: #24324a;
  gap: 3px;
}
.agent-auth-remote-title span {
  color: #7c8aa0;
  font-size: 0.75rem;
}
.agent-auth-form {
  display: grid;
  gap: 16px;
}
.agent-auth-form label {
  display: grid;
  gap: 7px;
  color: #334155;
  font-size: 0.8rem;
  font-weight: 600;
}
.agent-auth-form input,
.agent-search,
.agent-api-key-form input {
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border: 1px solid #dbe3ef;
  border-radius: 11px;
  outline: none;
  background: #fff;
  color: #1e293b;
}
.agent-auth-form input:focus,
.agent-search:focus,
.agent-api-key-form input:focus {
  border-color: #739cff;
  box-shadow: 0 0 0 3px rgba(79, 140, 255, 0.12);
}
.agent-auth-primary,
.agent-add-provider,
.agent-api-key-submit {
  cursor: pointer;
  border-radius: 11px;
  background: linear-gradient(145deg, #4f8cff, #4f46e5);
  color: #fff;
  font-weight: 700;
}
.agent-auth-primary {
  height: 43px;
  margin-top: 4px;
}
.agent-auth-local:disabled,
.agent-auth-primary:disabled,
.agent-api-key-submit:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.agent-selection-page {
  display: flex;
  flex-direction: column;
}
.agent-selection-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  gap: 16px;
}
.agent-add-provider {
  padding: 9px 13px;
}
.agent-search {
  flex: 0 0 42px;
  margin-bottom: 14px;
  background: #f8fafc;
}
.agent-option-list {
  display: grid;
  gap: 9px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.agent-model-option,
.agent-provider-option {
  border: 1px solid #e4eaf3;
  border-radius: 12px;
  background: #fff;
}
.agent-model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 15px;
  cursor: pointer;
  color: #24324a;
  text-align: left;
}
.agent-model-option:hover,
.agent-provider-option:hover {
  border-color: #b9cdfb;
  background: #f8fbff;
}
.agent-model-option.active {
  border-color: #91aff0;
  box-shadow: 0 0 0 2px rgba(79, 111, 232, 0.08);
}
.agent-model-option small {
  color: #7c8aa0;
}
.agent-provider-option > button {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  padding: 13px 15px;
  cursor: pointer;
  background: transparent;
  color: #24324a;
  text-align: left;
}
.agent-api-key-form {
  display: flex;
  gap: 8px;
  padding: 0 12px 12px;
}
.agent-api-key-submit {
  min-width: 66px;
}
.agent-empty-options {
  padding: 30px 0;
  color: #94a3b8;
  text-align: center;
}

/* ===== 会话视图 ===== */
.agent-conversation-layout {
  display: flex;
  min-height: 0;
  flex: 1;
}
.agent-session-manager {
  display: flex;
  min-height: 0;
  width: 270px;
  flex: 0 0 270px;
  flex-direction: column;
  padding: 16px 14px;
  border-right: 1px solid #e1e8f2;
  background: #f8fafc;
}
.agent-session-manager-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
}
.agent-session-manager-title > div {
  display: grid;
  color: #172554;
  gap: 3px;
}
.agent-session-manager-title > button {
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 9px;
  background: #4f6fe8;
  color: #fff;
}
.agent-session-refresh {
  margin-bottom: 12px;
  padding: 6px;
  background: transparent;
  color: #315ecf;
  cursor: pointer;
}
.agent-session-list {
  display: grid;
  min-height: 0;
  align-content: start;
  gap: 9px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.agent-session-item {
  display: flex;
  align-items: center;
  padding: 8px 9px 8px 13px;
  border: 1px solid #e1e8f2;
  border-radius: 12px;
  background: #fff;
  gap: 9px;
}
.agent-session-item.active {
  border-color: #91aff0;
  box-shadow: 0 0 0 2px rgba(79, 111, 232, 0.08);
}
.agent-session-open {
  display: grid;
  min-width: 0;
  flex: 1;
  cursor: pointer;
  background: transparent;
  color: #26354d;
  gap: 4px;
  text-align: left;
}
.agent-session-open strong,
.agent-session-open span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-session-open span {
  color: #7c8aa0;
  font-size: 0.73rem;
}
.agent-session-item-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 5px;
}
.agent-conversation-main {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: 1;
  flex-direction: column;
}
.agent-conversation-context {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  padding: 12px 18px;
  border-bottom: 1px solid #e1e8f2;
  color: #26354d;
}
.agent-conversation-context strong {
  overflow-wrap: anywhere;
}
.agent-conversation-context span {
  color: #64748b;
  font-size: 0.8rem;
}
.agent-session-dialog {
  display: grid;
  gap: 12px;
  margin: 12px 18px;
  padding: 16px;
  border: 1px solid #91aff0;
  border-radius: 12px;
  background: #f8fafc;
  color: #26354d;
}
.agent-session-dialog label {
  display: grid;
  gap: 6px;
}
.agent-session-dialog input {
  width: 100%;
  padding: 8px;
  border: 1px solid #91aff0;
  border-radius: 6px;
  background: #fff;
  color: #1e293b;
}
.agent-session-dialog > div {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.agent-session-dialog button {
  padding: 8px 12px;
  background: #eaf1ff;
  color: #315ecf;
  border-radius: 6px;
  cursor: pointer;
}
.agent-conversation-layout button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 消息区 ===== */
.agent-chat-messages {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  padding: 20px 17px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
}
.agent-chat-welcome {
  display: flex;
  min-height: 100%;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  color: #334155;
  text-align: center;
}
.agent-chat-welcome strong {
  font-size: 0.95rem;
}
.agent-chat-welcome p {
  max-width: 275px;
  margin: 8px 0 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.55;
}
.agent-chat-message {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.agent-chat-message.user {
  justify-content: flex-end;
}
.agent-chat-avatar {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(145deg, #60a5fa, #6366f1);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 800;
  box-shadow: 0 5px 12px rgba(79, 70, 229, 0.2);
}
.agent-chat-bubble {
  max-width: calc(100% - 43px);
  min-width: 0;
  border-radius: 6px 16px 16px;
  background: #f4f7fb;
  color: #334155;
  font-size: 0.84rem;
  line-height: 1.65;
  padding: 11px 13px;
}
.agent-chat-message.user .agent-chat-bubble {
  border-radius: 16px 16px 6px;
  background: linear-gradient(145deg, #4f8cff, #4f46e5);
  color: #fff;
  box-shadow: 0 7px 16px rgba(79, 70, 229, 0.17);
}
.agent-chat-bubble p {
  margin: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
/* 用户气泡是深色渐变底，内部统一继承白字 */
.agent-chat-message.user .agent-chat-bubble p,
.agent-chat-message.user .agent-chat-bubble :deep(*) {
  color: inherit;
}
.agent-reasoning {
  color: #64748b;
}
.agent-reasoning + .agent-reasoning,
.agent-final-answer + .agent-reasoning {
  margin-top: 11px;
  padding-top: 11px;
  border-top: 1px solid #dce4ef;
}
.agent-final-answer {
  margin-top: 11px;
  padding-top: 11px;
  border-top: 1px solid #dce4ef;
  color: #1e293b;
}
.agent-chat-bubble > .agent-final-answer:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}
.agent-markdown {
  min-width: 0;
  overflow-wrap: anywhere;
}
.agent-markdown :deep(p),
.agent-markdown :deep(ul),
.agent-markdown :deep(ol),
.agent-markdown :deep(pre),
.agent-markdown :deep(h1),
.agent-markdown :deep(h2),
.agent-markdown :deep(h3),
.agent-markdown :deep(h4) {
  margin: 0;
}
.agent-markdown > :deep(* + *) {
  margin-top: 9px;
}
.agent-markdown :deep(h1),
.agent-markdown :deep(h2),
.agent-markdown :deep(h3),
.agent-markdown :deep(h4) {
  color: #172554;
  font-size: 0.92rem;
  line-height: 1.45;
}
.agent-markdown :deep(ul),
.agent-markdown :deep(ol) {
  padding-left: 1.25rem;
}
.agent-markdown :deep(li + li) {
  margin-top: 4px;
}
.agent-markdown :deep(code) {
  border-radius: 5px;
  background: #e8edf5;
  color: #0f172a;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 0.78rem;
  padding: 1px 4px;
}
.agent-markdown :deep(pre) {
  overflow-x: auto;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 10px 11px;
}
.agent-markdown :deep(pre code) {
  display: block;
  min-width: max-content;
  background: transparent;
  color: inherit;
  padding: 0;
  white-space: pre;
}
.agent-markdown :deep(.agent-markdown-table-wrap) {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
}
.agent-markdown :deep(table) {
  width: 100%;
  min-width: max-content;
  border-collapse: collapse;
  font-size: 0.78rem;
  line-height: 1.45;
}
.agent-markdown :deep(th),
.agent-markdown :deep(td) {
  max-width: 260px;
  padding: 8px 10px;
  border-bottom: 1px solid #e8edf5;
  border-left: 1px solid #e8edf5;
  text-align: left;
  vertical-align: top;
  white-space: normal;
}
.agent-markdown :deep(th:first-child),
.agent-markdown :deep(td:first-child) {
  border-left: 0;
}
.agent-markdown :deep(th) {
  background: #f8fafc;
  color: #334155;
  font-weight: 800;
}
.agent-markdown :deep(tbody tr:last-child td) {
  border-bottom: 0;
}
.agent-response-label {
  display: flex;
  align-items: center;
  min-height: 20px;
  gap: 8px;
  margin-bottom: 5px;
  color: #475569;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.03em;
}
.agent-reasoning-toggle {
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.agent-reasoning-chevron {
  margin-left: auto;
  font-size: 0.9rem;
  transition: transform 0.2s ease;
}
.agent-reasoning-toggle[aria-expanded='true'] .agent-reasoning-chevron {
  transform: rotate(180deg);
}
.agent-final-answer .agent-response-label {
  color: #3730a3;
}
.agent-reasoning-placeholder {
  color: #94a3b8;
}
.agent-thinking-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.agent-thinking-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #6366f1;
  animation: agent-thinking 1.15s infinite ease-in-out;
}
.agent-thinking-dots i:nth-child(2) {
  animation-delay: 0.15s;
}
.agent-thinking-dots i:nth-child(3) {
  animation-delay: 0.3s;
}
.agent-message-error {
  margin-top: 4px;
  color: #dc2626;
  font-size: 0.75rem;
}

/* ===== 错误条与输入区 ===== */
.agent-chat-error {
  margin: 0 17px 10px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fff1f2;
  color: #b91c1c;
  font-size: 0.75rem;
  padding: 8px 10px;
}
.agent-chat-error button {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-decoration: underline;
}
.agent-chat-composer {
  display: flex;
  align-items: flex-end;
  gap: 9px;
  padding: 13px 15px 15px;
  border-top: 1px solid #e8edf5;
  background: #fff;
}
.agent-chat-composer textarea {
  min-height: 44px;
  max-height: 110px;
  flex: 1;
  resize: none;
  border: 1px solid #dbe3ee;
  border-radius: 14px;
  outline: none;
  background: #f8fafc;
  color: #1e293b;
  font-size: 0.84rem;
  line-height: 1.45;
  padding: 11px 13px;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
.agent-chat-composer textarea:focus {
  border-color: #818cf8;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.11);
}
.agent-chat-composer textarea:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.agent-chat-composer button {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  place-items: center;
  cursor: pointer;
  border-radius: 14px;
  background: linear-gradient(145deg, #4f8cff, #4f46e5);
  color: #fff;
  transition:
    transform 0.2s,
    opacity 0.2s;
}
.agent-chat-composer button.stop {
  background: linear-gradient(145deg, #ef4444, #dc2626);
}
.agent-chat-composer button:hover:not(:disabled) {
  transform: translateY(-1px);
}
.agent-chat-composer button:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}
.agent-chat-composer button svg {
  width: 21px;
  height: 21px;
  fill: currentColor;
}

@keyframes agent-thinking {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-4px);
  }
}
@keyframes agent-pulse {
  70% {
    box-shadow: 0 0 0 8px rgba(52, 211, 153, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(52, 211, 153, 0);
  }
}
@keyframes agent-pulse-danger {
  70% {
    box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
  }
}
@media (max-width: 900px) {
  .agent-chat-panel {
    top: 12px;
    right: 8px;
    bottom: 8px;
    left: 8px;
    width: auto;
    height: auto;
    min-width: 0;
    min-height: 0;
    /* 仍然保留上限：拖拽缩放留下的行内尺寸不能撑破窄屏 */
    max-width: calc(100vw - 16px);
    max-height: calc(100vh - 20px);
  }
  .agent-conversation-layout {
    flex-direction: column;
  }
  .agent-session-manager {
    width: 100%;
    flex: 0 0 auto;
    max-height: 200px;
    border-right: 0;
    border-bottom: 1px solid #e1e8f2;
  }
  .agent-chat-bubble {
    max-width: calc(100% - 43px);
  }
  .agent-auth-page {
    padding: 20px 16px;
  }
}

@media (max-width: 600px) {
  .agent-fab {
    right: 16px;
    bottom: 16px;
    width: 52px;
    height: 52px;
    border-radius: 18px;
  }
  .agent-fab svg {
    width: 30px;
    height: 30px;
  }
}
</style>
