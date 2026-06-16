#include "urma_failure_617.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure617> g_urma("urma_617");

bool UrmaFailure617::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure617::GetName() const
{
    return "URMA context、JFS对象无效导致删除JFS失败";
}

std::string UrmaFailure617::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure617::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure617::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure617::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs，Invalid parameter。";
}

std::string UrmaFailure617::GetId() const
{
    return "urma_617";
}

} // namespace diag
