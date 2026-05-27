#include "urma_failure_455.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure455> g_urma("urma_455");

bool UrmaFailure455::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfs_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure455::GetName() const
{
    return "provider操作表、JFS对象无效导致获取JFS失败";
}

std::string UrmaFailure455::GetRootCauseDesc() const
{
    return "函数用于获取JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure455::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure455::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure455::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfs_opt，Invalid parameter.。";
}

std::string UrmaFailure455::GetId() const
{
    return "urma_455";
}

} // namespace diag
