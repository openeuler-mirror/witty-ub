#include "urma_failure_501.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure501> g_urma("urma_501");

bool UrmaFailure501::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_perf_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Urma perf get info failed, need' | grep -F 'bytes buffer, but only' | grep -F 'provided'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure501::GetName() const
{
    return "获取锁过程中依赖步骤失败";
}

std::string UrmaFailure501::GetRootCauseDesc() const
{
    return "函数用于获取锁，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure501::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure501::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure501::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_perf_info，Urma perf get info failed, need，bytes buffer, but "
           "only，provided";
}

std::string UrmaFailure501::GetId() const
{
    return "urma_501";
}

} // namespace diag
