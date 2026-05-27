#include "urma_failure_485.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure485> g_urma("urma_485");

bool UrmaFailure485::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_scan_sysfs_devices' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed close dir:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure485::GetName() const
{
    return "释放sysfs过程中依赖步骤失败";
}

std::string UrmaFailure485::GetRootCauseDesc() const
{
    return "函数用于释放sysfs，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure485::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure485::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure485::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_scan_sysfs_devices，Failed close dir:，, errno:";
}

std::string UrmaFailure485::GetId() const
{
    return "urma_485";
}

} // namespace diag
