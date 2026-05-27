#include "urma_failure_487.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure487> g_urma("urma_487");

bool UrmaFailure487::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_discover_sysfs_path' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'snprintf failed, dev_name:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure487::GetName() const
{
    return "执行设备过程中依赖步骤失败";
}

std::string UrmaFailure487::GetRootCauseDesc() const
{
    return "函数用于执行设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure487::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure487::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure487::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_discover_sysfs_path，snprintf failed, dev_name:。";
}

std::string UrmaFailure487::GetId() const
{
    return "urma_487";
}

} // namespace diag
