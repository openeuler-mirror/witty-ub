#include "urma_failure_695.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure695> g_urma("urma_695");

bool UrmaFailure695::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure695::GetName() const
{
    return "JFR、URMA context、dev_fd无效导致激活JFR失败";
}

std::string UrmaFailure695::GetRootCauseDesc() const
{
    return "urma_cmd_active_jfr用于激活JFR，调用方传入的JFR、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure695::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure695::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure695::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jfr，Invalid parameter。";
}

std::string UrmaFailure695::GetId() const
{
    return "urma_695";
}
} // namespace diag
