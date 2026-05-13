#include "urma_0840_urma_set_jfs_opt_invalid_opt_id_opt_len.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0840UrmaSetJfsOptInvalidOptIdOptLen> g_urma("urma_0840");

bool Urma0840UrmaSetJfsOptInvalidOptIdOptLen::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"invalid opt id or opt len"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0840UrmaSetJfsOptInvalidOptIdOptLen::GetName() const
{
    return "urma_set_jfs_opt invalid opt id or opt len";
}

std::string Urma0840UrmaSetJfsOptInvalidOptIdOptLen::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `status != URMA_SUCCESS`；该路径返回 status";
}

RootCause Urma0840UrmaSetJfsOptInvalidOptIdOptLen::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0840UrmaSetJfsOptInvalidOptIdOptLen::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0840UrmaSetJfsOptInvalidOptIdOptLen::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：invalid opt id or opt len";
}

std::string Urma0840UrmaSetJfsOptInvalidOptIdOptLen::GetId() const
{
    return "urma_0840";
}
} // namespace diag
