#include "urma_1190_bdp_queue_front_data_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1190BdpQueueFrontDataIsNull> g_urma("urma_1190");

bool Urma1190BdpQueueFrontDataIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"data is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1190BdpQueueFrontDataIsNull::GetName() const
{
    return "bdp_queue_front data is NULL";
}

std::string Urma1190BdpQueueFrontDataIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `data == NULL`；该路径返回 -1";
}

RootCause Urma1190BdpQueueFrontDataIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1190BdpQueueFrontDataIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1190BdpQueueFrontDataIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：data is NULL";
}

std::string Urma1190BdpQueueFrontDataIsNull::GetId() const
{
    return "urma_1190";
}
} // namespace diag
