#include "urma_failure_851.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure851> g_urma("urma_851");

bool UrmaFailure851::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'check_valid_sgl' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'sge is a null pointer.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure851::GetName() const
{
    return "执行context过程中依赖步骤失败";
}

std::string UrmaFailure851::GetRootCauseDesc() const
{
    return "函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
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
    return "通过 URMA 日志关键字校验：check_valid_sgl，sge is a null pointer.";
}

std::string UrmaFailure851::GetId() const
{
    return "urma_851";
}

} // namespace diag
