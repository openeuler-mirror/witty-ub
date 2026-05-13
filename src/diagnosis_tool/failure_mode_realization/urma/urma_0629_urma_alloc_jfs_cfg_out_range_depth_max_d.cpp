#include "urma_0629_urma_alloc_jfs_cfg_out_range_depth_max_d.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD> g_urma("urma_0629");

bool Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "jfs cfg out of range, depth:%, max_depth:%, inline_data:%, max_inline_len:%,"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD::GetName() const
{
    return "urma_alloc_jfs jfs cfg out of range, depth:%, max_d";
}

std::string Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(cfg->depth == 0 || cfg->depth > attr->dev_cap.max_jfs_depth) || (cfg->max_inline_data "
           "> attr->dev_c`；该路径返回 URMA_EINVAL";
}

RootCause Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfs cfg out of range, depth:%, max_depth:%, inline_data:%, "
           "max_inline_len:%,";
}

std::string Urma0629UrmaAllocJfsCfgOutRangeDepthMaxD::GetId() const
{
    return "urma_0629";
}
} // namespace diag
