import assert from 'node:assert/strict'
import test from 'node:test'
import { useDiagCaseDetail } from '../src/composables/useDiagCaseDetail.ts'
import { useReportWorkbench } from '../src/composables/useReportWorkbench.ts'

test('关闭案例不通知数据变化，报告跳转可恢复原报告上下文', () => {
  const report = useReportWorkbench()
  const detail = useDiagCaseDetail()
  report.closeReport()
  detail.closeCase()
  const version = detail.caseVersion.value

  report.openReport('report-1', 'F02')
  report.suspendReport()
  detail.openCase('case-1', true)
  assert.equal(report.open.value, false)
  assert.equal(detail.returnToReport.value, true)
  detail.closeCase()
  report.resumeReport()
  assert.equal(detail.caseVersion.value, version)
  assert.equal(report.open.value, true)
  assert.equal(report.resume.value, true)
  assert.equal(report.reportId.value, 'report-1')
  assert.equal(report.sourceFaultId.value, 'F02')

  report.closeReport()
  report.openReport('report-2')
  assert.equal(report.resume.value, false)
  detail.openCase('case-2')
  assert.equal(detail.returnToReport.value, false)
  detail.closeCase()
  assert.equal(detail.caseVersion.value, version)
  detail.bumpCaseVersion()
  assert.equal(detail.caseVersion.value, version + 1)
  report.closeReport()
})
