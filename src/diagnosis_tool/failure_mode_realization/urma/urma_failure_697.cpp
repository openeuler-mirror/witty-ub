#include "urma_failure_697.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure697> g_urma("urma_697");

bool UrmaFailure697::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_modify_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure697::GetName() const
{
    return "Jetty、URMA context、dev_fd、属性参数无效导致修改Jetty失败";
}

std::string UrmaFailure697::GetRootCauseDesc() const
{
    return "urma_cmd_modify_jetty用于修改Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd、属性参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure697::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure697::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure697::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jetty，Invalid parameter。";
}

std::string UrmaFailure697::GetId() const
{
    return "urma_697";
}
} // namespace diag
