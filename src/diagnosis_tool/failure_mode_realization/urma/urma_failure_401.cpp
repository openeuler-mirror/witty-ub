#include "urma_failure_401.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure401> g_urma("urma_401");

bool UrmaFailure401::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("schedule_recv") != std::string::npos && message.find("No active port") != std::string::npos;
}

std::string UrmaFailure401::GetName() const
{
    return "schedule状态不满足要求导致接收schedule失败";
}

std::string UrmaFailure401::GetRootCauseDesc() const
{
    return "schedule_recv执行接收schedule时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure401::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure401::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure401::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：schedule_recv，No active port。";
}

std::string UrmaFailure401::GetId() const
{
    return "urma_401";
}
} // namespace diag
