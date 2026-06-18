#include "urma_failure_115.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure115> g_urma("urma_115");

bool UrmaFailure115::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jetty_async") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure115::GetName() const
{
    return "Notifier、URMA context、rjetty、token_value无效导致导入Jetty失败";
}

std::string UrmaFailure115::GetRootCauseDesc() const
{
    return "urma_import_jetty_async用于导入Jetty，调用方传入的Notifier、URMA "
           "context、rjetty、token_value不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure115::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure115::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure115::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jetty_async，Invalid parameter.。";
}

std::string UrmaFailure115::GetId() const
{
    return "urma_115";
}
} // namespace diag
