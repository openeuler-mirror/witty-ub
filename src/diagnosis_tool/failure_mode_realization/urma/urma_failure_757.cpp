#include "urma_failure_757.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure757> g_urma("urma_757");

bool UrmaFailure757::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_context_opt") != std::string::npos &&
           message.find("Invalid option value.") != std::string::npos;
}

std::string UrmaFailure757::GetName() const
{
    return "context状态不满足要求导致设置context失败";
}

std::string UrmaFailure757::GetRootCauseDesc() const
{
    return "urma_set_context_opt执行设置context时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure757::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure757::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure757::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_context_opt，Invalid option value.。";
}

std::string UrmaFailure757::GetId() const
{
    return "urma_757";
}
} // namespace diag
