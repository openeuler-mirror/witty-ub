#include "urma_failure_425.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure425> g_urma("urma_425");

bool UrmaFailure425::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfs_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure425::GetName() const
{
    return "URMA context、JFS对象无效导致获取JFS失败";
}

std::string UrmaFailure425::GetRootCauseDesc() const
{
    return "函数用于获取JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure425::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure425::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure425::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_jfs_opt，Invalid parameter.";
}

std::string UrmaFailure425::GetId() const
{
    return "urma_425";
}

} // namespace diag
