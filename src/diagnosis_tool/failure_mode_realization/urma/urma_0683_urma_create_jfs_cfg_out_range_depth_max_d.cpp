#include "urma_0683_urma_create_jfs_cfg_out_range_depth_max_d.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD> g_urma("urma_0683");

bool Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "jfs cfg out of range, depth:%, max_depth:%, inline_data:%, max_inline_len:%,"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD::GetName() const
{
    return "urma_create_jfs jfs cfg out of range, depth:%, max_d";
}

std::string Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(jfs_cfg->depth == 0 || jfs_cfg->depth > attr->dev_cap.max_jfs_depth) || "
           "(jfs_cfg->max_inline_data !`；该路径返回 NULL";
}

RootCause Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfs cfg out of range, depth:%, max_depth:%, inline_data:%, "
           "max_inline_len:%,";
}

std::string Urma0683UrmaCreateJfsCfgOutRangeDepthMaxD::GetId() const
{
    return "urma_0683";
}
} // namespace diag
