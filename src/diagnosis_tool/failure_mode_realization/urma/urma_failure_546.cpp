#include "urma_failure_546.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure546> g_urma("urma_546");

bool UrmaFailure546::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure546::GetName() const
{
    return "Jetty、URMA context、dev_fd无效导致删除Jetty失败";
}

std::string UrmaFailure546::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty用于删除Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure546::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure546::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure546::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty，Invalid parameter。";
}

std::string UrmaFailure546::GetId() const
{
    return "urma_546";
}
} // namespace diag
