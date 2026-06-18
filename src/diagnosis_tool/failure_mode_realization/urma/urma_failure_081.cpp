#include "urma_failure_081.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure081> g_urma("urma_081");

bool UrmaFailure081::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unimport_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure081::GetName() const
{
    return "目标Jetty无效导致取消导入Jetty失败";
}

std::string UrmaFailure081::GetRootCauseDesc() const
{
    return "urma_cmd_unimport_jetty用于取消导入Jetty，调用方传入的目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure081::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure081::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure081::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unimport_jetty，Invalid parameter。";
}

std::string UrmaFailure081::GetId() const
{
    return "urma_081";
}
} // namespace diag
