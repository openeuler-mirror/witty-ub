#include "urma_failure_626.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure626> g_urma("urma_626");

bool UrmaFailure626::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_query_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure626::GetName() const
{
    return "Jetty、URMA context、dev_fd、配置参数无效导致查询Jetty失败";
}

std::string UrmaFailure626::GetRootCauseDesc() const
{
    return "urma_cmd_query_jetty用于查询Jetty，调用方传入的Jetty、URMA "
           "context、dev_fd、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure626::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure626::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure626::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_query_jetty，Invalid parameter。";
}

std::string UrmaFailure626::GetId() const
{
    return "urma_626";
}
} // namespace diag
