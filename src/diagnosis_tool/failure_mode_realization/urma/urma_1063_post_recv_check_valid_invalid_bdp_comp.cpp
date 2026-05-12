#include "urma_1063_post_recv_check_valid_invalid_bdp_comp.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1063PostRecvCheckValidInvalidBdpComp> g_urma("urma_1063");

bool Urma1063PostRecvCheckValidInvalidBdpComp::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp_comp"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1063PostRecvCheckValidInvalidBdpComp::GetName() const
{
    return "post_recv_check_valid Invalid bdp_comp";
}

std::string Urma1063PostRecvCheckValidInvalidBdpComp::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_recv_comp)`；该路径返回 URMA_EINVAL";
}

RootCause Urma1063PostRecvCheckValidInvalidBdpComp::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1063PostRecvCheckValidInvalidBdpComp::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1063PostRecvCheckValidInvalidBdpComp::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp_comp";
}

std::string Urma1063PostRecvCheckValidInvalidBdpComp::GetId() const
{
    return "urma_1063";
}
} // namespace diag
