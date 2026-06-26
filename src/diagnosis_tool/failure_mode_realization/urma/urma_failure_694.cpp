#include "urma_failure_694.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure694> g_urma("urma_694");

bool UrmaFailure694::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jfr_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure694::GetName() const
{
    return "JFR、缓冲区、opt、len无效导致设置JFR失败";
}

std::string UrmaFailure694::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfr_opt用于设置JFR，调用方传入的JFR、缓冲区、opt、len不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure694::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure694::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure694::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure694::GetId() const
{
    return "urma_694";
}
} // namespace diag
