#include "urma_failure_588.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure588> g_urma("urma_588");

bool UrmaFailure588::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure588::GetName() const
{
    return "Jetty无效导致删除Jetty失败";
}

std::string UrmaFailure588::GetRootCauseDesc() const
{
    return "urma_delete_jetty用于删除Jetty，调用方传入的Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure588::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure588::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure588::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty，Invalid parameter.。";
}

std::string UrmaFailure588::GetId() const
{
    return "urma_588";
}
} // namespace diag
