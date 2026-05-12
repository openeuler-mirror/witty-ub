#include "urma_0258_post_send_check_valid_invalid_bdp_target_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0258PostSendCheckValidInvalidBdpTargetJetty> g_urma("urma_0258");

bool Urma0258PostSendCheckValidInvalidBdpTargetJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp_target_jetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0258PostSendCheckValidInvalidBdpTargetJetty::GetName() const
{
    return "post_send_check_valid Invalid bdp_target_jetty";
}

std::string Urma0258PostSendCheckValidInvalidBdpTargetJetty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bdp_tjetty(bdp_tjetty)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0258PostSendCheckValidInvalidBdpTargetJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0258PostSendCheckValidInvalidBdpTargetJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0258PostSendCheckValidInvalidBdpTargetJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp_target_jetty";
}

std::string Urma0258PostSendCheckValidInvalidBdpTargetJetty::GetId() const
{
    return "urma_0258";
}
} // namespace diag
