#include "urma_0383_urma_cmd_create_jetty_failed_fill_jetty_cfg.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0383UrmaCmdCreateJettyFailedFillJettyCfg> g_urma("urma_0383");

bool Urma0383UrmaCmdCreateJettyFailedFillJettyCfg::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to fill jetty cfg"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0383UrmaCmdCreateJettyFailedFillJettyCfg::GetName() const
{
    return "urma_cmd_create_jetty failed to fill jetty cfg";
}

std::string Urma0383UrmaCmdCreateJettyFailedFillJettyCfg::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `urma_init_jetty_cfg(&jetty->jetty_cfg, cfg) != 0`；该路径返回 -1";
}

RootCause Urma0383UrmaCmdCreateJettyFailedFillJettyCfg::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0383UrmaCmdCreateJettyFailedFillJettyCfg::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0383UrmaCmdCreateJettyFailedFillJettyCfg::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to fill jetty cfg";
}

std::string Urma0383UrmaCmdCreateJettyFailedFillJettyCfg::GetId() const
{
    return "urma_0383";
}
} // namespace diag
