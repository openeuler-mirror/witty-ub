#include "urma_0625_urma_alloc_jfr_cfg_out_range_depth_max_d.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD> g_urma("urma_0625");

bool Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfr cfg out of range, depth:%, max_depth:%, sge:%, max_sge:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD::GetName() const
{
    return "urma_alloc_jfr jfr cfg out of range, depth:%, max_d";
}

std::string Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `cfg->depth == 0 || cfg->depth > attr->dev_cap.max_jfr_depth || cfg->max_sge > "
           "attr->dev_cap.max_jfr_`；该路径返回 URMA_EINVAL";
}

RootCause Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfr cfg out of range, depth:%, max_depth:%, sge:%, max_sge:%.";
}

std::string Urma0625UrmaAllocJfrCfgOutRangeDepthMaxD::GetId() const
{
    return "urma_0625";
}
} // namespace diag
