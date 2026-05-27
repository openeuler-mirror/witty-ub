#include "urma_failure_476.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure476> g_urma("urma_476");

bool UrmaFailure476::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'read_eid_sysfs_with_index' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'snprintf failed, eid idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure476::GetName() const
{
    return "读取EID过程中依赖步骤失败";
}

std::string UrmaFailure476::GetRootCauseDesc() const
{
    return "函数用于读取EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure476::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure476::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure476::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：read_eid_sysfs_with_index，snprintf failed, eid idx:";
}

std::string UrmaFailure476::GetId() const
{
    return "urma_476";
}

} // namespace diag
