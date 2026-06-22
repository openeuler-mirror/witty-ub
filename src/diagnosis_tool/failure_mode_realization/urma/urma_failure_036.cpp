#include "urma_failure_036.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure036> g_urma("urma_036");

bool UrmaFailure036::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("init_create_jetty_cmd") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure036::GetName() const
{
    return "JFC无效导致初始化Jetty失败";
}

std::string UrmaFailure036::GetRootCauseDesc() const
{
    return "init_create_jetty_cmd用于初始化Jetty，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure036::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure036::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure036::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：init_create_jetty_cmd，Invalid parameter。";
}

std::string UrmaFailure036::GetId() const
{
    return "urma_036";
}
} // namespace diag
