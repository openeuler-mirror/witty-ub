#include "urma_failure_691.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure691> g_urma("urma_691");

bool UrmaFailure691::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_advise_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure691::GetName() const
{
    return "JFS、URMA context、dev_fd、tjfr无效导致advise、JFR失败";
}

std::string UrmaFailure691::GetRootCauseDesc() const
{
    return "urma_cmd_advise_jfr用于advise、JFR，调用方传入的JFS、URMA "
           "context、dev_fd、tjfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure691::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure691::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure691::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_advise_jfr，Invalid parameter。";
}

std::string UrmaFailure691::GetId() const
{
    return "urma_691";
}
} // namespace diag
