#include "urma_failure_866.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure866> g_urma("urma_866");

bool UrmaFailure866::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_str_to_eid' "
                                                         "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'format error:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure866::GetName() const
{
    return "执行EID过程中依赖步骤失败";
}

std::string UrmaFailure866::GetRootCauseDesc() const
{
    return "函数用于执行EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure866::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure866::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure866::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_str_to_eid，format error:。";
}

std::string UrmaFailure866::GetId() const
{
    return "urma_866";
}

} // namespace diag
