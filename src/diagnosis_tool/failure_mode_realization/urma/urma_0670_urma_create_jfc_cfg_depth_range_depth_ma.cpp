#include "urma_0670_urma_create_jfc_cfg_depth_range_depth_ma.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0670UrmaCreateJfcCfgDepthRangeDepthMa> g_urma("urma_0670");

bool Urma0670UrmaCreateJfcCfgDepthRangeDepthMa::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfc cfg depth of range, depth: %, max_depth: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0670UrmaCreateJfcCfgDepthRangeDepthMa::GetName() const
{
    return "urma_create_jfc jfc cfg depth of range, depth: %, ma";
}

std::string Urma0670UrmaCreateJfcCfgDepthRangeDepthMa::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jfc_cfg->depth == 0 || jfc_cfg->depth > attr->dev_cap.max_jfc_depth`；该路径返回 NULL";
}

RootCause Urma0670UrmaCreateJfcCfgDepthRangeDepthMa::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0670UrmaCreateJfcCfgDepthRangeDepthMa::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0670UrmaCreateJfcCfgDepthRangeDepthMa::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfc cfg depth of range, depth: %, max_depth: %.";
}

std::string Urma0670UrmaCreateJfcCfgDepthRangeDepthMa::GetId() const
{
    return "urma_0670";
}
} // namespace diag
