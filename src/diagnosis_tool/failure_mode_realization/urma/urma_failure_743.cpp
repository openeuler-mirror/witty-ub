#include "urma_failure_743.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure743> g_urma("urma_743");

bool UrmaFailure743::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_advise_jfr_async") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure743::GetName() const
{
    return "JFS、tjfr、cb_fun、cb_arg无效导致adviseadvise、JFR失败";
}

std::string UrmaFailure743::GetRootCauseDesc() const
{
    return "urma_advise_jfr_async用于adviseadvise、JFR，调用方传入的JFS、tjfr、cb_fun、cb_"
           "arg不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure743::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure743::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure743::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_advise_jfr_async，Invalid parameter.。";
}

std::string UrmaFailure743::GetId() const
{
    return "urma_743";
}
} // namespace diag
