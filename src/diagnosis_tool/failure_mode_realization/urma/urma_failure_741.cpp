#include "urma_failure_741.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure741> g_urma("urma_741");

bool UrmaFailure741::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_modify_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure741::GetName() const
{
    return "URMA context、JFS对象、JFR对象无效导致修改JFR失败";
}

std::string UrmaFailure741::GetRootCauseDesc() const
{
    return "函数用于修改JFR，调用方传入的URMA context、JFS对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
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
    return "通过 URMA 日志关键字校验：urma_cmd_modify_jfr，Invalid parameter";
}

std::string UrmaFailure741::GetId() const
{
    return "urma_741";
}

} // namespace diag
