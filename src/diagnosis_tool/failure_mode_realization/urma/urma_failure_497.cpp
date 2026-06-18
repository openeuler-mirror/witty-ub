#include "urma_failure_497.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure497> g_urma("urma_497");

bool UrmaFailure497::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_post_jetty_recv_wr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure497::GetName() const
{
    return "dp_ops、post_jetty_recv_wr、工作请求、bad_wr无效导致投递Jetty、工作请求失败";
}

std::string UrmaFailure497::GetRootCauseDesc() const
{
    return "urma_post_jetty_recv_wr用于投递Jetty、工作请求，调用方传入的dp_ops、post_jetty_recv_wr、工作请求、bad_"
           "wr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure497::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure497::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure497::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_post_jetty_recv_wr，Invalid parameter.。";
}

std::string UrmaFailure497::GetId() const
{
    return "urma_497";
}
} // namespace diag
