#include "urma_failure_698.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure698> g_urma("urma_698");

bool UrmaFailure698::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jetty_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure698::GetName() const
{
    return "Jetty、缓冲区、opt、len无效导致设置Jetty失败";
}

std::string UrmaFailure698::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_"
           "opt用于设置Jetty，调用方传入的Jetty、缓冲区、opt、len不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure698::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure698::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure698::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jetty_opt，Invalid parameter.。";
}

std::string UrmaFailure698::GetId() const
{
    return "urma_698";
}
} // namespace diag
