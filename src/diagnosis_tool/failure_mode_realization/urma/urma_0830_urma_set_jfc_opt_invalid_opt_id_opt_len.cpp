#include "urma_0830_urma_set_jfc_opt_invalid_opt_id_opt_len.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0830UrmaSetJfcOptInvalidOptIdOptLen> g_urma("urma_0830");

bool Urma0830UrmaSetJfcOptInvalidOptIdOptLen::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"invalid opt id or opt len"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0830UrmaSetJfcOptInvalidOptIdOptLen::GetName() const
{
    return "urma_set_jfc_opt invalid opt id or opt len";
}

std::string Urma0830UrmaSetJfcOptInvalidOptIdOptLen::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0830UrmaSetJfcOptInvalidOptIdOptLen::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0830UrmaSetJfcOptInvalidOptIdOptLen::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0830UrmaSetJfcOptInvalidOptIdOptLen::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：invalid opt id or opt len";
}

std::string Urma0830UrmaSetJfcOptInvalidOptIdOptLen::GetId() const
{
    return "urma_0830";
}
} // namespace diag
