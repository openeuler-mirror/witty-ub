#include "urma_failure_660.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure660> g_urma("urma_660");

bool UrmaFailure660::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure660::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致删除JFS失败";
}

std::string UrmaFailure660::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure660::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure660::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure660::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfs_batch，Invalid parameter.";
}

std::string UrmaFailure660::GetId() const
{
    return "urma_660";
}

} // namespace diag
