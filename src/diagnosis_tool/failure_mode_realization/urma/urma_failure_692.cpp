#include "urma_failure_692.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure692> g_urma("urma_692");

bool UrmaFailure692::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unadvise_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure692::GetName() const
{
    return "JFS、URMA context、dev_fd、tjfr无效导致unadvise、JFR失败";
}

std::string UrmaFailure692::GetRootCauseDesc() const
{
    return "urma_cmd_unadvise_jfr用于unadvise、JFR，调用方传入的JFS、URMA "
           "context、dev_fd、tjfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure692::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure692::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure692::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unadvise_jfr，Invalid parameter。";
}

std::string UrmaFailure692::GetId() const
{
    return "urma_692";
}
} // namespace diag
