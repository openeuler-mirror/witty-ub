#include "urma_failure_080.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure080> g_urma("urma_080");

bool UrmaFailure080::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_import_jetty_ex") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure080::GetName() const
{
    return "URMA context、dev_fd、目标Jetty、配置参数无效导致导入Jetty失败";
}

std::string UrmaFailure080::GetRootCauseDesc() const
{
    return "urma_cmd_import_jetty_ex用于导入Jetty，调用方传入的URMA "
           "context、dev_fd、目标Jetty、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure080::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure080::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure080::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_jetty_ex，Invalid parameter。";
}

std::string UrmaFailure080::GetId() const
{
    return "urma_080";
}
} // namespace diag
