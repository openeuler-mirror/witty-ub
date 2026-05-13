#include "urma_0678_urma_create_jfr_cfg_out_range_depth_max_d.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD> g_urma("urma_0678");

bool Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jfr cfg out of range, depth:%, max_depth:%, sge:%, max_sge:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD::GetName() const
{
    return "urma_create_jfr jfr cfg out of range, depth:%, max_d";
}

std::string Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `jfr_cfg->depth == 0 || jfr_cfg->depth > attr->dev_cap.max_jfr_depth || "
           "jfr_cfg->max_sge > attr->dev_`；该路径返回 NULL";
}

RootCause Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jfr cfg out of range, depth:%, max_depth:%, sge:%, max_sge:%.";
}

std::string Urma0678UrmaCreateJfrCfgOutRangeDepthMaxD::GetId() const
{
    return "urma_0678";
}
} // namespace diag
