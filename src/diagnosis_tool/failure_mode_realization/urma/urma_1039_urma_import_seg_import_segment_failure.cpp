#include "urma_1039_urma_import_seg_import_segment_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1039UrmaImportSegImportSegmentFailure> g_urma("urma_1039");

bool Urma1039UrmaImportSegImportSegmentFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to import seg, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1039UrmaImportSegImportSegmentFailure::GetName() const
{
    return "urma_import_seg 导入Segment失败";
}

std::string Urma1039UrmaImportSegImportSegmentFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 tseg";
}

RootCause Urma1039UrmaImportSegImportSegmentFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1039UrmaImportSegImportSegmentFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1039UrmaImportSegImportSegmentFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to import seg, dev_name: %, eid_idx: %.";
}

std::string Urma1039UrmaImportSegImportSegmentFailure::GetId() const
{
    return "urma_1039";
}
} // namespace diag
