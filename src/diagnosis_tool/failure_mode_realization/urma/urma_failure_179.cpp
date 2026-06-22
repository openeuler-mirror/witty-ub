#include "urma_failure_179.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure179> g_urma("urma_179");

bool UrmaFailure179::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure179::GetName() const
{
    return "URMA context、dev_fd、Jetty、配置参数无效导致创建Jetty失败";
}

std::string UrmaFailure179::GetRootCauseDesc() const
{
    return "urma_cmd_create_jetty用于创建Jetty，调用方传入的URMA "
           "context、dev_fd、Jetty、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure179::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure179::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure179::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jetty，Invalid parameter。";
}

std::string UrmaFailure179::GetId() const
{
    return "urma_179";
}
} // namespace diag
