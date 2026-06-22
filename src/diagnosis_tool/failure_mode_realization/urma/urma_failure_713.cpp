#include "urma_failure_713.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure713> g_urma("urma_713");

bool UrmaFailure713::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure713::GetName() const
{
    return "JFS、JFC无效导致激活JFS失败";
}

std::string UrmaFailure713::GetRootCauseDesc() const
{
    return "urma_active_jfs用于激活JFS，调用方传入的JFS、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure713::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure713::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure713::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfs，Invalid parameter.。";
}

std::string UrmaFailure713::GetId() const
{
    return "urma_713";
}
} // namespace diag
