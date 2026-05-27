#include "urma_failure_851.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure851> g_urma("urma_851");

bool UrmaFailure851::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_advise_jfr_async' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure851::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致执行JFR失败";
}

std::string UrmaFailure851::GetRootCauseDesc() const
{
    return "函数用于执行JFR，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure851::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure851::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure851::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_advise_jfr_async，Invalid parameter.。";
}

std::string UrmaFailure851::GetId() const
{
    return "urma_851";
}

} // namespace diag
