#include "urma_failure_741.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure741> g_urma("urma_741");

bool UrmaFailure741::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_advise_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure741::GetName() const
{
    return "JFS、tjfr无效导致adviseadvise、JFR失败";
}

std::string UrmaFailure741::GetRootCauseDesc() const
{
    return "urma_advise_jfr用于adviseadvise、JFR，调用方传入的JFS、tjfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure741::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure741::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure741::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_advise_jfr，Invalid parameter.。";
}

std::string UrmaFailure741::GetId() const
{
    return "urma_741";
}
} // namespace diag
