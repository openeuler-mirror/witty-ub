#include "urma_failure_449.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure449> g_urma("urma_449");

bool UrmaFailure449::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure449::GetName() const
{
    return "JFC无效导致删除JFC失败";
}

std::string UrmaFailure449::GetRootCauseDesc() const
{
    return "urma_delete_jfc用于删除JFC，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure449::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure449::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure449::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc，Invalid parameter.。";
}

std::string UrmaFailure449::GetId() const
{
    return "urma_449";
}
} // namespace diag
