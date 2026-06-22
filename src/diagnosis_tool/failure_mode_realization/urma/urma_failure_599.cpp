#include "urma_failure_599.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure599> g_urma("urma_599");

bool UrmaFailure599::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_notifier") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure599::GetName() const
{
    return "Notifier无效导致删除Notifier失败";
}

std::string UrmaFailure599::GetRootCauseDesc() const
{
    return "urma_delete_notifier用于删除Notifier，调用方传入的Notifier不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure599::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure599::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure599::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_notifier，Invalid parameter.。";
}

std::string UrmaFailure599::GetId() const
{
    return "urma_599";
}
} // namespace diag
