#include "urma_failure_728.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure728> g_urma("urma_728");

bool UrmaFailure728::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_modify_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure728::GetName() const
{
    return "Jetty、属性参数无效导致修改Jetty失败";
}

std::string UrmaFailure728::GetRootCauseDesc() const
{
    return "urma_modify_jetty用于修改Jetty，调用方传入的Jetty、属性参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure728::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure728::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure728::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jetty，Invalid parameter.。";
}

std::string UrmaFailure728::GetId() const
{
    return "urma_728";
}
} // namespace diag
