#include "urma_failure_618.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure618> g_urma("urma_618");

bool UrmaFailure618::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure618::GetName() const
{
    return "URMA context、JFS对象无效导致释放JFS失败";
}

std::string UrmaFailure618::GetRootCauseDesc() const
{
    return "函数用于释放JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure618::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure618::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure618::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_free_jfs，Invalid parameter";
}

std::string UrmaFailure618::GetId() const
{
    return "urma_618";
}

} // namespace diag
