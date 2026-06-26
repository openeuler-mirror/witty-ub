#include "urma_failure_586.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure586> g_urma("urma_586");

bool UrmaFailure586::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure586::GetName() const
{
    return "provider未提供query_jetty操作实现无效导致释放Jetty失败";
}

std::string UrmaFailure586::GetRootCauseDesc() const
{
    return "urma_free_jetty用于释放Jetty，调用方传入的provider未提供query_"
           "jetty操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure586::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure586::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure586::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jetty，Invalid parameter.。";
}

std::string UrmaFailure586::GetId() const
{
    return "urma_586";
}
} // namespace diag
