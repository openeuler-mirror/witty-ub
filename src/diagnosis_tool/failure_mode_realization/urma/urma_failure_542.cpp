#include "urma_failure_542.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure542> g_urma("urma_542");

bool UrmaFailure542::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure542::GetName() const
{
    return "JFR无效导致释放JFR失败";
}

std::string UrmaFailure542::GetRootCauseDesc() const
{
    return "urma_cmd_free_jfr用于释放JFR，调用方传入的JFR不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure542::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure542::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure542::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfr，Invalid parameter。";
}

std::string UrmaFailure542::GetId() const
{
    return "urma_542";
}
} // namespace diag
