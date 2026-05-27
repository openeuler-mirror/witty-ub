#include "urma_failure_857.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure857> g_urma("urma_857");

bool UrmaFailure857::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_str_to_eid' "
                                                         "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'format error:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure857::GetName() const
{
    return "执行EID过程中依赖步骤失败";
}

std::string UrmaFailure857::GetRootCauseDesc() const
{
    return "函数用于执行EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure857::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure857::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure857::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_str_to_eid，format error:";
}

std::string UrmaFailure857::GetId() const
{
    return "urma_857";
}

} // namespace diag
