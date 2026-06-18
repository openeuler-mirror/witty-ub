#include "urma_failure_602.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure602> g_urma("urma_602");

bool UrmaFailure602::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty_grp") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure602::GetName() const
{
    return "jetty_grp无效导致删除Jetty组失败";
}

std::string UrmaFailure602::GetRootCauseDesc() const
{
    return "urma_delete_jetty_grp用于删除Jetty组，调用方传入的jetty_grp不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure602::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure602::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure602::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_grp，Invalid parameter.。";
}

std::string UrmaFailure602::GetId() const
{
    return "urma_602";
}
} // namespace diag
