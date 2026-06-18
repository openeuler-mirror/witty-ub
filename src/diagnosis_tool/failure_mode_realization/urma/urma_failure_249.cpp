#include "urma_failure_249.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure249> g_urma("urma_249");

bool UrmaFailure249::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jfr_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure249::GetName() const
{
    return "JFR无效导致获取JFR失败";
}

std::string UrmaFailure249::GetRootCauseDesc() const
{
    return "urma_get_jfr_opt用于获取JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure249::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure249::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure249::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure249::GetId() const
{
    return "urma_249";
}
} // namespace diag
