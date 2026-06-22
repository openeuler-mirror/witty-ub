#include "urma_failure_106.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure106> g_urma("urma_106");

bool UrmaFailure106::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unimport_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure106::GetName() const
{
    return "目标Jetty无效导致取消导入Jetty失败";
}

std::string UrmaFailure106::GetRootCauseDesc() const
{
    return "urma_unimport_jetty用于取消导入Jetty，调用方传入的目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure106::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure106::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure106::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_jetty，Invalid parameter.。";
}

std::string UrmaFailure106::GetId() const
{
    return "urma_106";
}
} // namespace diag
