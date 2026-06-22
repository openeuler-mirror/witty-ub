#include "urma_failure_187.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure187> g_urma("urma_187");

bool UrmaFailure187::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfs") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos;
}

std::string UrmaFailure187::GetName() const
{
    return "URMA context、JFS配置、JFC无效导致创建JFS失败";
}

std::string UrmaFailure187::GetRootCauseDesc() const
{
    return "urma_create_jfs用于创建JFS，调用方传入的URMA context、JFS配置、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure187::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure187::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure187::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfs，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure187::GetId() const
{
    return "urma_187";
}
} // namespace diag
