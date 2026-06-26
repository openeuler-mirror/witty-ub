#include "urma_failure_103.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure103> g_urma("urma_103");

bool UrmaFailure103::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jetty_compat") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure103::GetName() const
{
    return "provider未提供import_jetty_ex操作实现无效导致导入Jetty、compat失败";
}

std::string UrmaFailure103::GetRootCauseDesc() const
{
    return "urma_import_jetty_compat用于导入Jetty、compat，调用方传入的provider未提供import_jetty_"
           "ex操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure103::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure103::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure103::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jetty_compat，Invalid parameter.。";
}

std::string UrmaFailure103::GetId() const
{
    return "urma_103";
}
} // namespace diag
