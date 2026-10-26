<script setup lang="ts">
import { onMounted } from 'vue'
import { useCaseLibrary } from '../../composables/useCaseLibrary'
import { caseAttachmentUrl, type CaseRecord } from '../../api/caseLibrary'

const {
  cases,
  categories,
  loading,
  error,
  scope,
  filterText,
  expanded,
  load,
  filteredCategories,
  scopedCases,
  scopeTitle,
  selectAll,
  selectCategory,
  selectType,
  toggleExpand,
} = useCaseLibrary()

const isActive = (key: string) => {
  const current = scope.value
  if (current.kind === 'all') return key === '__all__'
  if (current.kind === 'category') return key === `__cat__:${current.id}`
  return key === `__type__:${current.name}`
}

const featureLines = (item: CaseRecord) => {
  const lines: string[] = []
  const latency = item.features?.latency
  if (latency) {
    lines.push(
      `时延特征：超时分段 ${latency.timeout_segments?.join(', ') || '无'}；P99/P50 ${
        latency.p99_p50_ratio?.toFixed(1) ?? '-'
      }；Pod集中度 ${latency.pod_concentration || '-'}`,
    )
  }
  const conn = item.features?.connectivity
  if (conn) {
    lines.push(
      `通断特征：故障模式 ${Object.keys(conn.failure_mode_dist ?? {}).join(', ') || '无'}；Pod范围 ${
        conn.spatial_pod?.scope || '-'
      }；节点范围 ${conn.spatial_host?.scope || '-'}`,
    )
  }
  const summary = item.features?.summary
  if (summary) {
    lines.push(
      `统计：异常事件 ${summary.anomalous_event_count ?? 0}，故障事件 ${
        summary.failure_event_count ?? 0
      }，总记录 ${summary.total_parse_result_count ?? 0}`,
    )
  }
  return lines
}

onMounted(() => void load())
</script>
<template>
  <div v-if="loading" class="empty">
    <div class="icon">⏳</div>
    <div>正在加载案例库...</div>
  </div>
  <div v-else-if="error" class="error-banner" role="alert">
    案例加载失败：{{ error }}
    <button class="btn btn-sm btn-default" type="button" @click="load">重试</button>
  </div>
  <div v-else-if="cases.length === 0 && categories.length === 0" class="empty">
    <div class="icon">📭</div>
    <div>暂无案例</div>
    <div class="hint">诊断流程产出的案例会汇总在此，按故障大类/类型查看</div>
  </div>
  <div v-else class="case-layout">
    <aside class="case-sidebar">
      <div class="case-sidebar-search">
        <input class="input" v-model="filterText" placeholder="搜索故障大类/类型..." />
      </div>
      <div class="case-sidebar-list">
        <button
          type="button"
          :class="['case-type-item', { active: isActive('__all__') }]"
          @click="selectAll"
        >
          <span class="case-type-name">全部案例</span>
          <span class="case-type-count">{{ cases.length }}</span>
        </button>
        <div v-for="cat in filteredCategories" :key="cat.id" class="case-cat-group">
          <div class="case-cat-header">
            <button
              type="button"
              class="case-cat-toggle"
              :aria-expanded="expanded.has(cat.id)"
              @click.stop="toggleExpand(cat.id)"
            >
              {{ expanded.has(cat.id) ? '▼' : '▶' }}
            </button>
            <button
              type="button"
              :class="['case-cat-name', { active: isActive(`__cat__:${cat.id}`) }]"
              :title="cat.name"
              @click="selectCategory(cat.id)"
            >
              {{ cat.name }}
            </button>
            <span class="case-type-count">{{ cat.case_count }}</span>
          </div>
          <div v-if="cat.description" class="case-cat-desc">
            {{ cat.description }}
          </div>
          <div v-if="expanded.has(cat.id)" class="case-cat-types">
            <div
              v-for="t in cat.types"
              :key="t.name"
              :class="[
                'case-type-item',
                'case-type-child',
                { active: isActive(`__type__:${t.name}`) },
              ]"
            >
              <button
                type="button"
                class="case-type-name"
                :title="t.name"
                @click="selectType(t.name)"
              >
                {{ t.name }}
              </button>
              <span class="case-type-count">{{ t.case_count }}</span>
            </div>
          </div>
        </div>
        <div v-if="filteredCategories.length === 0" class="case-type-empty">无匹配结果</div>
      </div>
    </aside>

    <main class="case-main">
      <div class="case-main-header">
        <h2>{{ scopeTitle }}</h2>
        <span class="case-main-count">共 {{ scopedCases.length }} 条</span>
      </div>
      <div class="case-main-list">
        <div v-for="c in scopedCases" :key="c.id" class="card case-card">
          <div class="case-card-header">
            <span class="badge badge-pending">{{ c.root_cause_type }}</span>
            <span class="badge badge-success">{{ c.case_category || '未分类' }}</span>
            <span v-if="c.fault_category" class="badge badge-normal">{{ c.fault_category }}</span>
            <span class="case-card-time">{{ c.created_at || '—' }}</span>
            <a
              v-if="c.attachment_path"
              :href="caseAttachmentUrl(c.id)"
              class="btn btn-sm btn-text"
              target="_blank"
              rel="noopener noreferrer"
              title="下载附件"
            >
              📎 附件
            </a>
          </div>
          <div class="case-card-body">
            <div v-if="c.description" class="case-card-row">
              <span class="case-card-label">说明：</span>
              <span>{{ c.description }}</span>
            </div>
            <div v-for="line in featureLines(c)" :key="line" class="case-card-row">
              <span>{{ line }}</span>
            </div>
            <div class="case-card-row">
              <span class="case-card-label">关联任务：</span>
              <span>{{ c.task_names?.join(', ') || '无' }}</span>
            </div>
          </div>
        </div>
        <div v-if="scopedCases.length === 0" class="empty">
          <div class="icon">📭</div>
          <div>暂无匹配案例</div>
        </div>
      </div>
    </main>
  </div>
</template>
