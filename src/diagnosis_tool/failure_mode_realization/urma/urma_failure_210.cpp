#include "urma_failure_210.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure210> g_urma("urma_210");

bool UrmaFailure210::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_notifier") != std::string::npos &&
           message.find("Failed to alloc notifier.") != std::string::npos;
}

std::string UrmaFailure210::GetName() const
{
    return "urma notifier incompletejetty list分配失败导致创建Notifier失败";
}

std::string UrmaFailure210::GetRootCauseDesc() const
{
    return "urma_create_notifier执行创建Notifier前需要准备urma notifier incompletejetty "
           "list，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure210::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure210::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure210::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_notifier，Failed to alloc notifier.。";
}

std::string UrmaFailure210::GetId() const
{
    return "urma_210";
}
} // namespace diag
