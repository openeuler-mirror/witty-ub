#include "urma_failure_199.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure199> g_urma("urma_199");

bool UrmaFailure199::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_check_trans_mode") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos;
}

std::string UrmaFailure199::GetName() const
{
    return "Jetty、trans、MODE无效导致创建Jetty、trans、MODE失败";
}

std::string UrmaFailure199::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_trans_"
           "mode用于创建Jetty、trans、MODE，调用方传入的Jetty、trans、MODE不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure199::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure199::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure199::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_trans_mode，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure199::GetId() const
{
    return "urma_199";
}
} // namespace diag
