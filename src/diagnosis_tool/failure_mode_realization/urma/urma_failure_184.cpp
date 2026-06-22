#include "urma_failure_184.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure184> g_urma("urma_184");

bool UrmaFailure184::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_notifier") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure184::GetName() const
{
    return "URMA context、dev_fd无效导致创建Notifier失败";
}

std::string UrmaFailure184::GetRootCauseDesc() const
{
    return "urma_cmd_create_notifier用于创建Notifier，调用方传入的URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure184::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure184::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure184::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_notifier，Invalid parameter。";
}

std::string UrmaFailure184::GetId() const
{
    return "urma_184";
}
} // namespace diag
