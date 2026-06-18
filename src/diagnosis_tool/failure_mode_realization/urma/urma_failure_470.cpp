#include "urma_failure_470.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure470> g_urma("urma_470");

bool UrmaFailure470::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure470::GetName() const
{
    return "JFC无效导致去激活JFC失败";
}

std::string UrmaFailure470::GetRootCauseDesc() const
{
    return "urma_deactive_jfc用于去激活JFC，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure470::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure470::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure470::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfc，Invalid parameter.。";
}

std::string UrmaFailure470::GetId() const
{
    return "urma_470";
}
} // namespace diag
