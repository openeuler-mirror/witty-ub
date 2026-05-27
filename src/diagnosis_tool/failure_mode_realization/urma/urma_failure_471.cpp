#include "urma_failure_471.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure471> g_urma("urma_471");

bool UrmaFailure471::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_read_sysfs_file' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'snprintf failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure471::GetName() const
{
    return "读取sysfs过程中依赖步骤失败";
}

std::string UrmaFailure471::GetRootCauseDesc() const
{
    return "函数用于读取sysfs，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure471::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure471::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure471::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_read_sysfs_file，snprintf failed";
}

std::string UrmaFailure471::GetId() const
{
    return "urma_471";
}

} // namespace diag
