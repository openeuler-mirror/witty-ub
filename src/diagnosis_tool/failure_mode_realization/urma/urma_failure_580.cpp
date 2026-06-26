#include "urma_failure_580.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure580> g_urma("urma_580");

bool UrmaFailure580::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos;
}

std::string UrmaFailure580::GetName() const
{
    return "JFR无效导致删除JFR失败";
}

std::string UrmaFailure580::GetRootCauseDesc() const
{
    return "urma_delete_jfr_batch用于删除JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure580::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure580::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure580::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr_batch，Invalid parameter, index:。";
}

std::string UrmaFailure580::GetId() const
{
    return "urma_580";
}
} // namespace diag
