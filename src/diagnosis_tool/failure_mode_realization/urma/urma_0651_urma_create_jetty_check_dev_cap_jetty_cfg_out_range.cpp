#include "urma_0651_urma_create_jetty_check_dev_cap_jetty_cfg_out_range.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange> g_urma("urma_0651");

bool Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"jetty cfg out of range, jfs_depth:%, max_jfs_depth: %,"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange::GetName() const
{
    return "urma_create_jetty_check_dev_cap jetty cfg out of range, jfs_depth:%,";
}

std::string Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(jfs_cfg->depth == 0 || jfs_cfg->depth > cap->max_jfs_depth) || "
           "(jfs_cfg->max_inline_data != 0 && jf`；该路径返回 -1";
}

RootCause Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：jetty cfg out of range, jfs_depth:%, max_jfs_depth: %,";
}

std::string Urma0651UrmaCreateJettyCheckDevCapJettyCfgOutRange::GetId() const
{
    return "urma_0651";
}
} // namespace diag
