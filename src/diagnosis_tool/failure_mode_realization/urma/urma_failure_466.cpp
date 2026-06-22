#include "urma_failure_466.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure466> g_urma("urma_466");

bool UrmaFailure466::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure466::GetName() const
{
    return "JFC无效导致激活JFC失败";
}

std::string UrmaFailure466::GetRootCauseDesc() const
{
    return "urma_active_jfc用于激活JFC，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure466::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure466::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure466::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfc，Invalid parameter.。";
}

std::string UrmaFailure466::GetId() const
{
    return "urma_466";
}
} // namespace diag
