#include "urma_failure_590.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure590> g_urma("urma_590");

bool UrmaFailure590::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_batch") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure590::GetName() const
{
    return "jetty_arr、bad_jetty无效导致删除Jetty失败";
}

std::string UrmaFailure590::GetRootCauseDesc() const
{
    return "urma_delete_jetty_batch用于删除Jetty，调用方传入的jetty_arr、bad_"
           "jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure590::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure590::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure590::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_batch，Invalid parameter.。";
}

std::string UrmaFailure590::GetId() const
{
    return "urma_590";
}
} // namespace diag
