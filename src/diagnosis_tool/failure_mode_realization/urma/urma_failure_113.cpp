#include "urma_failure_113.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure113> g_urma("urma_113");

bool UrmaFailure113::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unbind_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure113::GetName() const
{
    return "provider未提供bind_jetty_ex操作实现无效导致解绑Jetty失败";
}

std::string UrmaFailure113::GetRootCauseDesc() const
{
    return "urma_unbind_jetty用于解绑Jetty，调用方传入的provider未提供bind_jetty_"
           "ex操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure113::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure113::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure113::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unbind_jetty，Invalid parameter.。";
}

std::string UrmaFailure113::GetId() const
{
    return "urma_113";
}
} // namespace diag
