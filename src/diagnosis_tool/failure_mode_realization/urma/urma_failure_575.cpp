#include "urma_failure_575.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure575> g_urma("urma_575");

bool UrmaFailure575::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure575::GetName() const
{
    return "JFR无效导致删除JFR失败";
}

std::string UrmaFailure575::GetRootCauseDesc() const
{
    return "urma_delete_jfr用于删除JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure575::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure575::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure575::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr，Invalid parameter.。";
}

std::string UrmaFailure575::GetId() const
{
    return "urma_575";
}
} // namespace diag
