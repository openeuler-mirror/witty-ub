#include "urma_failure_186.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure186> g_urma("urma_186");

bool UrmaFailure186::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure186::GetName() const
{
    return "URMA context、JFS配置、JFC无效导致创建JFS失败";
}

std::string UrmaFailure186::GetRootCauseDesc() const
{
    return "urma_create_jfs用于创建JFS，调用方传入的URMA context、JFS配置、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure186::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure186::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure186::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfs，Invalid parameter.。";
}

std::string UrmaFailure186::GetId() const
{
    return "urma_186";
}
} // namespace diag
