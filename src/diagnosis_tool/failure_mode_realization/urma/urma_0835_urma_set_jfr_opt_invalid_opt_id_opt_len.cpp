#include "urma_0835_urma_set_jfr_opt_invalid_opt_id_opt_len.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0835UrmaSetJfrOptInvalidOptIdOptLen> g_urma("urma_0835");

bool Urma0835UrmaSetJfrOptInvalidOptIdOptLen::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"invalid opt id or opt len"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0835UrmaSetJfrOptInvalidOptIdOptLen::GetName() const
{
    return "urma_set_jfr_opt invalid opt id or opt len";
}

std::string Urma0835UrmaSetJfrOptInvalidOptIdOptLen::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0835UrmaSetJfrOptInvalidOptIdOptLen::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0835UrmaSetJfrOptInvalidOptIdOptLen::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0835UrmaSetJfrOptInvalidOptIdOptLen::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：invalid opt id or opt len";
}

std::string Urma0835UrmaSetJfrOptInvalidOptIdOptLen::GetId() const
{
    return "urma_0835";
}
} // namespace diag
