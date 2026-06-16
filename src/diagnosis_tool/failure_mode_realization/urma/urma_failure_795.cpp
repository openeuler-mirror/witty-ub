#include "urma_failure_795.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure795> g_urma("urma_795");

bool UrmaFailure795::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfs_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to set opt, jfs has been activated'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure795::GetName() const
{
    return "设置JFS过程中依赖步骤失败";
}

std::string UrmaFailure795::GetRootCauseDesc() const
{
    return "函数用于设置JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure795::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure795::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure795::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfs_opt，Failed to set opt, jfs has been activated。";
}

std::string UrmaFailure795::GetId() const
{
    return "urma_795";
}

} // namespace diag
