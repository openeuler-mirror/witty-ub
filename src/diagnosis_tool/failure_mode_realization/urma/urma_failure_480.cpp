#include "urma_failure_480.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure480> g_urma("urma_480");

bool UrmaFailure480::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'read_eid_sysfs_with_index' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'snprintf failed, eid idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure480::GetName() const
{
    return "读取EID过程中依赖步骤失败";
}

std::string UrmaFailure480::GetRootCauseDesc() const
{
    return "函数用于读取EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure480::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure480::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure480::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_sysfs_with_index，snprintf failed, eid idx:。";
}

std::string UrmaFailure480::GetId() const
{
    return "urma_480";
}

} // namespace diag
