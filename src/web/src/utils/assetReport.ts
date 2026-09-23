// 资产库内「查看诊断报告」入口的纯逻辑：按钮三态与弹层提示。
// 抽成纯函数是为了能直接用 node --test 覆盖三态与边界（见 docs/design/asset-report-entry.md §5）。
export type AssetReportButtonState = 'loading' | 'empty' | 'single' | 'multiple'

/** 弹层一次拉取的份数上限；超出时给出跳转全局报告库的提示。 */
export const ASSET_REPORT_DIALOG_PAGE_SIZE = 50

/**
 * 由该库报告总数推导按钮状态：
 * - 未探测完（loading）或总数未知 → loading（此时不可点）
 * - 0 份 → empty（可点，弹层直接提示「暂无相关诊断报告，可通过 Agent 生成」）
 * - 1 份 → single（直接新窗口打开）
 * - ≥2 份 → multiple（弹层列出）
 */
export const resolveAssetReportButtonState = (
  total: number | null | undefined,
  loading = false,
): AssetReportButtonState => {
  if (loading || typeof total !== 'number' || !Number.isFinite(total) || total < 0) return 'loading'
  if (total === 0) return 'empty'
  return total === 1 ? 'single' : 'multiple'
}

/** 按钮悬停文案：只有探测中不可点，需要说明原因。 */
export const assetReportButtonTitle = (state: AssetReportButtonState): string =>
  state === 'loading' ? '正在检查该资产库的诊断报告…' : '查看诊断报告'

/**
 * 只有探测中不可点。0 份时按钮仍可点——点击后在弹层里直接提示
 * 「暂无相关诊断报告，可通过 Agent 生成」，比置灰更能告诉用户下一步怎么做。
 */
export const isAssetReportButtonDisabled = (state: AssetReportButtonState): boolean =>
  state === 'loading'

/** 超出弹层上限时的末尾提示文案；未超出返回 null。 */
export const buildAssetReportListNotice = (
  total: number | null | undefined,
  pageSize = ASSET_REPORT_DIALOG_PAGE_SIZE,
): string | null =>
  typeof total === 'number' && total > pageSize
    ? `仅显示最近 ${pageSize} 份，完整列表见侧栏「诊断报告 → 报告库」`
    : null
