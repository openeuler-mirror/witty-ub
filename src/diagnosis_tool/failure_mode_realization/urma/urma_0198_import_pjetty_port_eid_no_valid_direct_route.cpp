#include "urma_0198_import_pjetty_port_eid_no_valid_direct_route.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0198ImportPjettyPortEidNoValidDirectRoute> g_urma("urma_0198");

bool Urma0198ImportPjettyPortEidNoValidDirectRoute::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"No valid direct route"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0198ImportPjettyPortEidNoValidDirectRoute::GetName() const
{
    return "import_pjetty_for_port_eid No valid direct route";
}

std::string Urma0198ImportPjettyPortEidNoValidDirectRoute::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!has_valid_route`；该路径返回 -1";
}

RootCause Urma0198ImportPjettyPortEidNoValidDirectRoute::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0198ImportPjettyPortEidNoValidDirectRoute::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0198ImportPjettyPortEidNoValidDirectRoute::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：No valid direct route";
}

std::string Urma0198ImportPjettyPortEidNoValidDirectRoute::GetId() const
{
    return "urma_0198";
}
} // namespace diag
