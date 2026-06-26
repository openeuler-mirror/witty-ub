#include "urma_failure_459.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure459> g_urma("urma_459");

bool UrmaFailure459::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfc_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure459::GetName() const
{
    return "JFC、缓冲区、len无效导致设置JFC失败";
}

std::string UrmaFailure459::GetRootCauseDesc() const
{
    return "urma_set_jfc_opt用于设置JFC，调用方传入的JFC、缓冲区、len不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure459::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure459::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure459::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfc_opt，Invalid parameter.。";
}

std::string UrmaFailure459::GetId() const
{
    return "urma_459";
}
} // namespace diag
