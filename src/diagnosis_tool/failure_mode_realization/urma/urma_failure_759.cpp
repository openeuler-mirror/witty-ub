#include "urma_failure_759.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure759> g_urma("urma_759");

bool UrmaFailure759::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_context_opt") != std::string::npos &&
           message.find("Invalid option name.") != std::string::npos;
}

std::string UrmaFailure759::GetName() const
{
    return "context状态不满足要求导致设置context失败";
}

std::string UrmaFailure759::GetRootCauseDesc() const
{
    return "urma_set_context_opt执行设置context时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure759::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure759::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure759::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_context_opt，Invalid option name.。";
}

std::string UrmaFailure759::GetId() const
{
    return "urma_759";
}
} // namespace diag
