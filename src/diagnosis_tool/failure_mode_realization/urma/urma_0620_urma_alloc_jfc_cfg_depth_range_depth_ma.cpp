#include "urma_0620_urma_alloc_jfc_cfg_depth_range_depth_ma.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0620UrmaAllocJfcCfgDepthRangeDepthMa> g_urma("urma_0620");

bool Urma0620UrmaAllocJfcCfgDepthRangeDepthMa::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfc cfg depth of range, depth: %, max_depth: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0620UrmaAllocJfcCfgDepthRangeDepthMa::GetName() const
{
    return "urma_alloc_jfc jfc cfg depth of range, depth: %, ma";
}

std::string Urma0620UrmaAllocJfcCfgDepthRangeDepthMa::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `cfg->depth == 0 || cfg->depth > attr->dev_cap.max_jfc_depth`；该路径返回 URMA_EINVAL";
}

RootCause Urma0620UrmaAllocJfcCfgDepthRangeDepthMa::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0620UrmaAllocJfcCfgDepthRangeDepthMa::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0620UrmaAllocJfcCfgDepthRangeDepthMa::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfc cfg depth of range, depth: %, max_depth: %.";
}

std::string Urma0620UrmaAllocJfcCfgDepthRangeDepthMa::GetId() const
{
    return "urma_0620";
}
} // namespace diag
