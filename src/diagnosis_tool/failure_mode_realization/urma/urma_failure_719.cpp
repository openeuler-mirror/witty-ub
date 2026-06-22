#include "urma_failure_719.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure719> g_urma("urma_719");

bool UrmaFailure719::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfr_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure719::GetName() const
{
    return "JFR、缓冲区、len无效导致设置JFR失败";
}

std::string UrmaFailure719::GetRootCauseDesc() const
{
    return "urma_set_jfr_opt用于设置JFR，调用方传入的JFR、缓冲区、len不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure719::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure719::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure719::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure719::GetId() const
{
    return "urma_719";
}
} // namespace diag
