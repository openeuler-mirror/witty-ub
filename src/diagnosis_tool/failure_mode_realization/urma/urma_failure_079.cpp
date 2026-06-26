#include "urma_failure_079.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure079> g_urma("urma_079");

bool UrmaFailure079::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_import_jetty") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure079::GetName() const
{
    return "URMA context、dev_fd、目标Jetty、配置参数无效导致导入Jetty失败";
}

std::string UrmaFailure079::GetRootCauseDesc() const
{
    return "urma_cmd_import_jetty用于导入Jetty，调用方传入的URMA "
           "context、dev_fd、目标Jetty、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure079::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure079::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure079::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_jetty，Invalid parameter。";
}

std::string UrmaFailure079::GetId() const
{
    return "urma_079";
}
} // namespace diag
