#include "urma_0075_bind_jetty_single_path_no_valid_direct_route.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0075BindJettySinglePathNoValidDirectRoute> g_urma("urma_0075");

bool Urma0075BindJettySinglePathNoValidDirectRoute::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"No valid direct route"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0075BindJettySinglePathNoValidDirectRoute::GetName() const
{
    return "bind_jetty_single_path No valid direct route";
}

std::string Urma0075BindJettySinglePathNoValidDirectRoute::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!has_valid_route`；该路径返回 URMA_FAIL";
}

RootCause Urma0075BindJettySinglePathNoValidDirectRoute::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0075BindJettySinglePathNoValidDirectRoute::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0075BindJettySinglePathNoValidDirectRoute::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：No valid direct route";
}

std::string Urma0075BindJettySinglePathNoValidDirectRoute::GetId() const
{
    return "urma_0075";
}
} // namespace diag
