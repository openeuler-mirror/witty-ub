#include "urma_failure_668.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure668> g_urma("urma_668");

bool UrmaFailure668::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Invalid parameter, index:' | grep -F 'jfs in the array is NULL.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure668::GetName() const
{
    return "JFS对象无效导致删除JFS失败";
}

std::string UrmaFailure668::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure668::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure668::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure668::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Invalid parameter, index:，jfs in the array is "
           "NULL.。";
}

std::string UrmaFailure668::GetId() const
{
    return "urma_668";
}

} // namespace diag
