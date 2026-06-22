#include "urma_failure_398.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure398> g_urma("urma_398");

bool UrmaFailure398::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("schedule_send_balance") != std::string::npos &&
           message.find("Invalid min_active_count.") != std::string::npos;
}

std::string UrmaFailure398::GetName() const
{
    return "schedule、balance状态不满足要求导致发送schedule、balance失败";
}

std::string UrmaFailure398::GetRootCauseDesc() const
{
    return "schedule_send_"
           "balance执行发送schedule、balance时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure398::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure398::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure398::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：schedule_send_balance，Invalid min_active_count.。";
}

std::string UrmaFailure398::GetId() const
{
    return "urma_398";
}
} // namespace diag
