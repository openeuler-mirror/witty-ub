#include "urma_failure_182.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure182> g_urma("urma_182");

bool UrmaFailure182::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_alloc_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure182::GetName() const
{
    return "URMA context、dev_fd、Jetty、配置参数无效导致分配Jetty失败";
}

std::string UrmaFailure182::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_jetty用于分配Jetty，调用方传入的URMA "
           "context、dev_fd、Jetty、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure182::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure182::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure182::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jetty，Invalid parameter。";
}

std::string UrmaFailure182::GetId() const
{
    return "urma_182";
}
} // namespace diag
