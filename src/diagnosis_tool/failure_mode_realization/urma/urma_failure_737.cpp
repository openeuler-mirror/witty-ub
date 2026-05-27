#include "urma_failure_737.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure737> g_urma("urma_737");

bool UrmaFailure737::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfs_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure737::GetName() const
{
    return "URMA context、JFS对象无效导致设置JFS失败";
}

std::string UrmaFailure737::GetRootCauseDesc() const
{
    return "函数用于设置JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure737::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure737::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure737::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_jfs_opt，Invalid parameter.";
}

std::string UrmaFailure737::GetId() const
{
    return "urma_737";
}

} // namespace diag
