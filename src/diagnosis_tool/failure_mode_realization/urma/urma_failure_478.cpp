#include "urma_failure_478.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure478> g_urma("urma_478");

bool UrmaFailure478::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'read_eid_list_sysyf' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'printf failed, eid idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure478::GetName() const
{
    return "读取EID过程中依赖步骤失败";
}

std::string UrmaFailure478::GetRootCauseDesc() const
{
    return "函数用于读取EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure478::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure478::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure478::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_list_sysyf，printf failed, eid idx:。";
}

std::string UrmaFailure478::GetId() const
{
    return "urma_478";
}

} // namespace diag
