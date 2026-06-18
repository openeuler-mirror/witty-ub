#include "urma_failure_443.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure443> g_urma("urma_443");

bool UrmaFailure443::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure443::GetName() const
{
    return "URMA context、JFC配置无效导致创建JFC失败";
}

std::string UrmaFailure443::GetRootCauseDesc() const
{
    return "urma_create_jfc用于创建JFC，调用方传入的URMA context、JFC配置不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure443::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure443::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure443::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfc，Invalid parameter.。";
}

std::string UrmaFailure443::GetId() const
{
    return "urma_443";
}
} // namespace diag
