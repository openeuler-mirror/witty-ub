#include "urma_failure_751.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure751> g_urma("urma_751");

bool UrmaFailure751::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_getenv_log_level") != std::string::npos &&
           message.find("Invalid parameter: log level str.") != std::string::npos;
}

std::string UrmaFailure751::GetName() const
{
    return "level_str无效导致getenvgetenv、LOG、level失败";
}

std::string UrmaFailure751::GetRootCauseDesc() const
{
    return "urma_getenv_log_level用于getenvgetenv、LOG、level，调用方传入的level_"
           "str不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure751::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure751::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure751::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_getenv_log_level，Invalid parameter: log level str.。";
}

std::string UrmaFailure751::GetId() const
{
    return "urma_751";
}
} // namespace diag
