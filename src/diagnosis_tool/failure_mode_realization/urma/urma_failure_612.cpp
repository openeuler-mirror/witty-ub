#include "urma_failure_612.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure612> g_urma("urma_612");

bool UrmaFailure612::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure612::GetName() const
{
    return "JFS对象无效导致删除JFS失败";
}

std::string UrmaFailure612::GetRootCauseDesc() const
{
    return "函数用于删除JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure612::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure612::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure612::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfs_batch，Invalid parameter";
}

std::string UrmaFailure612::GetId() const
{
    return "urma_612";
}

} // namespace diag
