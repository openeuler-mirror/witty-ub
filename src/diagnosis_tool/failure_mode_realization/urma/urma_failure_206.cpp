#include "urma_failure_206.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure206> g_urma("urma_206");

bool UrmaFailure206::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure206::GetName() const
{
    return "provider未提供unbind_jetty_async操作实现无效导致分配Jetty失败";
}

std::string UrmaFailure206::GetRootCauseDesc() const
{
    return "urma_alloc_jetty用于分配Jetty，调用方传入的provider未提供unbind_jetty_"
           "async操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure206::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure206::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure206::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jetty，Invalid parameter.。";
}

std::string UrmaFailure206::GetId() const
{
    return "urma_206";
}
} // namespace diag
