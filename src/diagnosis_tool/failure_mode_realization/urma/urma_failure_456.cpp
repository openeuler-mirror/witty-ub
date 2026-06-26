#include "urma_failure_456.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure456> g_urma("urma_456");

bool UrmaFailure456::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure456::GetName() const
{
    return "URMA context、配置参数、JFC无效导致分配JFC失败";
}

std::string UrmaFailure456::GetRootCauseDesc() const
{
    return "urma_alloc_jfc用于分配JFC，调用方传入的URMA context、配置参数、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure456::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure456::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure456::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfc，Invalid parameter.。";
}

std::string UrmaFailure456::GetId() const
{
    return "urma_456";
}
} // namespace diag
