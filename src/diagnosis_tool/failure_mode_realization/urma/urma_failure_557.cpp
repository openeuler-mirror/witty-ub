#include "urma_failure_557.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure557> g_urma("urma_557");

bool UrmaFailure557::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_deactive_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure557::GetName() const
{
    return "Jetty、URMA context、dev_fd无效导致去激活Jetty失败";
}

std::string UrmaFailure557::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_jetty用于去激活Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure557::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure557::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure557::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jetty，Invalid parameter。";
}

std::string UrmaFailure557::GetId() const
{
    return "urma_557";
}
} // namespace diag
