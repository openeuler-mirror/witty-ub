#include "urma_failure_254.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure254> g_urma("urma_254");

bool UrmaFailure254::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_query_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure254::GetName() const
{
    return "provider未提供modify_jetty操作实现无效导致查询Jetty失败";
}

std::string UrmaFailure254::GetRootCauseDesc() const
{
    return "urma_query_jetty用于查询Jetty，调用方传入的provider未提供modify_"
           "jetty操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure254::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure254::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure254::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_jetty，Invalid parameter.。";
}

std::string UrmaFailure254::GetId() const
{
    return "urma_254";
}
} // namespace diag
