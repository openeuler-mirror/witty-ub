#include "urma_failure_056.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure056> g_urma("urma_056");

bool UrmaFailure056::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jfs_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add jfs p_vjetty_id info'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure056::GetName() const
{
    return "创建JFS过程中依赖步骤失败";
}

std::string UrmaFailure056::GetRootCauseDesc() const
{
    return "函数用于创建JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure056::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure056::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure056::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_del_jfs_p_vjetty_info，Failed to add jfs p_vjetty_id info";
}

std::string UrmaFailure056::GetId() const
{
    return "urma_056";
}

} // namespace diag
