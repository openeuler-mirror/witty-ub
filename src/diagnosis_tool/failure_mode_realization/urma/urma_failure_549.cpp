#include "urma_failure_549.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure549> g_urma("urma_549");

bool UrmaFailure549::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos;
}

std::string UrmaFailure549::GetName() const
{
    return "jetty_arr、bad_jetty无效导致删除Jetty失败";
}

std::string UrmaFailure549::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty_batch用于删除Jetty，调用方传入的jetty_arr、bad_"
           "jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure549::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure549::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure549::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_batch，Invalid parameter, index:。";
}

std::string UrmaFailure549::GetId() const
{
    return "urma_549";
}
} // namespace diag
