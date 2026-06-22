#include "urma_failure_622.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure622> g_urma("urma_622");

bool UrmaFailure622::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfr_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure622::GetName() const
{
    return "JFR无效导致获取JFR失败";
}

std::string UrmaFailure622::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfr_opt用于获取JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure622::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure622::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure622::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure622::GetId() const
{
    return "urma_622";
}
} // namespace diag
