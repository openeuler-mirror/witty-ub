#include "urma_failure_623.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure623> g_urma("urma_623");

bool UrmaFailure623::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfr_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure623::GetName() const
{
    return "URMA context、JFR对象无效导致删除JFR失败";
}

std::string UrmaFailure623::GetRootCauseDesc() const
{
    return "函数用于删除JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure623::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure623::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure623::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfr_batch，Invalid parameter, index:";
}

std::string UrmaFailure623::GetId() const
{
    return "urma_623";
}

} // namespace diag
