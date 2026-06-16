#include "urma_failure_620.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure620> g_urma("urma_620");

bool UrmaFailure620::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfs_batch' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure620::GetName() const
{
    return "URMA context、JFS对象无效导致删除JFS失败";
}

std::string UrmaFailure620::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure620::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure620::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure620::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs_batch，Invalid parameter, index:。";
}

std::string UrmaFailure620::GetId() const
{
    return "urma_620";
}

} // namespace diag
