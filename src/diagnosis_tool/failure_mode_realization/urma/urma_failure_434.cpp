#include "urma_failure_434.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure434> g_urma("urma_434");

bool UrmaFailure434::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfce") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure434::GetName() const
{
    return "ret无效导致创建JFCE失败";
}

std::string UrmaFailure434::GetRootCauseDesc() const
{
    return "urma_cmd_create_jfce用于创建JFCE，调用方传入的ret不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure434::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure434::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure434::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfce，Invalid parameter。";
}

std::string UrmaFailure434::GetId() const
{
    return "urma_434";
}
} // namespace diag
