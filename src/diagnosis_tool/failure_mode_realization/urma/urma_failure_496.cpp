#include "urma_failure_496.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure496> g_urma("urma_496");

bool UrmaFailure496::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_post_jetty_send_wr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure496::GetName() const
{
    return "dp_ops、post_jetty_send_wr、工作请求、bad_wr无效导致投递Jetty、工作请求失败";
}

std::string UrmaFailure496::GetRootCauseDesc() const
{
    return "urma_post_jetty_send_wr用于投递Jetty、工作请求，调用方传入的dp_ops、post_jetty_send_wr、工作请求、bad_"
           "wr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure496::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure496::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure496::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_post_jetty_send_wr，Invalid parameter.。";
}

std::string UrmaFailure496::GetId() const
{
    return "urma_496";
}
} // namespace diag
