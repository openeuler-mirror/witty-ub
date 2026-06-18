#include "urma_failure_555.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure555> g_urma("urma_555");

bool UrmaFailure555::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure555::GetName() const
{
    return "Jetty、URMA context、dev_fd无效导致释放Jetty失败";
}

std::string UrmaFailure555::GetRootCauseDesc() const
{
    return "urma_cmd_free_jetty用于释放Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure555::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure555::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure555::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jetty，Invalid parameter。";
}

std::string UrmaFailure555::GetId() const
{
    return "urma_555";
}
} // namespace diag
