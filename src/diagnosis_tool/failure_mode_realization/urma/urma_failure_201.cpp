#include "urma_failure_201.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure201> g_urma("urma_201");

bool UrmaFailure201::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_check_trans_mode") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos &&
           message.find(", order_type:") != std::string::npos;
}

std::string UrmaFailure201::GetName() const
{
    return "Jetty、trans、MODE无效导致创建Jetty、trans、MODE失败";
}

std::string UrmaFailure201::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_trans_"
           "mode用于创建Jetty、trans、MODE，调用方传入的Jetty、trans、MODE不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure201::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure201::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure201::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_trans_mode，Invalid parameter, trans_mode:，, "
           "order_typ"
           "e:。";
}

std::string UrmaFailure201::GetId() const
{
    return "urma_201";
}
} // namespace diag
