#include "urma_failure_083.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure083> g_urma("urma_083");

bool UrmaFailure083::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_import_jetty_async") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure083::GetName() const
{
    return "Notifier、URMA context、dev_fd、目标Jetty无效导致导入Jetty失败";
}

std::string UrmaFailure083::GetRootCauseDesc() const
{
    return "urma_cmd_import_jetty_async用于导入Jetty，调用方传入的Notifier、URMA "
           "context、dev_fd、目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure083::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure083::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure083::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_jetty_async，Invalid parameter。";
}

std::string UrmaFailure083::GetId() const
{
    return "urma_083";
}
} // namespace diag
