#include "urma_1194_bdp_queue_pop_tail_data_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1194BdpQueuePopTailDataIsNull> g_urma("urma_1194");

bool Urma1194BdpQueuePopTailDataIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"data is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1194BdpQueuePopTailDataIsNull::GetName() const
{
    return "bdp_queue_pop_tail data is NULL";
}

std::string Urma1194BdpQueuePopTailDataIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `data == NULL`；该路径返回 -1";
}

RootCause Urma1194BdpQueuePopTailDataIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1194BdpQueuePopTailDataIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1194BdpQueuePopTailDataIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：data is NULL";
}

std::string Urma1194BdpQueuePopTailDataIsNull::GetId() const
{
    return "urma_1194";
}
} // namespace diag
