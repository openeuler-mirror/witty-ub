#include "urma_failure_725.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure725> g_urma("urma_725");

bool UrmaFailure725::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfr") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos;
}

std::string UrmaFailure725::GetName() const
{
    return "JFR无效导致激活JFR失败";
}

std::string UrmaFailure725::GetRootCauseDesc() const
{
    return "urma_active_jfr用于激活JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure725::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure725::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure725::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfr，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure725::GetId() const
{
    return "urma_725";
}
} // namespace diag
