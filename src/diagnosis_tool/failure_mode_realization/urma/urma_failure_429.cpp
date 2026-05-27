#include "urma_failure_429.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure429> g_urma("urma_429");

bool UrmaFailure429::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfs_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure429::GetName() const
{
    return "URMA context、JFS对象无效导致获取JFS失败";
}

std::string UrmaFailure429::GetRootCauseDesc() const
{
    return "函数用于获取JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure429::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure429::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure429::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfs_opt，Invalid parameter.。";
}

std::string UrmaFailure429::GetId() const
{
    return "urma_429";
}

} // namespace diag
