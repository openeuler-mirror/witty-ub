#include "urma_1016_import_pseg_port_eid_no_valid_direct_route.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1016ImportPsegPortEidNoValidDirectRoute> g_urma("urma_1016");

bool Urma1016ImportPsegPortEidNoValidDirectRoute::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"No valid direct route"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1016ImportPsegPortEidNoValidDirectRoute::GetName() const
{
    return "import_pseg_for_port_eid No valid direct route";
}

std::string Urma1016ImportPsegPortEidNoValidDirectRoute::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!has_valid_route`；该路径返回 -1";
}

RootCause Urma1016ImportPsegPortEidNoValidDirectRoute::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1016ImportPsegPortEidNoValidDirectRoute::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1016ImportPsegPortEidNoValidDirectRoute::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：No valid direct route";
}

std::string Urma1016ImportPsegPortEidNoValidDirectRoute::GetId() const
{
    return "urma_1016";
}
} // namespace diag
