#include "urma_failure_582.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure582> g_urma("urma_582");

bool UrmaFailure582::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure582::GetName() const
{
    return "JFR无效导致去激活JFR失败";
}

std::string UrmaFailure582::GetRootCauseDesc() const
{
    return "urma_deactive_jfr用于去激活JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure582::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure582::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure582::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfr，Invalid parameter.。";
}

std::string UrmaFailure582::GetId() const
{
    return "urma_582";
}
} // namespace diag
