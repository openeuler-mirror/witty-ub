#include "urma_1192_bdp_queue_pop_head_data_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1192BdpQueuePopHeadDataIsNull> g_urma("urma_1192");

bool Urma1192BdpQueuePopHeadDataIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"data is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1192BdpQueuePopHeadDataIsNull::GetName() const
{
    return "bdp_queue_pop_head data is NULL";
}

std::string Urma1192BdpQueuePopHeadDataIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `data == NULL`；该路径返回 -1";
}

RootCause Urma1192BdpQueuePopHeadDataIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1192BdpQueuePopHeadDataIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1192BdpQueuePopHeadDataIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：data is NULL";
}

std::string Urma1192BdpQueuePopHeadDataIsNull::GetId() const
{
    return "urma_1192";
}
} // namespace diag
