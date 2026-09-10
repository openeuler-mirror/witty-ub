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

// A1（对齐旧版 eed74f7e）：面板可拖拽缩放（上/左/左上角手柄）
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
  const maxWidth = Math.max(320, window.innerWidth - 32)
  const maxHeight = Math.max(320, window.innerHeight - 106)
  const minWidth = Math.min(640, maxWidth)
  const minHeight = Math.min(420, maxHeight)
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

const toggle = () => {
  open.value = !open.value
  if (open.value) {
    syncAsset()
    restoreOnce()
    void scrollToBottom()
    void nextTick(() => panelRef.value?.focus())
  }
}

const closePanel = () => {
  open.value = false
  void nextTick(() => fabRef.value?.focus())
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
  suspend()
})

const statusLabelOf = () =>
  connectionState.value === 'connected'
    ? '已连接'
    : connectionState.value === 'connecting'
      ? '连接中'
      : '未连接'

const currentModelLabel = () => {
  const selected = selectedModel.value
  if (!selected) return '未选择模型'
  const model = connectedModels.value.find(
    (item) => item.providerID === selected.providerID && item.id === selected.modelID,
  )
  return `${selected.providerID} · ${model?.name ?? selected.modelID}`
}

const onInputKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendMessage()
  }
}
</script>

<template>
  <!-- FAB：仅分析页挂载（App.vue 控制挂载时机） -->
  <button
    ref="fabRef"
    :class="['agent-fab', { active: open, disconnected: connectionState !== 'connected' }]"
    title="AI 故障诊断助手"
    :aria-label="open ? '关闭 AI 故障诊断助手' : '打开 AI 故障诊断助手'"
    :aria-expanded="open"
    aria-controls="agent-chat-panel"
    @click="toggle"
  >
    <span class="agent-fab-pulse" />
    <svg
      viewBox="0 0 24 24"
      width="26"
      height="26"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
    >
      <rect x="4" y="7" width="16" height="11" rx="3" />
      <circle cx="9" cy="12.5" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="15" cy="12.5" r="1.2" fill="currentColor" stroke="none" />
      <path d="M12 7V4M8 4h8" />
    </svg>
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
        v-if="view !== 'chat' && connectionState === 'connected'"
        class="agent-back"
        aria-label="返回"
        @click="goBack"
      >
        ‹
      </button>
      <span
        :class="['agent-chat-status', connectionState]"
        :title="statusLabelOf()"
        :aria-label="'连接状态：' + statusLabelOf()"
        role="status"
      />
      <div class="agent-chat-title">
        <strong>AI 故障诊断助手</strong>
        <small>
          {{ view === 'chat' ? '当前模型：' + currentModelLabel() : '时延与通断故障分析' }}
        </small>
      </div>
      <button v-if="view === 'chat'" class="btn btn-text btn-sm" @click="view = 'models'">
        模型切换
      </button>
      <button class="agent-chat-close" aria-label="关闭 AI 故障诊断助手" @click="closePanel">
        ✕
      </button>
    </header>

    <div v-if="connectionError" class="agent-chat-error" role="alert">
      <span>{{ connectionError }}</span>
      <button v-if="isHistoryFailed && sessionId" @click="openConversation(sessionId)">
        重新加载会话
      </button>
    </div>

    <!-- ===== 登录视图 ===== -->
    <div v-if="view === 'login'" class="agent-view agent-login">
      <button
        class="agent-login-card"
        :disabled="isLoggingIn || connectionState === 'connecting'"
        @click="loginLocalAgent"
      >
        <strong>连接到本机 OpenCode 服务器</strong>
        <span>127.0.0.1:4096 · 无需用户名和密码</span>
      </button>
      <form class="agent-login-card" @submit.prevent="loginRemoteAgent">
        <strong>连接远程 OpenCode 服务器</strong>
        <input class="input" v-model="remoteAddress" placeholder="IP:端口号" autocomplete="url" />
        <input
          class="input"
          v-model="remoteUsername"
          placeholder="用户名"
          autocomplete="username"
        />
        <input
          class="input"
          type="password"
          v-model="remotePassword"
          placeholder="密码"
          autocomplete="current-password"
        />
        <button class="btn btn-primary" type="submit" :disabled="isLoggingIn">
          {{ isLoggingIn ? '连接中...' : '连接' }}
        </button>
      </form>
    </div>

    <!-- ===== 模型视图 ===== -->
    <div v-else-if="view === 'models'" class="agent-view">
      <div class="agent-view-bar">
        <input class="input" v-model="modelSearch" placeholder="搜索模型 / Provider" />
        <button class="btn btn-default btn-sm" @click="view = 'providers'">＋ 新增</button>
      </div>
      <div v-if="filteredModels.length === 0" class="agent-empty">没有找到已连接的模型</div>
      <div v-else class="agent-model-list">
        <button
          v-for="model in filteredModels"
          :key="model.providerID + '/' + model.id"
          :class="[
            'agent-model-item',
            {
              active:
                selectedModel?.providerID === model.providerID &&
                selectedModel?.modelID === model.id,
            },
          ]"
          @click="selectModel(model.providerID, model.id)"
        >
          <strong>{{ model.name }}</strong>
          <small>{{ model.providerID }}</small>
        </button>
      </div>
    </div>

    <!-- ===== Provider / API key 视图 ===== -->
    <div v-else-if="view === 'providers'" class="agent-view">
      <div class="agent-view-bar">
        <input class="input" v-model="providerSearch" placeholder="搜索 Provider" />
      </div>
      <div v-if="filteredProviders.length === 0" class="agent-empty">暂无需要配置的 Provider</div>
      <div v-else class="agent-provider-list">
        <div v-for="provider in filteredProviders" :key="provider.id" class="agent-provider-item">
          <button
            class="agent-provider-toggle"
            @click="expandedProviderId = expandedProviderId === provider.id ? '' : provider.id"
          >
            {{ provider.name }}
            <span>{{ expandedProviderId === provider.id ? '▾' : '▸' }}</span>
          </button>
          <form
            v-if="expandedProviderId === provider.id"
            class="agent-provider-form"
            @submit.prevent="authorizeProvider(provider.id)"
          >
            <input
              class="input"
              type="password"
              v-model="providerApiKey"
              :placeholder="provider.name + ' API Key'"
              autocomplete="off"
            />
            <button
              class="btn btn-primary btn-sm"
              type="submit"
              :disabled="!providerApiKey || isAuthorizing"
            >
              {{ isAuthorizing ? '认证中' : '认证' }}
            </button>
          </form>
        </div>
      </div>
    </div>

    <!-- ===== 会话视图 ===== -->
    <div v-else class="agent-conversation-layout">
      <aside class="agent-session-manager">
        <div class="agent-session-bar">
          <strong>会话</strong>
          <button
            class="btn btn-text btn-sm"
            :disabled="isSessionCreating || isSessionSaving || isSubmitting"
            @click="newConversation"
          >
            {{ isSessionCreating ? '创建中…' : '＋ 新建' }}
          </button>
        </div>
        <button
          class="btn btn-text btn-sm agent-session-refresh"
          :disabled="isSessionsLoading || isSessionCreating || isSessionSaving"
          @click="refreshSessions"
        >
          刷新会话列表
        </button>
        <input class="input" v-model="sessionSearch" placeholder="搜索会话 / 资产" />
        <div v-if="isSessionsLoading" class="agent-empty">正在加载会话...</div>
        <div v-else-if="filteredSessions.length === 0" class="agent-empty">暂无会话</div>
        <div v-else class="agent-session-list">
          <div
            v-for="session in filteredSessions"
            :key="session.id"
            :class="['agent-session-item', { active: session.id === sessionId }]"
            role="button"
            tabindex="0"
            :aria-label="'打开会话：' + (session.title || session.id.slice(0, 12))"
            @click="openConversation(session.id)"
            @keydown.enter.prevent="openConversation(session.id)"
            @keydown.space.prevent="openConversation(session.id)"
          >
            <div class="agent-session-title">{{ session.title || session.id.slice(0, 12) }}</div>
            <div class="agent-session-meta">
              <span>
                {{ sessionAssetName(session.id) || '未关联资产' }}
                ·
                {{
                  sessionStatuses[session.id]?.type === 'busy'
                    ? '正在回答'
                    : sessionStatuses[session.id]?.type === 'retry'
                      ? '正在重试'
                      : session.time?.updated
                        ? new Date(session.time.updated).toLocaleString()
                        : '空闲'
                }}
              </span>
              <span class="agent-session-actions">
                <button
                  title="重命名"
                  :aria-label="'重命名会话：' + (session.title || session.id.slice(0, 12))"
                  :disabled="isSessionSaving || isSubmitting"
                  @click.stop="showSessionDialog('rename', session)"
                >
                  ✎
                </button>
                <button
                  title="删除"
                  :aria-label="'删除会话：' + (session.title || session.id.slice(0, 12))"
                  :disabled="isSessionSaving || isSubmitting"
                  @click.stop="showSessionDialog('delete', session)"
                >
                  ×
                </button>
              </span>
            </div>
          </div>
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
              class="input"
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
            <button
              class="btn btn-default btn-sm"
              type="button"
              :disabled="isSessionSaving"
              @click="sessionDialog = null"
            >
              取消
            </button>
            <button class="btn btn-primary btn-sm" type="submit" :disabled="isSessionSaving">
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
        <div ref="messagesRef" class="agent-messages">
          <div v-if="isHistoryLoading" class="agent-welcome">正在加载历史消息…</div>
          <div v-else-if="messages.length === 0" class="agent-welcome">
            <div class="agent-welcome-icon">✦</div>
            <p>你好，我是故障诊断助手。</p>
            <p class="agent-welcome-hint">
              我可以基于当前资产（{{ props.asset?.name || '未选择' }}）的时延与通断数据分析故障。
            </p>
          </div>
          <div
            v-for="message in messages"
            :key="message.id"
            :class="['agent-message', message.role]"
          >
            <span v-if="message.role === 'assistant'" class="agent-avatar">AI</span>
            <div class="agent-bubble">
              <template v-for="part in displayPartsOf(message)" :key="part.id">
                <div v-if="part.type === 'reasoning'" class="agent-reasoning">
                  <button class="agent-reasoning-toggle" @click="part.collapsed = !part.collapsed">
                    <span v-if="message.status === 'thinking' && !part.text" class="agent-typing">
                      正在分析问题并查询诊断数据
                      <i></i><i></i><i></i>
                    </span>
                    <template v-else>思考过程</template>
                    <b>{{ part.collapsed ? '▸' : '▾' }}</b>
                  </button>
                  <div v-show="!part.collapsed && part.text" class="agent-reasoning-body">
                    {{ part.text }}
                  </div>
                </div>
                <div
                  v-else-if="part.text"
                  class="agent-markdown"
                  v-html="renderAgentMarkdown(part.text)"
                />
              </template>
              <div v-if="message.status === 'error'" class="agent-message-error">响应失败</div>
            </div>
          </div>
        </div>

        <div class="agent-composer">
          <textarea
            v-model="input"
            class="agent-input"
            rows="1"
            placeholder="描述故障现象或提问，Enter 发送，Shift+Enter 换行"
            :disabled="
              isSending ||
              isHistoryLoading ||
              isHistoryFailed ||
              isSessionCreating ||
              isSessionSaving
            "
            @keydown="onInputKeydown"
          />
          <button
            v-if="!isSending"
            class="btn btn-primary agent-send"
            :disabled="
              !input.trim() ||
              isHistoryLoading ||
              isHistoryFailed ||
              isSessionCreating ||
              isSessionSaving ||
              isSubmitting
            "
            @click="sendMessage"
          >
            发送
          </button>
          <button v-else class="btn btn-primary agent-send stop" @click="abortAgentSession">
            ■
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.agent-fab {
  position: fixed;
  right: 28px;
  bottom: 26px;
  width: 62px;
  height: 62px;
  border-radius: 50%;
  border: none;
  background: var(--primary, #2563eb);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4);
  z-index: 70;
}
.agent-fab.disconnected {
  background: var(--text3, #9ca3af);
}
.agent-fab.active {
  background: var(--primary, #2563eb);
}
.agent-fab-pulse {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #22c55e;
}
.agent-fab.disconnected .agent-fab-pulse {
  background: #ef4444;
}
.agent-chat-panel {
  position: fixed;
  right: 28px;
  bottom: 102px;
  width: min(980px, calc(100vw - 32px));
  height: min(800px, calc(100vh - 166px));
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 106px);
  background: var(--bg, #fff);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 69;
}

/* A1：拖拽缩放手柄（上边 / 左边 / 左上角） */
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
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.agent-back {
  border: none;
  background: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--text2);
}
.agent-chat-status {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #22c55e;
  flex-shrink: 0;
}
.agent-chat-status.connecting {
  background: #f59e0b;
}
.agent-chat-status.disconnected {
  background: #9ca3af;
}
.agent-chat-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
.agent-chat-title small {
  color: var(--text3);
  font-size: 11px;
}
.agent-chat-close {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--text2);
}
.agent-chat-error {
  background: #fef2f2;
  color: var(--danger, #dc2626);
  font-size: 12px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.agent-chat-error button {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-decoration: underline;
}
.agent-view {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.agent-login {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 420px;
  margin: 0 auto;
}
.agent-login-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px;
  background: var(--bg2, #f9fafb);
  font-size: 13px;
}
.agent-login-card span {
  color: var(--text3);
  font-size: 12px;
}
.agent-view-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.agent-view-bar .input {
  flex: 1;
}
.agent-empty {
  color: var(--text3);
  font-size: 13px;
  text-align: center;
  padding: 28px 0;
}
.agent-model-list,
.agent-provider-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.agent-model-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  background: none;
  cursor: pointer;
  text-align: left;
}
.agent-model-item.active {
  border-color: var(--primary, #2563eb);
  background: rgba(37, 99, 235, 0.06);
}
.agent-model-item small {
  color: var(--text3);
  font-size: 11px;
}
.agent-provider-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.agent-provider-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  border: none;
  background: none;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
}
.agent-provider-form {
  display: flex;
  gap: 8px;
  padding: 0 14px 12px;
}
.agent-provider-form .input {
  flex: 1;
}
.agent-conversation-layout {
  flex: 1;
  display: flex;
  min-height: 0;
}
.agent-session-manager {
  width: 270px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}
.agent-session-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.agent-session-refresh {
  align-self: flex-start;
}
.agent-session-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.agent-session-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 12px;
}
.agent-session-item.active {
  border-color: var(--primary, #2563eb);
  background: rgba(37, 99, 235, 0.06);
}
.agent-session-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-session-meta {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  color: var(--text3);
  margin-top: 2px;
}
.agent-session-meta > span:first-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-session-actions button {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--text3);
  padding: 0 2px;
}
.agent-session-actions button:disabled,
.agent-conversation-layout button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.agent-conversation-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.agent-conversation-context {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.agent-conversation-context strong {
  overflow-wrap: anywhere;
}
.agent-conversation-context span {
  color: var(--text3);
}
.agent-session-dialog {
  display: grid;
  gap: 10px;
  margin: 12px 16px 0;
  padding: 14px;
  border: 1px solid var(--primary, #2563eb);
  border-radius: 10px;
  background: var(--bg2, #f9fafb);
  font-size: 12px;
}
.agent-session-dialog label {
  display: grid;
  gap: 6px;
}
.agent-session-dialog p {
  margin: 0;
}
.agent-session-dialog > div {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.agent-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.agent-welcome {
  text-align: center;
  color: var(--text2);
  margin: auto;
}
.agent-welcome-icon {
  font-size: 28px;
  color: var(--primary, #2563eb);
}
.agent-welcome-hint {
  font-size: 12px;
  color: var(--text3);
}
.agent-message {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.agent-message.user {
  justify-content: flex-end;
}
.agent-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--primary, #2563eb);
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.agent-bubble {
  max-width: 76%;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  background: var(--bg2, #f3f4f6);
}
.agent-message.user .agent-bubble {
  background: var(--primary, #2563eb);
  color: #fff;
}
.agent-message-error {
  color: var(--danger, #dc2626);
  font-size: 12px;
  margin-top: 4px;
}
.agent-reasoning {
  border: 1px dashed var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  overflow: hidden;
}
.agent-reasoning-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: rgba(0, 0, 0, 0.03);
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text2);
}
.agent-reasoning-toggle b {
  margin-left: auto;
}
.agent-reasoning-body {
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text2);
  white-space: pre-wrap;
  word-break: break-word;
}
.agent-typing i {
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text3);
  margin-left: 4px;
  animation: agent-blink 1.2s infinite;
}
.agent-typing i:nth-child(2) {
  animation-delay: 0.2s;
}
.agent-typing i:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes agent-blink {
  0%,
  80%,
  100% {
    opacity: 0.2;
  }
  40% {
    opacity: 1;
  }
}
.agent-markdown :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  overflow-x: auto;
  font-size: 12px;
}
.agent-markdown :deep(code) {
  font-family: monospace;
  font-size: 12px;
}
.agent-markdown :deep(.agent-markdown-table-wrap) {
  overflow-x: auto;
  margin: 8px 0;
}
.agent-markdown :deep(table) {
  border-collapse: collapse;
  font-size: 12px;
}
.agent-markdown :deep(th),
.agent-markdown :deep(td) {
  border: 1px solid var(--border);
  padding: 4px 8px;
  text-align: left;
}
.agent-markdown :deep(h1),
.agent-markdown :deep(h2),
.agent-markdown :deep(h3),
.agent-markdown :deep(h4) {
  font-size: 13px;
  margin: 8px 0 4px;
}
.agent-composer {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  align-items: flex-end;
}
.agent-input {
  flex: 1;
  resize: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  max-height: 120px;
}
.agent-send {
  flex-shrink: 0;
}
.agent-send.stop {
  background: var(--danger, #dc2626);
  border-color: var(--danger, #dc2626);
}

@media (max-width: 900px) {
  .agent-fab {
    right: 16px;
    bottom: 16px;
    width: 52px;
    height: 52px;
  }
  .agent-chat-panel {
    top: 64px;
    right: 8px;
    bottom: 76px;
    width: calc(100vw - 16px);
    height: auto;
  }
  .agent-conversation-layout {
    flex-direction: column;
  }
  .agent-session-manager {
    width: 100%;
    max-height: 180px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  .agent-session-list {
    overflow-y: auto;
  }
  .agent-bubble {
    max-width: 88%;
  }
}
</style>
