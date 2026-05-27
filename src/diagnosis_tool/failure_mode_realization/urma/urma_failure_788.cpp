#include "urma_failure_788.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure788> g_urma("urma_788");

bool UrmaFailure788::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfs_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure788::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供set_jfs_opt操作实现无效导致设置JFS失败";
}

std::string UrmaFailure788::GetRootCauseDesc() const
{
    return "函数用于设置JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供set_jfs_"
           "opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure788::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure788::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure788::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfs_opt，Invalid parameter.";
}

std::string UrmaFailure788::GetId() const
{
    return "urma_788";
}

} // namespace diag
