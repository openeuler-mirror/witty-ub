#include "urma_failure_790.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure790> g_urma("urma_790");

bool UrmaFailure790::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfs_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec ops->set_jfs_opt.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure790::GetName() const
{
    return "设置JFS过程中依赖步骤失败";
}

std::string UrmaFailure790::GetRootCauseDesc() const
{
    return "函数用于设置JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure790::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure790::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure790::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfs_opt，Failed to exec ops->set_jfs_opt.";
}

std::string UrmaFailure790::GetId() const
{
    return "urma_790";
}

} // namespace diag
