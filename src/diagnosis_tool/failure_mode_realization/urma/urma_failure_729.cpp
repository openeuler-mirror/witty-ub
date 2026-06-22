#include "urma_failure_729.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure729> g_urma("urma_729");

bool UrmaFailure729::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_advise_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure729::GetName() const
{
    return "provider未提供unbind_jetty操作实现无效导致adviseadvise、Jetty失败";
}

std::string UrmaFailure729::GetRootCauseDesc() const
{
    return "urma_advise_jetty用于adviseadvise、Jetty，调用方传入的provider未提供unbind_"
           "jetty操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure729::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure729::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure729::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_advise_jetty，Invalid parameter.。";
}

std::string UrmaFailure729::GetId() const
{
    return "urma_729";
}
} // namespace diag
