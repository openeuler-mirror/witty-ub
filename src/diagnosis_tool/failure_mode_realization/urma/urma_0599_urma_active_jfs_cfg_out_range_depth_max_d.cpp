#include "urma_0599_urma_active_jfs_cfg_out_range_depth_max_d.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD> g_urma("urma_0599");

bool Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "jfs cfg out of range, depth:%, max_depth:%, inline_data:%, max_inline_len:%,"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD::GetName() const
{
    return "urma_active_jfs jfs cfg out of range, depth:%, max_d";
}

std::string Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(cfg->depth == 0 || cfg->depth > attr->dev_cap.max_jfs_depth) || (cfg->max_inline_data "
           "> attr->dev_c`；该路径返回 URMA_EINVAL";
}

RootCause Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfs cfg out of range, depth:%, max_depth:%, inline_data:%, "
           "max_inline_len:%,";
}

std::string Urma0599UrmaActiveJfsCfgOutRangeDepthMaxD::GetId() const
{
    return "urma_0599";
}
} // namespace diag
