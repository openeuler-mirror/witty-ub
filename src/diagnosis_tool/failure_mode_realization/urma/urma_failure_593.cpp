#include "urma_failure_593.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure593> g_urma("urma_593");

bool UrmaFailure593::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos;
}

std::string UrmaFailure593::GetName() const
{
    return "Jetty无效导致删除Jetty失败";
}

std::string UrmaFailure593::GetRootCauseDesc() const
{
    return "urma_delete_jetty_batch用于删除Jetty，调用方传入的Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure593::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure593::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure593::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_batch，Invalid parameter, index:。";
}

std::string UrmaFailure593::GetId() const
{
    return "urma_593";
}
} // namespace diag
