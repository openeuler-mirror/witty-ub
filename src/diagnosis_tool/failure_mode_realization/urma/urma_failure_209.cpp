#include "urma_failure_209.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure209> g_urma("urma_209");

bool UrmaFailure209::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_notifier") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure209::GetName() const
{
    return "URMA context无效导致创建Notifier失败";
}

std::string UrmaFailure209::GetRootCauseDesc() const
{
    return "urma_create_notifier用于创建Notifier，调用方传入的URMA context不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure209::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure209::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure209::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_notifier，Invalid parameter.。";
}

std::string UrmaFailure209::GetId() const
{
    return "urma_209";
}
} // namespace diag
