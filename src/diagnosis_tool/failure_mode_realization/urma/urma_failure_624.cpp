#include "urma_failure_624.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure624> g_urma("urma_624");

bool UrmaFailure624::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'bad jfs index exceed array length, bad_jfs_index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure624::GetName() const
{
    return "删除JFS过程中依赖步骤失败";
}

std::string UrmaFailure624::GetRootCauseDesc() const
{
    return "函数用于删除JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure624::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure624::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure624::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs_batch，bad jfs index exceed array length, "
           "bad_jfs_index:。";
}

std::string UrmaFailure624::GetId() const
{
    return "urma_624";
}

} // namespace diag
