#include "urma_1066_post_send_check_valid_send_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1066PostSendCheckValidSendFailure> g_urma("urma_1066");

bool Urma1066PostSendCheckValidSendFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp_send_comp"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1066PostSendCheckValidSendFailure::GetName() const
{
    return "post_send_check_valid 发送失败";
}

std::string Urma1066PostSendCheckValidSendFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_send_comp)`；该路径返回 URMA_EINVAL";
}

RootCause Urma1066PostSendCheckValidSendFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1066PostSendCheckValidSendFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1066PostSendCheckValidSendFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp_send_comp";
}

std::string Urma1066PostSendCheckValidSendFailure::GetId() const
{
    return "urma_1066";
}
} // namespace diag
