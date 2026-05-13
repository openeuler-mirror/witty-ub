#include "urma_1064_post_recv_check_valid_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1064PostRecvCheckValidFailure> g_urma("urma_1064");

bool Urma1064PostRecvCheckValidFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp_recv_comp type: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1064PostRecvCheckValidFailure::GetName() const
{
    return "post_recv_check_valid 接收失败";
}

std::string Urma1064PostRecvCheckValidFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_recv_comp->comp_type != BONDP_COMP_JETTY && bdp_recv_comp->comp_type != "
           "BONDP_COMP_JFR`；该路径返回 URMA_EINVAL";
}

RootCause Urma1064PostRecvCheckValidFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1064PostRecvCheckValidFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1064PostRecvCheckValidFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp_recv_comp type: %";
}

std::string Urma1064PostRecvCheckValidFailure::GetId() const
{
    return "urma_1064";
}
} // namespace diag
