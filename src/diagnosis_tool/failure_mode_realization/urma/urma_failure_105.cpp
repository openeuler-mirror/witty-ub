#include "urma_failure_105.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure105> g_urma("urma_105");

bool UrmaFailure105::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jetty_ex") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure105::GetName() const
{
    return "URMA context、rjetty、token_value、配置参数无效导致导入Jetty失败";
}

std::string UrmaFailure105::GetRootCauseDesc() const
{
    return "urma_import_jetty_ex用于导入Jetty，调用方传入的URMA "
           "context、rjetty、token_value、配置参数不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure105::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure105::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure105::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jetty_ex，Invalid parameter.。";
}

std::string UrmaFailure105::GetId() const
{
    return "urma_105";
}
} // namespace diag
