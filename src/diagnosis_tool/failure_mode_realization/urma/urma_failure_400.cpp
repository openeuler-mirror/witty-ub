#include "urma_failure_400.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure400> g_urma("urma_400");

bool UrmaFailure400::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("schedule_send") != std::string::npos && message.find("No active port") != std::string::npos;
}

std::string UrmaFailure400::GetName() const
{
    return "schedule状态不满足要求导致发送schedule失败";
}

std::string UrmaFailure400::GetRootCauseDesc() const
{
    return "schedule_send执行发送schedule时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure400::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure400::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure400::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：schedule_send，No active port。";
}

std::string UrmaFailure400::GetId() const
{
    return "urma_400";
}
} // namespace diag
