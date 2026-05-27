#include "urma_failure_617.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure617> g_urma("urma_617");

bool UrmaFailure617::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'bad jfs index exceed array length, bad_jfs_index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure617::GetName() const
{
    return "删除JFS过程中依赖步骤失败";
}

std::string UrmaFailure617::GetRootCauseDesc() const
{
    return "函数用于删除JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
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
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jfs_batch，bad jfs index exceed array length, bad_jfs_index:";
}

std::string UrmaFailure617::GetId() const
{
    return "urma_617";
}

} // namespace diag
